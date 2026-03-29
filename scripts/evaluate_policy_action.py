"""Evaluate an ODRL policy for a GitHub Actions access request.

Loads the policy for the requested dataset, evaluates it against
the requester's DID and declared purpose, and outputs the decision.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from fair_data_access.policy import load_policy, evaluate_policy


# Map dataset IDs to their ODRL policy files (or nanopub URIs)
POLICY_DIR = Path(__file__).parent.parent / "policies"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--did", required=True)
    parser.add_argument("--purpose", default="")
    args = parser.parse_args()

    # Look for a local policy file first, fall back to nanopub
    policy_file = POLICY_DIR / f"{args.dataset}.jsonld"
    if policy_file.exists():
        policy = load_policy(policy_file)
        policy_uri = policy.get("uid", str(policy_file))
    else:
        # Try to fetch from nanopub network
        from fair_data_access.policy import fetch_policy
        # Policy nanopub URIs should be configured in a dataset registry
        registry_file = POLICY_DIR / "registry.json"
        if registry_file.exists():
            registry = json.loads(registry_file.read_text())
            nanopub_uri = registry.get(args.dataset, {}).get("policy_nanopub")
            if nanopub_uri:
                policy = fetch_policy(nanopub_uri)
                policy_uri = nanopub_uri
            else:
                print(f"No policy found for dataset: {args.dataset}")
                _set_output("decision", "deny")
                _set_output("reason", f"No policy configured for dataset '{args.dataset}'")
                sys.exit(0)
        else:
            print(f"No policy file or registry found for dataset: {args.dataset}")
            _set_output("decision", "deny")
            _set_output("reason", f"No policy configured for dataset '{args.dataset}'")
            sys.exit(0)

    # Evaluate
    decision = evaluate_policy(
        policy,
        requester_did=args.did,
        purpose=args.purpose,
    )

    if decision:
        print(f"PERMIT: {args.did} may access {args.dataset} for purpose={args.purpose}")
        _set_output("decision", "permit")
        _set_output("policy_nanopub_uri", policy_uri)
    else:
        reason = f"Policy constraints not satisfied (purpose={args.purpose})"
        print(f"DENY: {reason}")
        _set_output("decision", "deny")
        _set_output("reason", reason)


def _set_output(name: str, value: str):
    output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")
    with open(output_file, "a") as f:
        f.write(f"{name}={value}\n")


if __name__ == "__main__":
    main()
