"""ODRL Access Grant verification for FAIR Data.

Verifies that a valid ODRL Access Grant for FAIR Data nanopub exists
for a requester + dataset, and that it was signed with the same key
as the corresponding ODRL Access Policy for FAIR Data.

The SPARQL index is only used to find candidate grants. Every decision is
taken on the signed nanopublications themselves: a valid signature proves a
record is intact, and comparing signing keys proves who issued it. The
self-declared dct:creator is reported but never trusted.
"""

import tempfile
from pathlib import Path

import httpx
from rdflib import RDF, Dataset, Namespace, URIRef

ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
NP = Namespace("http://www.nanopub.org/nschema#")
NPX = Namespace("http://purl.org/nanopub/x/")
DCT = Namespace("http://purl.org/dc/terms/")
FAIR = Namespace("https://fair2adapt.eu/ns/")

SPARQL_ENDPOINT = "https://query.knowledgepixels.com/repo/full"


def _did_to_url(did: str) -> str:
    """Convert a did:web identifier to its HTTPS URL.

    e.g. did:web:fair2adapt.github.io:fair-data-access
      → https://fair2adapt.github.io/fair-data-access/did.json
    """
    if did.startswith("did:web:"):
        parts = did.replace("did:web:", "").split(":")
        domain = parts[0]
        path = "/".join(parts[1:]) if len(parts) > 1 else ""
        url = f"https://{domain}/{path}/did.json" if path else f"https://{domain}/did.json"
        return url
    return did


def find_grants(dataset_uri: str, requester_did: str = None) -> list[dict]:
    """Search the nanopub network for ODRL Access Grant for FAIR Data nanopubs.

    Parameters
    ----------
    dataset_uri : URI of the dataset (e.g. https://fair2adapt.eu/data/hamburg-buildings)
    requester_did : DID of the requester (optional, filters results)

    Returns
    -------
    List of dicts with keys: nanopub_uri, creator, target, assignee, policy
    """
    assignee_filter = ""
    if requester_did:
        # Search for both did:web: and its HTTPS URL equivalent
        did_url = _did_to_url(requester_did)
        if did_url != requester_did:
            assignee_filter = (
                f'?grant odrl:assignee ?assignee .\n'
                f'        FILTER (?assignee = <{requester_did}> || ?assignee = <{did_url}>)'
            )
        else:
            assignee_filter = f'?grant odrl:assignee <{requester_did}> .'

    query = f"""
    PREFIX odrl: <http://www.w3.org/ns/odrl/2/>
    PREFIX np: <http://www.nanopub.org/nschema#>
    PREFIX npx: <http://purl.org/nanopub/x/>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX fair: <https://fair2adapt.eu/ns/>

    SELECT ?np ?creator ?assignee ?policy WHERE {{
      graph ?head {{
        ?np a np:Nanopublication ;
            np:hasAssertion ?assertion ;
            np:hasPublicationInfo ?pubinfo .
      }}
      graph ?assertion {{
        ?grant a odrl:Agreement ;
               odrl:target <{dataset_uri}> .
        {assignee_filter}
        OPTIONAL {{ ?grant odrl:assignee ?assignee . }}
        OPTIONAL {{ ?grant fair:underPolicy ?policy . }}
      }}
      OPTIONAL {{
        graph ?pubinfo {{
          ?np dct:creator ?creator .
        }}
      }}
    }}
    """

    response = httpx.get(
        SPARQL_ENDPOINT,
        params={"query": query},
        headers={"Accept": "application/json"},
        follow_redirects=True,
        timeout=60,
    )
    response.raise_for_status()

    results = []
    for binding in response.json().get("results", {}).get("bindings", []):
        results.append({
            "nanopub_uri": binding["np"]["value"],
            "creator": binding.get("creator", {}).get("value"),
            "assignee": binding.get("assignee", {}).get("value"),
            "policy": binding.get("policy", {}).get("value"),
        })
    return results


def artifact_code(nanopub_uri: str) -> str:
    """The trusty-URI artifact code, independent of the namespace it is served under.

    The same nanopublication is addressable as https://w3id.org/np/<code> and, when
    published via Science Live, as https://w3id.org/sciencelive/np/<code>. Only the
    final segment is identity; compare on that, never on the whole URI.
    """
    return nanopub_uri.rstrip("/").rsplit("/", 1)[-1].removesuffix(".trig")


def canonical_nanopub_url(nanopub_uri: str) -> str:
    """The URL to fetch a nanopub's RDF from, whatever namespace it was minted under.

    A nanopublication's identity is its trusty-URI artifact code, and the registry
    serves every nanopub at https://w3id.org/np/<code>. Platform-specific namespaces
    (e.g. Science Live's https://w3id.org/sciencelive/np/<code>) are not guaranteed to
    content-negotiate to RDF, so always fetch through the canonical form.
    """
    return f"https://w3id.org/np/{artifact_code(nanopub_uri)}"


