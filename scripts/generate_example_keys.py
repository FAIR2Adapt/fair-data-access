#!/usr/bin/env python3
"""Ensure a self-contained example *consumer* identity exists for the demo.

The private half of the example identity is deliberately never committed
(`.gitignore` excludes `*-private.pem`; CI injects it from a GitHub Secret).
So that `pixi run run` works on a fresh clone with **zero secrets**, this
script mints a matched triple when the private key is absent:

    keys/example-consumer-private.pem   (gitignored)
    keys/example-consumer-public.pem    (committed — overwritten locally)
    keys/did/example-consumer.json      (committed — overwritten locally)

The three MUST match: `01_provider.py` wraps the dataset key for the public key
in the DID document, and `02_consumer.py` unwraps it with the private key.
Regenerating only when the private key is missing keeps repeat runs stable.

If the private key already exists (e.g. CI wrote it from the secret, or a prior
local run generated it), this is a no-op — the canonical committed identity is
left untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

from fair_data_access.did import create_did_document
from fair_data_access.keys import generate_did_keypair

REPO = Path(__file__).resolve().parent.parent
WT = REPO / "examples" / "walkthrough"
KEYS = WT / "keys"
DID_DIR = KEYS / "did"

CONSUMER_DID = "did:web:fair2adapt.github.io:fair-data-access:example-consumer"

PRIVATE = KEYS / "example-consumer-private.pem"
PUBLIC = KEYS / "example-consumer-public.pem"
DID_DOC = DID_DIR / "example-consumer.json"


def main() -> None:
    if PRIVATE.exists():
        print(f"[setup_keys] private key present — using existing identity ({PRIVATE.relative_to(REPO)})")
        return

    print("[setup_keys] no private key found — minting a throwaway example consumer identity")
    KEYS.mkdir(parents=True, exist_ok=True)
    DID_DIR.mkdir(parents=True, exist_ok=True)

    private_pem, public_pem = generate_did_keypair()
    PRIVATE.write_bytes(private_pem)
    PUBLIC.write_bytes(public_pem)

    did_document = create_did_document(CONSUMER_DID, public_pem)
    DID_DOC.write_text(json.dumps(did_document, indent=2) + "\n")

    print(f"[setup_keys] wrote {PRIVATE.relative_to(REPO)} (gitignored)")
    print(f"[setup_keys] wrote {PUBLIC.relative_to(REPO)}")
    print(f"[setup_keys] wrote {DID_DOC.relative_to(REPO)}")


if __name__ == "__main__":
    main()
