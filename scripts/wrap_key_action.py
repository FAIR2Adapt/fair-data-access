"""Wrap a dataset key for a requester in GitHub Actions context."""

import argparse
import base64
import os
import sys

from fair_data_access.keys import wrap_key, save_wrapped_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--did", required=True)
    parser.add_argument("--public-key-pem", required=True, help="Base64-encoded PEM public key")
    args = parser.parse_args()

    # Get the dataset symmetric key from GitHub Secrets
    dataset_key_b64 = os.environ.get("DATASET_KEY")
    if not dataset_key_b64:
        print(f"ERROR: No DATASET_KEY secret configured for {args.dataset}")
        sys.exit(1)

    dataset_key = base64.b64decode(dataset_key_b64)
    recipient_pubkey_pem = base64.b64decode(args.public_key_pem)

    wrapped = wrap_key(dataset_key, recipient_pubkey_pem)

    # Save wrapped key
    did_hash = _sha256(args.did)
    output_path = f"docs/keys/{did_hash}/{args.dataset}.key"
    save_wrapped_key(wrapped, output_path)

    output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")
    with open(output_file, "a") as f:
        f.write(f"wrapped_key_path={output_path}\n")

    print(f"Wrapped key saved to: {output_path}")


def _sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


if __name__ == "__main__":
    main()
