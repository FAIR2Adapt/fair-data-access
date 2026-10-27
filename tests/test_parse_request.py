"""Tests for validation of untrusted access-request issue bodies."""

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "parse_request", Path(__file__).parent.parent / "scripts" / "parse_request.py"
)
parse_request = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parse_request)

DATASETS = {"hamburg-buildings"}


def _body(dataset="hamburg-buildings",
          did="did:web:fair2adapt.github.io:fair-data-access",
          purpose="Academic Research (https://w3id.org/dpv#AcademicResearch)"):
    return (
        f"### Dataset ID\n\n{dataset}\n\n"
        f"### Your DID\n\n{did}\n\n"
        f"### Purpose\n\n{purpose}\n\n"
        "### Affiliation\n\nLifewatch ERIC\n\n"
        "### Justification\n\nTesting.\n"
    )


def _validate(body):
    return parse_request.validate_request(parse_request.parse_issue_body(body), DATASETS)


def test_valid_request_is_accepted():
    fields, reason = _validate(_body())
    assert reason == ""
    assert fields == {
        "dataset": "hamburg-buildings",
        "did": "did:web:fair2adapt.github.io:fair-data-access",
        "purpose": "https://w3id.org/dpv#AcademicResearch",
        "dataset_secret_name": "HAMBURG_BUILDINGS",
    }


def test_other_purpose_is_accepted():
    fields, _ = _validate(_body(purpose="Other"))
    assert fields["purpose"] == "Other"


def test_did_with_port_is_accepted():
    fields, _ = _validate(_body(did="did:web:localhost%3A8443:user"))
    assert fields["did"] == "did:web:localhost%3A8443:user"


@pytest.mark.parametrize("dataset", [
    "unknown-dataset",
    'hamburg-buildings"; echo pwned; "',
    "hamburg-buildings$(id)",
    "../hamburg-buildings",
    "HAMBURG-BUILDINGS",
])
def test_bad_dataset_is_rejected(dataset):
    fields, reason = _validate(_body(dataset=dataset))
    assert fields is None
    assert reason == "Unknown dataset ID"


@pytest.mark.parametrize("did", [
    'did:web:example.org"; echo pwned; "',
    "did:web:example.org:$(id)",
    "did:web:example.org:`id`",
    "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
    "https://example.org/did.json",
    "did:web:",
])
def test_bad_did_is_rejected(did):
    fields, reason = _validate(_body(did=did))
    assert fields is None
    assert reason.startswith("Invalid DID")


@pytest.mark.parametrize("purpose", [
    "Academic Research (https://w3id.org/dpv#AcademicResearch)$(id)",
    "Academic Research (https://evil.example/#x)",
    "anything",
])
def test_bad_purpose_is_rejected(purpose):
    fields, reason = _validate(_body(purpose=purpose))
    assert fields is None
    assert reason == "Invalid purpose"


def test_rejection_does_not_echo_input(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setenv("ISSUE_BODY", _body(dataset="evil\ndecision=permit"))
    monkeypatch.setattr(parse_request, "load_registry_ids", lambda: DATASETS)
    parse_request.main()
    lines = out.read_text().splitlines()
    assert lines == ["valid=false", "reason=Unknown dataset ID"]
