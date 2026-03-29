"""Parse a GitHub Issue body from the access-request template.

Extracts dataset, DID, purpose, and affiliation fields
and sets them as GitHub Actions outputs.
"""

import os
import re
import sys


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


def main():
    body = sys.argv[1]
    fields = parse_issue_body(body)

    if not fields.get("dataset") or not fields.get("did"):
        print("ERROR: Could not parse required fields from issue body")
        sys.exit(1)

    # Convert dataset id to GitHub Secret name format
    # e.g., "hamburg-buildings" → "HAMBURG_BUILDINGS"
    dataset_secret_name = fields["dataset"].upper().replace("-", "_")

    # Write GitHub Actions outputs
    output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")
    with open(output_file, "a") as f:
        f.write(f"dataset={fields['dataset']}\n")
        f.write(f"did={fields['did']}\n")
        f.write(f"purpose={fields.get('purpose', '')}\n")
        f.write(f"affiliation={fields.get('affiliation', '')}\n")
        f.write(f"dataset_secret_name={dataset_secret_name}\n")

    print(f"Parsed request: dataset={fields['dataset']}, did={fields['did']}, purpose={fields.get('purpose')}")


if __name__ == "__main__":
    main()
