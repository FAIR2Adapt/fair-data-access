"""CLI for fair-data-access.

Commands:
  encrypt     Encrypt a data file
  decrypt     Decrypt an encrypted data file
  keygen      Generate a DID keypair
  did-doc     Create a did.json document from a public key
  policy      Create an ODRL policy
  wrap-key    Wrap a dataset key for a recipient DID
"""

import argparse
import base64
import json
import sys
from pathlib import Path


def cmd_encrypt(args):
    from fair_data_access.encrypt import encrypt_file, generate_key

    key = None
    if args.key:
        key = base64.b64decode(args.key)

    output_path, key = encrypt_file(args.input, args.output, key)
    key_b64 = base64.b64encode(key).decode()

    print(f"Encrypted: {output_path}")
    print(f"Key (base64, store securely): {key_b64}")

    if args.save_key:
        Path(args.save_key).write_text(key_b64)
        print(f"Key saved to: {args.save_key}")


def cmd_decrypt(args):
    from fair_data_access.encrypt import decrypt_file

    key = base64.b64decode(args.key)
    output_path = decrypt_file(args.input, args.output, key)
    print(f"Decrypted: {output_path}")


def cmd_keygen(args):
    from fair_data_access.keys import generate_did_keypair

    private_pem, public_pem = generate_did_keypair()

    private_path = Path(args.output_dir) / "private_key.pem"
    public_path = Path(args.output_dir) / "public_key.pem"

    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)

    print(f"Private key: {private_path}")
    print(f"Public key:  {public_path}")
    print("Keep the private key secret. Share the public key in your DID document.")


def cmd_did_doc(args):
    from fair_data_access.did import create_did_document

    public_pem = Path(args.public_key).read_bytes()
    doc = create_did_document(args.did, public_pem)

    output = Path(args.output) if args.output else Path("did.json")
    output.write_text(json.dumps(doc, indent=2))
    print(f"DID document written to: {output}")
    print(f"Serve this at: https://{args.did.split(':')[2]}/.well-known/did.json")


def cmd_policy(args):
    from fair_data_access.policy import create_policy, save_policy

    permissions = []
    if args.permit_actions:
        perm = {"action": args.permit_actions}
        if args.purpose:
            perm["constraint"] = {
                "leftOperand": "purpose",
                "operator": "eq",
                "rightOperand": args.purpose,
            }
        permissions.append(perm)

    prohibitions = []
    if args.prohibit_actions:
        prohibitions.append({"action": args.prohibit_actions})

    duties = []
    if args.require_attribution:
        duties.append({"action": "attribute"})

    policy = create_policy(
        policy_uid=args.uid,
        target=args.target,
        permissions=permissions or None,
        prohibitions=prohibitions or None,
        duties=duties or None,
    )

    output = Path(args.output) if args.output else Path("policy.jsonld")
    save_policy(policy, output)
    print(f"Policy written to: {output}")
    print(json.dumps(policy, indent=2))


def cmd_wrap_key(args):
    from fair_data_access.keys import wrap_key, save_wrapped_key
    from fair_data_access.did import resolve_did, get_public_key_pem

    dataset_key = base64.b64decode(args.dataset_key)

    if args.public_key:
        recipient_pubkey = Path(args.public_key).read_bytes()
    else:
        did_doc = resolve_did(args.did)
        recipient_pubkey = get_public_key_pem(did_doc)

    wrapped = wrap_key(dataset_key, recipient_pubkey)
    output = Path(args.output) if args.output else Path(f"wrapped_key.json")
    save_wrapped_key(wrapped, output)
    print(f"Wrapped key written to: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="ODRL-based access control for FAIR data",
    )
    sub = parser.add_subparsers(dest="command")

    # encrypt
    p = sub.add_parser("encrypt", help="Encrypt a data file")
    p.add_argument("input", help="Input file to encrypt")
    p.add_argument("-o", "--output", help="Output path (default: input.enc)")
    p.add_argument("-k", "--key", help="AES-256 key (base64). Generated if omitted.")
    p.add_argument("--save-key", help="Save key to this file")

    # decrypt
    p = sub.add_parser("decrypt", help="Decrypt a file")
    p.add_argument("input", help="Encrypted file")
    p.add_argument("-k", "--key", required=True, help="AES-256 key (base64)")
    p.add_argument("-o", "--output", help="Output path")

    # keygen
    p = sub.add_parser("keygen", help="Generate a DID keypair")
    p.add_argument("-d", "--output-dir", default=".", help="Output directory")

    # did-doc
    p = sub.add_parser("did-doc", help="Create a DID document")
    p.add_argument("did", help="Your DID (e.g., did:web:fair2adapt.eu)")
    p.add_argument("public_key", help="Path to public_key.pem")
    p.add_argument("-o", "--output", help="Output path (default: did.json)")

    # policy
    p = sub.add_parser("policy", help="Create an ODRL policy")
    p.add_argument("--uid", required=True, help="Policy URI")
    p.add_argument("--target", required=True, help="Dataset URI")
    p.add_argument("--permit-actions", nargs="+", help="Permitted actions")
    p.add_argument("--prohibit-actions", nargs="+", help="Prohibited actions")
    p.add_argument("--purpose", help="Required purpose constraint")
    p.add_argument("--require-attribution", action="store_true")
    p.add_argument("-o", "--output", help="Output path")

    # wrap-key
    p = sub.add_parser("wrap-key", help="Wrap a dataset key for a recipient")
    p.add_argument("--dataset-key", required=True, help="Dataset key (base64)")
    p.add_argument("--did", help="Recipient DID (resolved to get public key)")
    p.add_argument("--public-key", help="Recipient public key PEM file (alternative to DID)")
    p.add_argument("-o", "--output", help="Output path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "encrypt": cmd_encrypt,
        "decrypt": cmd_decrypt,
        "keygen": cmd_keygen,
        "did-doc": cmd_did_doc,
        "policy": cmd_policy,
        "wrap-key": cmd_wrap_key,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
