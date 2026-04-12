# Cryptographic keys for the walkthrough

## What is committed

| File | Purpose |
|------|---------|
| `example-provider-public.pem` | Provider's EC P-256 public key (for verifying grants) |
| `example-consumer-public.pem` | Consumer's EC P-256 public key (for wrapping dataset keys) |
| `did/example-provider.json` | Provider DID document (JSON-LD, served via GitHub Pages) |
| `did/example-consumer.json` | Consumer DID document (JSON-LD, served via GitHub Pages) |

## What is NOT committed

| File | Why |
|------|-----|
| `*_private.pem` | Private keys are generated on first notebook run and gitignored. Anyone with a private key can impersonate the corresponding identity. |

## These are walkthrough keys

These keys are for the walkthrough only. They correspond to two synthetic
identities used in the example:

- `did:web:fair2adapt.github.io:fair-data-access:example-provider`
- `did:web:fair2adapt.github.io:fair-data-access:example-consumer`

**Do not use these keys for real data.** Generate your own keypair using
`00_setup_did.ipynb` or the CLI:

```bash
fair-data-access keygen -d ~/.fair-data-access/
```