def same_nanopub(a: str | None, b: str | None) -> bool:
    """True when two URIs denote the same nanopublication under any namespace."""
    if not a or not b:
        return False
    return artifact_code(a) == artifact_code(b)


def fetch_nanopub_trig(nanopub_uri: str) -> str:
    """Fetch a nanopub as TriG text through its canonical URL."""
    response = httpx.get(
        canonical_nanopub_url(nanopub_uri),
        headers={"Accept": "application/trig"},
        follow_redirects=True,
        timeout=60,
    )
    response.raise_for_status()

    body = response.text.lstrip()
    ctype = response.headers.get("content-type", "")
    # "<" alone is not a reliable signal: TriG statements may start with a URI, and
    # an HTML shell starts "<!DOCTYPE". Test for markup explicitly.
    if body[:9].lower().startswith(("<!doctype", "<html")) or "html" in ctype:
        raise ValueError(
            f"{nanopub_uri} did not return RDF (got {response.headers.get('content-type', '?')}). "
            "Some vanity namespaces serve an HTML application shell; try the "
            f"https://w3id.org/np/{artifact_code(nanopub_uri)} form."
        )
    return response.text


def parse_nanopub(trig: str, nanopub_uri: str = "") -> tuple[Dataset, URIRef]:
    """Parse nanopub TriG and return (dataset, its own identifier).

    The identifier is read from the RDF rather than assumed to equal the URL we
    fetched: a nanopub served under one namespace may identify itself under another,
    in which case constructing graph names from the request URL finds nothing.
    """
    ds = Dataset()
    ds.parse(data=trig, format="trig")

    for graph in ds.graphs():
        for subj in graph.subjects(NP.hasPublicationInfo, None):
            return ds, URIRef(str(subj))

    raise ValueError(f"No np:hasPublicationInfo found in {nanopub_uri}")


def signature_is_valid(trig: str) -> bool:
    """Check that a nanopub's signature matches its content and embedded key.

    This proves the record is intact, not who signed it: compare the
    signing key (signing_public_key) to establish that.
    """
    from nanopub import Nanopub

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir) / "np.trig"
        tmp.write_text(trig)
        return Nanopub(rdf=tmp).has_valid_signature


def signing_public_key(ds: Dataset, np_uri: URIRef) -> str:
    """The public key np_uri was signed with, whitespace-free.

    Read from the signature node (npx:hasSignatureTarget np_uri), the same
    node the nanopub library verifies against. Any other npx:hasPublicKey in
    pubinfo is ignored: a signer can add one naming someone else's key.
    """
    sig_nodes = {s for s, _, _, _ in ds.quads((None, NPX.hasSignatureTarget, np_uri, None))}
    if len(sig_nodes) != 1:
        raise ValueError(f"Expected one signature for {np_uri}, found {len(sig_nodes)}")
    sig = sig_nodes.pop()

    # The nanopub library skips verification for DSA and reports it valid,
    # so accept only the algorithm it actually checks.
    algorithms = {str(o).upper() for _, _, o, _ in ds.quads((sig, NPX.hasAlgorithm, None, None))}
    if algorithms != {"RSA"}:
        raise ValueError(f"Unsupported signature algorithm {sorted(algorithms)} for {np_uri}")

    keys = {"".join(str(o).split()) for _, _, o, _ in ds.quads((sig, NPX.hasPublicKey, None, None))}
    if len(keys) != 1:
        raise ValueError(f"Expected one public key on the signature of {np_uri}, found {len(keys)}")
    return keys.pop()


def grant_matches(
    ds: Dataset, dataset_uri: str, assignees: set[str], policy_nanopub_uri: str
) -> bool:
    """True if the signed grant assertion names this dataset, assignee and policy.

    Read from the fetched nanopub itself, not from the SPARQL index, which
    is a third-party copy.
    """
    for graph in ds.graphs():
        if not str(graph.identifier).rstrip("/").endswith("assertion"):
            continue
        for grant in graph.subjects(RDF.type, ODRL.Agreement):
            targets = {str(o) for o in graph.objects(grant, ODRL.target)}
            grant_assignees = {str(o) for o in graph.objects(grant, ODRL.assignee)}
            policies = [str(o) for o in graph.objects(grant, FAIR.underPolicy)]
            if (
                dataset_uri in targets
                and grant_assignees & assignees
                and any(same_nanopub(p, policy_nanopub_uri) for p in policies)
            ):
                return True
    return False


def find_retractions(nanopub_uri: str) -> list[str]:
    """URIs of nanopubs that claim to retract the given nanopub (unverified)."""
    targets = " ".join(
        f"<{uri}>" for uri in {nanopub_uri, canonical_nanopub_url(nanopub_uri)}
    )
    query = f"""
    PREFIX np: <http://www.nanopub.org/nschema#>
    PREFIX npx: <http://purl.org/nanopub/x/>

    SELECT DISTINCT ?retractNp WHERE {{
      VALUES ?target {{ {targets} }}
      graph ?retractHead {{
        ?retractNp np:hasAssertion ?retractAssertion .
      }}
      graph ?retractAssertion {{
        ?someone npx:retracts ?target .
      }}
    }}
    """
    response = httpx.get(
        SPARQL_ENDPOINT,
        params={"query": query},
        headers={"Accept": "application/json"},
        follow_redirects=True,
        timeout=60,
    )
    response.raise_for_status()
    return [
        b["retractNp"]["value"]
        for b in response.json().get("results", {}).get("bindings", [])
    ]


