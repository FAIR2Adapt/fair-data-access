"""Tests for RO-Crate integration of encrypted, policy-controlled data."""

import json

import pytest
import rdflib

from fair_data_access import rocrate
from fair_data_access.encrypt import encrypt_file, generate_key
from fair_data_access.keys import generate_did_keypair, wrap_key

POLICY = "https://w3id.org/np/RAkCc5ernqtkD4bGumI2wsJOC14-jy1sbYtWwukTL_bgM"
KEY_SERVER = "https://fair2adapt.github.io/fair-data-access"
DID = "did:web:example.org:consumer"


def _crate(tmp_path):
    path = tmp_path / "ro-crate-metadata.json"
    path.write_text(json.dumps({
        "@context": rocrate.RO_CRATE_CONTEXT,
        "@graph": [{"@id": "./", "@type": "Dataset", "hasPart": []}],
    }))
    return path


def test_declare_access_terms_is_idempotent_and_keeps_existing_terms():
    crate = {"@context": [rocrate.RO_CRATE_CONTEXT, {"mine": "http://example.org/mine"}]}
    rocrate.declare_access_terms(crate)
    rocrate.declare_access_terms(crate)
    assert crate["@context"][0] == rocrate.RO_CRATE_CONTEXT
    local = crate["@context"][1]
    assert local["mine"] == "http://example.org/mine"
    assert local["hasPolicy"]["@id"] == "http://www.w3.org/ns/odrl/2/hasPolicy"
    assert len(crate["@context"]) == 2


def test_policy_link_is_linked_data(tmp_path):
    path = _crate(tmp_path)
    rocrate.add_encrypted_file_to_crate(
        path, "data.gpkg.enc", "Data", "Encrypted data", "application/geopackage+sqlite3",
        POLICY, KEY_SERVER, conditions_of_access="Academic research only",
    )
    crate = json.loads(path.read_text())
    entry = next(e for e in crate["@graph"] if e["@id"] == "data.gpkg.enc")
    assert entry["accessRights"] == {"@id": rocrate.ACCESS_RESTRICTED}
    assert entry["conditionsOfAccess"] == "Academic research only"

    # Parse as JSON-LD (remote RO-Crate context swapped for a local stand-in)
    crate["@context"][0] = {"@vocab": "http://schema.org/"}
    g = rdflib.Graph().parse(data=json.dumps(crate), format="json-ld", base="http://example.org/crate/")
    s = rdflib.URIRef("http://example.org/crate/data.gpkg.enc")
    odrl = rdflib.Namespace("http://www.w3.org/ns/odrl/2/")
    dct = rdflib.Namespace("http://purl.org/dc/terms/")
    assert (s, odrl.hasPolicy, rdflib.URIRef(POLICY)) in g
    assert (s, dct.accessRights, rdflib.URIRef(rocrate.ACCESS_RESTRICTED)) in g
    enc = next(g.objects(s, rdflib.URIRef(rocrate.SCIENCELIVE_TERMS + "contentEncryption")))
    assert (enc, rdflib.URIRef(rocrate.SCIENCELIVE_TERMS + "keyServer"), rdflib.URIRef(KEY_SERVER)) in g


def test_load_encrypted_input_fetches_key_at_workflow_path(tmp_path, monkeypatch):
    private_pem, public_pem = generate_did_keypair()
    dataset_key = generate_key()
    plain = tmp_path / "data.gpkg"
    plain.write_bytes(b"37 building footprints")
    enc = tmp_path / "data.gpkg.enc"
    encrypt_file(str(plain), output_path=str(enc), key=dataset_key)
    wrapped = wrap_key(dataset_key, public_pem)

    requested = []

    class Response:
        content = wrapped

        def raise_for_status(self):
            pass

    import httpx
    monkeypatch.setattr(httpx, "get", lambda url, **kw: requested.append(url) or Response())

    entry = {"@id": str(enc), "contentEncryption": {"algorithm": "AES-256-GCM", "keyServer": KEY_SERVER + "/"}}
    out = rocrate.load_encrypted_input(entry, private_pem, requester_did=DID, dataset="hamburg-buildings")
    assert out == b"37 building footprints"
    assert requested == [f"{KEY_SERVER}/keys/{rocrate.did_hash(DID)}/hamburg-buildings.key"]


def test_load_encrypted_input_needs_did_and_dataset_for_key_server():
    entry = {"@id": "x.enc", "contentEncryption": {"keyServer": KEY_SERVER}}
    with pytest.raises(ValueError, match="requester_did"):
        rocrate.load_encrypted_input(entry, b"")
