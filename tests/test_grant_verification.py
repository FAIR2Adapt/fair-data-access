"""Tests for grant verification: issuer key, policy link and retractions.

Network access is replaced by in-memory nanopubs; signature checking is
stubbed so the tests focus on which signed records are trusted.
"""

import pytest

from fair_data_access import grant as g
from fair_data_access.policy import evaluate_policy

POLICY = "https://w3id.org/np/RApolicy"
OTHER_POLICY = "https://w3id.org/np/RAother"
GRANT = "https://w3id.org/np/RAgrant"
DATASET = "https://fair2adapt.eu/data/hamburg-buildings"
DID = "did:web:example.org:consumer"
PROVIDER_KEY = "PROVIDERKEY"
ATTACKER_KEY = "ATTACKERKEY"
ORCID = "https://orcid.org/0000-0002-1784-2920"


def _nanopub(uri, key, assertion="", algorithm="RSA", extra_pubinfo=""):
    return f"""
@prefix np: <http://www.nanopub.org/nschema#> .
@prefix npx: <http://purl.org/nanopub/x/> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix odrl: <http://www.w3.org/ns/odrl/2/> .
@prefix fair: <https://fair2adapt.eu/ns/> .

<{uri}/Head> {{
  <{uri}> a np:Nanopublication ;
    np:hasAssertion <{uri}/assertion> ;
    np:hasProvenance <{uri}/provenance> ;
    np:hasPublicationInfo <{uri}/pubinfo> .
}}
<{uri}/assertion> {{ {assertion} }}
<{uri}/provenance> {{ }}
<{uri}/pubinfo> {{
  <{uri}> dct:creator <{ORCID}> .
  {extra_pubinfo}
  <{uri}/sig> npx:hasSignatureTarget <{uri}> ; npx:hasAlgorithm "{algorithm}" ;
    npx:hasPublicKey "{key}" ; npx:signedBy <{ORCID}> .
}}
"""


def _grant(uri=GRANT, key=PROVIDER_KEY, policy=POLICY, assignee=DID, **kwargs):
    return _nanopub(uri, key, assertion=f"""
  <{uri}/grant> a odrl:Agreement ;
    odrl:target <{DATASET}> ;
    odrl:assignee <{assignee}> ;
    fair:underPolicy <{policy}> .""", **kwargs)


@pytest.fixture
def network(monkeypatch):
    """A fake nanopub network: uri -> TriG, plus retraction index."""
    store = {POLICY: _nanopub(POLICY, PROVIDER_KEY)}
    retractions = {}
    monkeypatch.setattr(g, "fetch_nanopub_trig", lambda uri: store[uri])
    monkeypatch.setattr(g, "signature_is_valid", lambda trig: True)
    monkeypatch.setattr(
        g, "find_grants",
        lambda dataset, did: [{"nanopub_uri": u, "creator": ORCID}
                              for u in store if u not in (POLICY,) and "retract" not in u],
    )
    monkeypatch.setattr(g, "find_retractions", lambda uri: retractions.get(uri, []))
    return store, retractions


def test_grant_signed_with_policy_key_is_accepted(network):
    store, _ = network
    store[GRANT] = _grant()
    assert g.verify_access(DATASET, DID, POLICY)["granted"]


def test_grant_claiming_provider_orcid_but_other_key_is_rejected(network):
    store, _ = network
    store[GRANT] = _grant(key=ATTACKER_KEY)  # same dct:creator, different key
    result = g.verify_access(DATASET, DID, POLICY)
    assert not result["granted"]


def test_decoy_provider_key_in_pubinfo_is_ignored(network):
    store, _ = network
    # Signed with the attacker's key, plus a stray triple naming the provider's key
    store[GRANT] = _grant(
        key=ATTACKER_KEY,
        extra_pubinfo=f'<{GRANT}/decoy> npx:hasPublicKey "{PROVIDER_KEY}" .',
    )
    assert not g.verify_access(DATASET, DID, POLICY)["granted"]


def test_dsa_signature_is_rejected(network):
    # The nanopub library reports DSA signatures valid without checking them
    store, _ = network
    store[GRANT] = _grant(algorithm="DSA")
    assert not g.verify_access(DATASET, DID, POLICY)["granted"]


def test_grant_under_another_policy_is_rejected(network):
    store, _ = network
    store[GRANT] = _grant(policy=OTHER_POLICY)
    assert not g.verify_access(DATASET, DID, POLICY)["granted"]


def test_grant_for_another_requester_is_rejected(network):
    store, _ = network
    store[GRANT] = _grant(assignee="did:web:example.org:someone-else")
    assert not g.verify_access(DATASET, DID, POLICY)["granted"]


def test_policy_link_matches_across_namespaces(network):
    store, _ = network
    store[GRANT] = _grant(policy="https://w3id.org/sciencelive/np/RApolicy")
    assert g.verify_access(DATASET, DID, POLICY)["granted"]


def test_retraction_by_issuer_revokes_grant(network):
    store, retractions = network
    store[GRANT] = _grant()
    store["https://w3id.org/np/RAretract"] = _nanopub("https://w3id.org/np/RAretract", PROVIDER_KEY)
    retractions[GRANT] = ["https://w3id.org/np/RAretract"]
    assert not g.verify_access(DATASET, DID, POLICY)["granted"]


def test_retraction_by_someone_else_is_ignored(network):
    store, retractions = network
    store[GRANT] = _grant()
    store["https://w3id.org/np/RAretract"] = _nanopub("https://w3id.org/np/RAretract", ATTACKER_KEY)
    retractions[GRANT] = ["https://w3id.org/np/RAretract"]
    assert g.verify_access(DATASET, DID, POLICY)["granted"]


def _policy(*constraints):
    return {"permission": [{"action": "use", "constraint": list(constraints)}]}


PURPOSE_EQ = {"leftOperand": "purpose", "operator": "eq",
              "rightOperand": "https://w3id.org/dpv#AcademicResearch"}


def test_purpose_constraint_is_evaluated():
    assert evaluate_policy(_policy(PURPOSE_EQ), purpose="AcademicResearch")
    assert not evaluate_policy(_policy(PURPOSE_EQ), purpose="CommercialResearch")


@pytest.mark.parametrize("constraint", [
    {"leftOperand": "dateTime", "operator": "lt", "rightOperand": "2020-01-01"},
    {"leftOperand": "spatial", "operator": "eq", "rightOperand": "https://example.org/de"},
    {"leftOperand": "purpose", "operator": "isA", "rightOperand": "https://w3id.org/dpv#ResearchAndDevelopment"},
])
def test_unsupported_constraints_fail_closed(constraint):
    assert not evaluate_policy(_policy(PURPOSE_EQ, constraint), purpose="AcademicResearch")
