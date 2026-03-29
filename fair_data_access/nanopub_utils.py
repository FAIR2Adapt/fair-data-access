"""Nanopublication utilities for ODRL policies and access grants.

Uses the nanopub Python library to publish and fetch nanopublications
on the decentralized nanopub network.
"""

import json
from datetime import datetime, timezone

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, XSD


ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
NPX = Namespace("http://purl.org/nanopub/x/")
FAIR = Namespace("https://fair2adapt.eu/ns/")


def create_policy_nanopub_rdf(
    policy_jsonld: dict,
    author_orcid: str,
) -> tuple[Graph, Graph, Graph]:
    """Create RDF graphs for a nanopublication wrapping an ODRL policy.

    Parameters
    ----------
    policy_jsonld : the ODRL policy as a JSON-LD dict
    author_orcid : ORCID of the policy author (e.g., 'https://orcid.org/0000-...')

    Returns
    -------
    (assertion_graph, provenance_graph, pubinfo_graph)
    """
    # Assertion: the ODRL policy itself
    assertion = Graph()
    assertion.parse(data=json.dumps(policy_jsonld), format="json-ld")

    # Provenance
    provenance = Graph()
    assertion_uri = URIRef("http://purl.org/nanopub/temp/assertion")
    provenance.add((
        assertion_uri,
        PROV.wasAttributedTo,
        URIRef(author_orcid),
    ))
    provenance.add((
        assertion_uri,
        PROV.generatedAtTime,
        Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime),
    ))

    # Publication info
    pubinfo = Graph()
    np_uri = URIRef("http://purl.org/nanopub/temp/")
    pubinfo.add((np_uri, NPX.hasNanopubType, NPX.Policy))
    pubinfo.add((
        np_uri,
        PROV.wasAttributedTo,
        URIRef(author_orcid),
    ))

    return assertion, provenance, pubinfo


def publish_policy(
    policy_jsonld: dict,
    author_orcid: str,
) -> str:
    """Publish an ODRL policy as a nanopublication.

    Parameters
    ----------
    policy_jsonld : the ODRL policy as JSON-LD dict
    author_orcid : ORCID of the policy author

    Returns
    -------
    The nanopublication URI (e.g., 'https://w3id.org/np/RA-...')
    """
    from nanopub import Nanopub, NanopubClient

    assertion, provenance, pubinfo = create_policy_nanopub_rdf(
        policy_jsonld, author_orcid
    )

    np = Nanopub(
        assertion=assertion,
        provenance=provenance,
        pubinfo=pubinfo,
    )

    client = NanopubClient()
    published = client.publish(np)
    return published.nanopub_uri


def create_access_grant_rdf(
    dataset_uri: str,
    requester_did: str,
    policy_nanopub_uri: str,
    actions: list[str],
    author_orcid: str,
    workflow_run_url: str | None = None,
) -> tuple[Graph, Graph, Graph]:
    """Create RDF graphs for an access grant nanopublication.

    This records that a specific DID was granted access to a dataset
    under a specific ODRL policy.
    """
    now = Literal(
        datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime
    )

    # Assertion: the access grant
    assertion = Graph()
    grant = URIRef("http://purl.org/nanopub/temp/grant")
    assertion.add((grant, RDF.type, ODRL.Agreement))
    assertion.add((grant, ODRL.target, URIRef(dataset_uri)))
    assertion.add((grant, ODRL.assignee, URIRef(requester_did)))
    for action in actions:
        assertion.add((grant, ODRL.action, ODRL[action]))
    assertion.add((grant, PROV.generatedAtTime, now))
    assertion.add((grant, FAIR.underPolicy, URIRef(policy_nanopub_uri)))

    # Provenance
    provenance = Graph()
    assertion_uri = URIRef("http://purl.org/nanopub/temp/assertion")
    provenance.add((assertion_uri, PROV.wasAttributedTo, URIRef(author_orcid)))
    if workflow_run_url:
        provenance.add((
            assertion_uri,
            PROV.wasGeneratedBy,
            URIRef(workflow_run_url),
        ))

    # Publication info
    pubinfo = Graph()
    np_uri = URIRef("http://purl.org/nanopub/temp/")
    pubinfo.add((np_uri, NPX.hasNanopubType, NPX.AccessGrant))
    pubinfo.add((np_uri, PROV.wasAttributedTo, URIRef(author_orcid)))

    return assertion, provenance, pubinfo


def publish_access_grant(
    dataset_uri: str,
    requester_did: str,
    policy_nanopub_uri: str,
    actions: list[str],
    author_orcid: str,
    workflow_run_url: str | None = None,
) -> str:
    """Publish an access grant as a nanopublication.

    Returns
    -------
    The nanopublication URI of the access grant.
    """
    from nanopub import Nanopub, NanopubClient

    assertion, provenance, pubinfo = create_access_grant_rdf(
        dataset_uri=dataset_uri,
        requester_did=requester_did,
        policy_nanopub_uri=policy_nanopub_uri,
        actions=actions,
        author_orcid=author_orcid,
        workflow_run_url=workflow_run_url,
    )

    np = Nanopub(
        assertion=assertion,
        provenance=provenance,
        pubinfo=pubinfo,
    )

    client = NanopubClient()
    published = client.publish(np)
    return published.nanopub_uri
