"""Resolve a DID and extract the public key for GitHub Actions."""

import base64
import os
import sys

from fair_data_access.did import resolve_did, get_public_key_pem


def main():
    did = sys.argv[1]

    try:
        did_doc = resolve_did(did)
        public_key_pem = get_public_key_pem(did_doc)
        pubkey_b64 = base64.b64encode(public_key_pem).decode()

        output_file = os.environ.get("GITHUB_OUTPUT", "/dev/stdout")
        with open(output_file, "a") as f:
            f.write(f"public_key_pem_b64={pubkey_b64}\n")

        print(f"Resolved DID: {did}")
        print(f"Public key extracted from verification method")
    except Exception as e:
        print(f"ERROR resolving DID {did}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
