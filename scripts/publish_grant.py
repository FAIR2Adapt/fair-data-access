"""Publish an access grant nanopublication after approval."""

import argparse
import os

from fair_data_access.nanopub_utils import publish_access_grant


AUTHOR_ORCID = os.environ.get(
    "AUTHOR_ORCID", "https://orcid.org/0000-0002-1784-2920"
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--did", required=True)
    parser.add_argument("--policy-nanopub", required=True)
    parser.add_argument("--workflow-run", default=None)
    args = parser.parse_args()

    dataset_uri = f"https://fair2adapt.eu/data/{args.dataset}"

    try:
        nanopub_uri = publish_access_grant(
            dataset_uri=dataset_uri,
            requester_did=args.did,
            policy_nanopub_uri=args.policy_nanopub,
            actions=["use"],
            author_orcid=AUTHOR_ORCID,
            workflow_run_url=args.workflow_run,
        )
        print(f"Access grant published: {nanopub_uri}")

        output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")
        with open(output_file, "a") as f:
            f.write(f"grant_nanopub_uri={nanopub_uri}\n")
    except Exception as e:
        print(f"WARNING: Could not publish access grant nanopub: {e}")
        print("Access was still granted (key was wrapped), but audit nanopub failed.")


if __name__ == "__main__":
    main()