def is_retracted_by_key(nanopub_uri: str, public_key: str) -> bool:
    """True if a validly signed retraction made with public_key exists.

    Anyone can publish a retraction; only one signed with the issuer's key counts.
    """
    for retraction_uri in find_retractions(nanopub_uri):
        try:
            trig = fetch_nanopub_trig(retraction_uri)
            ds, np_uri = parse_nanopub(trig, retraction_uri)
            if signing_public_key(ds, np_uri) == public_key and signature_is_valid(trig):
                return True
        except Exception as e:
            print(f"    Ignoring unverifiable retraction {retraction_uri}: {e}")
    return False


def verify_access(
    dataset_uri: str,
    requester_did: str,
    policy_nanopub_uri: str,
) -> dict:
    """Verify that a requester has been granted access to a dataset.

    Checks:
    1. The policy nanopub has a valid signature; its signing key is the
       issuer key for this dataset
    2. A grant nanopub exists whose signed assertion names this dataset,
       this requester and this policy (fair:underPolicy)
    3. The grant has a valid signature, made with the SAME key as the policy
       (only the data provider can authorize)
    4. The grant has not been retracted by a retraction signed with that key

    Parameters
    ----------
    dataset_uri : URI of the dataset
    requester_did : DID of the requester
    policy_nanopub_uri : URI of the policy nanopub

    Returns
    -------
    dict with keys:
      - granted: bool
      - reason: str
      - grant_nanopub: str (URI, if found)
      - policy_creator: str
      - grant_creator: str
    """
    result = {
        "granted": False,
        "reason": "",
        "grant_nanopub": None,
        "policy_creator": None,
        "grant_creator": None,
    }

    # Step 1: Get the policy's signing key
    print(f"Checking policy: {policy_nanopub_uri}")
    try:
        policy_trig = fetch_nanopub_trig(policy_nanopub_uri)
        policy_ds, policy_np = parse_nanopub(policy_trig, policy_nanopub_uri)
        if not signature_is_valid(policy_trig):
            result["reason"] = "Policy nanopub has an invalid signature"
            return result
        issuer_key = signing_public_key(policy_ds, policy_np)
        result["policy_creator"] = next(
            (str(c) for g in policy_ds.graphs() for c in g.objects(policy_np, DCT.creator)),
            None,
        )
        print(f"  Policy creator: {result['policy_creator']}")
    except Exception as e:
        result["reason"] = f"Cannot fetch policy nanopub: {e}"
        return result

    # Step 2: Search for candidate grants
    print(f"Searching for grants: dataset={dataset_uri}, requester={requester_did}")
    grants = find_grants(dataset_uri, requester_did)

    if not grants:
        result["reason"] = "No ODRL Access Grant for FAIR Data found for this requester and dataset"
        return result

    print(f"  Found {len(grants)} candidate grant(s)")
    assignees = {requester_did, _did_to_url(requester_did)}

    # Step 3: Check each grant on its signed content
    for grant in grants:
        grant_uri = grant["nanopub_uri"]
        result["grant_nanopub"] = grant_uri
        result["grant_creator"] = grant["creator"]
        print(f"  Checking grant: {grant_uri}")

        try:
            grant_trig = fetch_nanopub_trig(grant_uri)
            grant_ds, grant_np = parse_nanopub(grant_trig, grant_uri)
        except Exception as e:
            print(f"    REJECTED: cannot fetch grant: {e}")
            continue

        if not grant_matches(grant_ds, dataset_uri, assignees, policy_nanopub_uri):
            print("    REJECTED: grant does not name this dataset, requester and policy")
            continue

        try:
            grant_key = signing_public_key(grant_ds, grant_np)
            sig_valid = signature_is_valid(grant_trig)
        except Exception as e:
            print(f"    REJECTED: signature verification failed: {e}")
            continue

        if not sig_valid:
            print("    REJECTED: invalid signature")
            continue

        if grant_key != issuer_key:
            print("    REJECTED: grant not signed with the policy publisher's key")
            continue

        if is_retracted_by_key(grant_uri, issuer_key):
            print("    REJECTED: grant retracted by its issuer")
            continue

        print("    VALID: signature verified, signed with the policy publisher's key")
        result["granted"] = True
        result["reason"] = "Valid grant found: signature verified, signed with the policy publisher's key"
        return result

    # No valid grant found
    result["reason"] = "Grant(s) found but none are valid (wrong policy, wrong key, bad signature or retracted)"
    return result
