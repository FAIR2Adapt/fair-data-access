"""ODRL policy creation, evaluation, and fetching.

Policies are expressed as ODRL JSON-LD and can be published as
nanopublications for immutability and verifiability.
"""

import json
from pathlib import Path

import httpx
from rdflib import Graph


ODRL_CONTEXT = "http://www.w3.org/ns/odrl.jsonld"

# Standard ODRL actions (from the W3C vocabulary)
# Non-standard actions should use full URIs
ODRL_ACTIONS = {
    "use", "transfer", "acceptTracking", "aggregate", "annotate",
    "anonymize", "archive", "attribute", "compensate", "concurrentUse",
    "delete", "derive", "digitize", "display", "distribute", "ensureExclusivity",
    "execute", "extract", "give", "grantUse", "include", "index", "inform",
    "install", "modify", "move", "nextPolicy", "obtainConsent", "play",
    "present", "print", "read", "reproduce", "reviewPolicy", "sell",
    "stream", "synchronize", "textToSpeech", "transform", "translate",
    "uninstall", "watermark",
}


def _normalize_action(action: str) -> str:
    """Ensure non-standard actions use full ODRL URIs."""
    if action in ODRL_ACTIONS:
        return action
    # If it looks like a URI, keep it as is
    if action.startswith("http://") or action.startswith("https://"):
        return action
    # Non-standard action: use ODRL namespace
    return f"http://www.w3.org/ns/odrl/2/{action}"


def _normalize_actions(actions):
    """Normalize a single action or list of actions."""
    if isinstance(actions, list):
        return [_normalize_action(a) for a in actions]
    return _normalize_action(actions)


def create_policy(
    policy_uid: str,
    target: str,
    permissions: list[dict] | None = None,
    prohibitions: list[dict] | None = None,
    duties: list[dict] | None = None,
    policy_type: str = "Offer",
) -> dict:
    """Create an ODRL policy as a JSON-LD dictionary.

    Parameters
    ----------
    policy_uid : unique identifier for the policy (URI)
    target : URI of the dataset this policy applies to
    permissions : list of permission dicts with 'action' and optional 'constraint'
    prohibitions : list of prohibition dicts with 'action'
    duties : list of duty dicts with 'action'
    policy_type : 'Offer', 'Set', or 'Agreement'

    Returns
    -------
    ODRL policy as JSON-LD dict.

    Example
    -------
    >>> policy = create_policy(
    ...     policy_uid="https://fair2adapt.eu/policy/hamburg-buildings",
    ...     target="https://fair2adapt.eu/data/hamburg-buildings",
    ...     permissions=[{
    ...         "action": ["use", "reproduce"],
    ...         "constraint": {
    ...             "leftOperand": "purpose",
    ...             "operator": "eq",
    ...             "rightOperand": "AcademicResearch"
    ...         }
    ...     }],
    ...     prohibitions=[{"action": ["distribute", "commercialize"]}],
    ...     duties=[{"action": "attribute"}],
    ... )
    """
    policy = {
        "@context": ODRL_CONTEXT,
        "@type": policy_type,
        "uid": policy_uid,
    }

    if permissions:
        policy["permission"] = []
        for perm in permissions:
            p = {"target": target, "action": _normalize_actions(perm["action"])}
            if "constraint" in perm:
                p["constraint"] = [perm["constraint"]] if isinstance(perm["constraint"], dict) else perm["constraint"]
            if "assignee" in perm:
                p["assignee"] = perm["assignee"]
            policy["permission"].append(p)

    if prohibitions:
        policy["prohibition"] = []
        for prohib in prohibitions:
            policy["prohibition"].append({
                "target": target,
                "action": _normalize_actions(prohib["action"]),
            })

    if duties:
        policy["duty"] = []
        for duty in duties:
            d = {"action": _normalize_actions(duty["action"])}
            if "target" in duty:
                d["target"] = duty["target"]
            policy["duty"].append(d)

    return policy


def save_policy(policy: dict, output_path: str | Path) -> Path:
    """Save an ODRL policy to a JSON-LD file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(policy, indent=2))
    return output_path


def load_policy(path: str | Path) -> dict:
    """Load an ODRL policy from a JSON-LD file."""
    return json.loads(Path(path).read_text())


def fetch_policy(nanopub_uri: str) -> dict:
    """Fetch an ODRL policy from a nanopublication URI.

    Resolves the nanopub, extracts the assertion graph,
    and returns the ODRL policy as a dict.
    """
    # Nanopub URIs resolve to RDF; fetch as JSON-LD
    response = httpx.get(
        nanopub_uri,
        headers={"Accept": "application/ld+json"},
        follow_redirects=True,
    )
    response.raise_for_status()

    # Parse the nanopub RDF and extract the assertion graph
    g = Graph()
    g.parse(data=response.text, format="json-ld")

    # Extract the ODRL policy from the assertion
    # Nanopub structure: head → assertion, provenance, pubinfo
    # The ODRL policy is in the assertion graph
    policy_json = _extract_odrl_from_graph(g)
    return policy_json


def _extract_odrl_from_graph(g: Graph) -> dict:
    """Extract ODRL policy triples from an RDF graph."""
    from rdflib import ODRL2, RDF

    # Find the policy node (subject with type odrl:Offer, odrl:Set, or odrl:Agreement)
    policy_types = [ODRL2.Offer, ODRL2.Set, ODRL2.Agreement]
    for policy_type in policy_types:
        for s in g.subjects(RDF.type, policy_type):
            # Serialize just the policy subgraph
            policy_graph = Graph()
            for triple in g.triples((s, None, None)):
                policy_graph.add(triple)
            return json.loads(
                policy_graph.serialize(format="json-ld")
            )
    raise ValueError("No ODRL policy found in the RDF graph")


def evaluate_policy(
    policy: dict,
    requester_did: str | None = None,
    purpose: str | None = None,
    context: dict | None = None,
) -> bool:
    """Evaluate an ODRL policy against a request context.

    Parameters
    ----------
    policy : ODRL policy dict (JSON-LD)
    requester_did : DID of the requester
    purpose : declared purpose (e.g., 'AcademicResearch')
    context : additional context for policy evaluation

    Returns
    -------
    True if access is permitted, False otherwise.
    """
    # Check permissions and their constraints
    permissions = policy.get("permission", [])
    if not permissions:
        return False

    for perm in permissions:
        constraints = perm.get("constraint", [])
        if not constraints:
            # No constraints = unconditionally permitted
            return True

        # Check all constraints
        all_satisfied = True
        for constraint in constraints:
            left = constraint.get("leftOperand", "")
            operator = constraint.get("operator", "")
            right = constraint.get("rightOperand", "")

            if left in ("purpose", "odrl:purpose", "http://www.w3.org/ns/odrl/2/purpose"):
                if operator in ("eq", "odrl:eq"):
                    # Compare purpose value or DPV URI
                    if purpose != right and f"https://w3id.org/dpv#{purpose}" != right:
                        all_satisfied = False
                        break
            elif context and left in context:
                if operator in ("eq", "odrl:eq"):
                    if context[left] != right:
                        all_satisfied = False
                        break

        if all_satisfied:
            return True

    return False
