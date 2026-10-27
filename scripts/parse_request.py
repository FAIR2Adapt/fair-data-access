"""Parse and validate a GitHub Issue body from the access-request template.

The issue body is untrusted input from any GitHub user. It is read from the
ISSUE_BODY environment variable (never interpolated into a shell command),
and only fields that pass strict validation are written as GitHub Actions
outputs:

- dataset must be a key of policies/registry.json
- did must be a well-formed did:web identifier
- purpose must be one of the DPV purposes offered by the template, or "Other"

If validation fails, valid=false and a fixed reason are written instead.
"""

import json
import os
import re
import sys
from pathlib import Path


REGISTRY_FILE = Path(__file__).parent.parent / "policies" / "registry.json"

DATASET_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
# did:web:<host>[%3A<port>][:<path-segment>]*
DID_WEB_RE = re.compile(
    r"^did:web:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?(?:%3A[0-9]{1,5})?"
    r"(?::[A-Za-z0-9._~-]{1,128}){0,16}$"
)
DPV_PURPOSE_RE = re.compile(r"\((https://w3id\.org/dpv#[A-Za-z]{1,64})\)\s*$")


def parse_issue_body(body: str) -> dict:
    """Parse structured fields from the issue body."""
    fields = {}

    patterns = {
        "dataset": r"### Dataset ID\s*\n\s*(.+)",
        "did": r"### Your DID\s*\n\s*(.+)",
        "purpose": r"### Purpose\s*\n\s*(.+)",
        "affiliation": r"### Affiliation\s*\n\s*(.+)",
        "justification": r"### Justification\s*\n\s*([\s\S]+?)(?=###|$)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, body)
        if match:
            fields[field] = match.group(1).strip()

    return fields


def load_registry_ids(registry_file: Path = REGISTRY_FILE) -> set[str]:
    """Return the dataset IDs configured in the policy registry."""
    if not registry_file.exists():
        return set()
    return set(json.loads(registry_file.read_text()))


def validate_request(fields: dict, dataset_ids: set[str]) -> tuple[dict | None, str]:
    """Validate parsed fields.

    Returns (validated_fields, "") on success, or (None, reason) on failure.
    Reasons are fixed strings so that no user input is echoed back.
    """
    dataset = fields.get("dataset", "")
    did = fields.get("did", "")
    purpose_line = fields.get("purpose", "")

    if not DATASET_RE.fullmatch(dataset) or dataset not in dataset_ids:
        return None, "Unknown dataset ID"
    if not DID_WEB_RE.fullmatch(did):
        return None, "Invalid DID: only did:web identifiers are supported"

    match = DPV_PURPOSE_RE.search(purpose_line)
    if match:
        purpose = match.group(1)
    elif purpose_line == "Other":
        purpose = "Other"
    else:
        return None, "Invalid purpose"

    return {
        "dataset": dataset,
        "did": did,
        "purpose": purpose,
        # e.g., "hamburg-buildings" → "HAMBURG_BUILDINGS" (GitHub Secret name format)
        "dataset_secret_name": dataset.upper().replace("-", "_"),
    }, ""


def main():
    body = os.environ.get("ISSUE_BODY")
    if body is None and len(sys.argv) > 1:
        body = sys.argv[1]
    fields = parse_issue_body(body or "")

    validated, reason = validate_request(fields, load_registry_ids())

    output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")
    with open(output_file, "a") as f:
        if validated is None:
            f.write("valid=false\n")
            f.write(f"reason={reason}\n")
        else:
            f.write("valid=true\n")
            for key, value in validated.items():
                f.write(f"{key}={value}\n")

    if validated is None:
        print(f"Rejected request: {reason}")
    else:
        print(
            f"Parsed request: dataset={validated['dataset']}, "
            f"did={validated['did']}, purpose={validated['purpose']}"
        )


if __name__ == "__main__":
    main()
