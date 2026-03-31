"""Verify an ODRL Access Grant for a GitHub Actions access request.

Checks that the data provider has published a valid ODRL Access Grant
for FAIR Data nanopub for this requester + dataset, with verified
signature and creator match against the policy publisher.

Flow:
1. Requester opens a GitHub Issue requesting access
2. Data provider reviews and publishes a grant via Nanodash
3. Requester triggers this workflow (or it runs on issue label)
4. This script verifies the grant nanopub exists and is valid
5. If valid → key is wrapped and released
"""

import argparse
import json
import os
import sys
from pathlib import Path

from fair_data_access.grant import verify_access


POLICY_DIR = Path(__file__).parent.parent / "policies"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--did", required=True)
    parser.add_argument("--purpose", default="")  # kept for logging, not used for decisions
    args = parser.parse_args()

    # Load registry to get the policy nanopub URI
    registry_file = POLICY_DIR / "registry.json"
    if not registry_file.exists():
        print(f"No registry found")
        _set_output("decision", "deny")
        _set_output("reason", "No policy registry configured")
        sys.exit(0)

    registry = json.loads(registry_file.read_text())
    dataset_entry = registry.get(args.dataset, {})
    policy_nanopub = dataset_entry.get("policy_nanopub")

    if not policy_nanopub:
        print(f"No policy nanopub configured for dataset: {args.dataset}")
        _set_output("decision", "deny")
        _set_output("reason", f"No policy configured for dataset '{args.dataset}'")
        sys.exit(0)

    # Build the dataset URI from the registry convention
    dataset_uri = f"https://fair2adapt.eu/data/{args.dataset}"

    print(f"Dataset:   {args.dataset} ({dataset_uri})")
    print(f"Requester: {args.did}")
    print(f"Policy:    {policy_nanopub}")
    print()

    # Verify that a valid grant nanopub exists
    result = verify_access(
        dataset_uri=dataset_uri,
        requester_did=args.did,
        policy_nanopub_uri=policy_nanopub,
    )

    if result["granted"]:
        print(f"\nPERMIT: valid grant found")
        print(f"  Grant:   {result['grant_nanopub']}")
        print(f"  Creator: {result['grant_creator']}")
        _set_output("decision", "permit")
        _set_output("policy_nanopub_uri", policy_nanopub)
        _set_output("grant_nanopub_uri", result["grant_nanopub"])
    else:
        reason = result["reason"]
        print(f"\nDENY: {reason}")
        _set_output("decision", "deny")
        _set_output("reason", reason)
        _set_output("policy_nanopub_uri", policy_nanopub)


def _set_output(name: str, value: str):
    output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")
    with open(output_file, "a") as f:
        f.write(f"{name}={value}\n")


if __name__ == "__main__":
    main()
