"""ODRL Access Grant verification for FAIR Data.

Verifies that a valid ODRL Access Grant for FAIR Data nanopub exists
for a requester + dataset, and that it was published by the same
identity that published the corresponding ODRL Access Policy for FAIR Data.
"""

import tempfile
from pathlib import Path

import httpx
from rdflib import Dataset, Namespace, URIRef

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
      graph ?pubinfo {{
        ?np dct:creator ?creator .
      }}
      FILTER NOT EXISTS {{
        graph ?retractHead {{
          ?retractNp np:hasAssertion ?retractAssertion .
        }}
        graph ?retractAssertion {{
          ?someone npx:retracts ?np .
        }}
      }}
    }}
    """

    response = httpx.get(
        SPARQL_ENDPOINT,
        params={"query": query},
        headers={"Accept": "application/json"},
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()

    results = []
    for binding in response.json().get("results", {}).get("bindings", []):
        results.append({
            "nanopub_uri": binding["np"]["value"],
            "creator": binding["creator"]["value"],
            "assignee": binding.get("assignee", {}).get("value"),
            "policy": binding.get("policy", {}).get("value"),
        })
    return results


def get_nanopub_creator(nanopub_uri: str) -> str:
    """Get the dct:creator of a nanopub from its pubinfo graph."""
    response = httpx.get(
        nanopub_uri,
        headers={"Accept": "application/trig"},
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()

    ds = Dataset()
    ds.parse(data=response.text, format="trig")

    pubinfo_uri = nanopub_uri.rstrip("/") + "/pubinfo"
    pubinfo = ds.graph(pubinfo_uri)

    for creator in pubinfo.objects(URIRef(nanopub_uri), DCT.creator):
        return str(creator)

    raise ValueError(f"No creator found in nanopub {nanopub_uri}")


def verify_nanopub_signature(nanopub_uri: str) -> bool:
    """Verify the cryptographic signature of a nanopub.

    Downloads the nanopub and uses the nanopub library to check
    that the signature matches the content and public key.
    """
    from nanopub import Nanopub

    response = httpx.get(
        nanopub_uri,
        headers={"Accept": "application/trig"},
        follow_redirects=True,
        timeout=30,
    )
    response.raise_for_status()

    tmp = Path(tempfile.mktemp(suffix=".trig"))
    try:
        tmp.write_text(response.text)
        np_obj = Nanopub(rdf=tmp)
        return np_obj.has_valid_signature
    finally:
        tmp.unlink()


def verify_access(
    dataset_uri: str,
    requester_did: str,
    policy_nanopub_uri: str,
) -> dict:
    """Verify that a requester has been granted access to a dataset.

    Checks:
    1. A valid ODRL Access Grant for FAIR Data nanopub exists for this
       requester + dataset
    2. The grant nanopub has a valid cryptographic signature
    3. The grant was published by the SAME identity that published the
       ODRL Access Policy for FAIR Data (only the data provider can authorize)

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

    # Step 1: Get the policy creator
    print(f"Checking policy creator: {policy_nanopub_uri}")
    try:
        policy_creator = get_nanopub_creator(policy_nanopub_uri)
        result["policy_creator"] = policy_creator
        print(f"  Policy creator: {policy_creator}")
    except Exception as e:
        result["reason"] = f"Cannot fetch policy nanopub: {e}"
        return result

    # Step 2: Search for grants
    print(f"Searching for grants: dataset={dataset_uri}, requester={requester_did}")
    grants = find_grants(dataset_uri, requester_did)

    if not grants:
        result["reason"] = "No ODRL Access Grant for FAIR Data found for this requester and dataset"
        return result

    print(f"  Found {len(grants)} grant(s)")

    # Step 3: Check each grant
    for grant in grants:
        grant_uri = grant["nanopub_uri"]
        grant_creator = grant["creator"]
        result["grant_nanopub"] = grant_uri
        result["grant_creator"] = grant_creator

        print(f"  Checking grant: {grant_uri}")
        print(f"    Grant creator: {grant_creator}")

        # Check creator match
        if grant_creator != policy_creator:
            print(f"    REJECTED: grant creator does not match policy creator")
            continue

        # Step 4: Verify signature
        print(f"    Verifying signature...")
        try:
            sig_valid = verify_nanopub_signature(grant_uri)
        except Exception as e:
            print(f"    Signature verification failed: {e}")
            continue

        if not sig_valid:
            print(f"    REJECTED: invalid signature")
            continue

        print(f"    VALID: signature verified, creator authorized")
        result["granted"] = True
        result["reason"] = "Valid grant found: signature verified, creator matches policy publisher"
        return result

    # No valid grant found
    result["reason"] = "Grant(s) found but none are valid (creator mismatch or bad signature)"
    return result
