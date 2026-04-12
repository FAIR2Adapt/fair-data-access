# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Chapter 0 — Set up your decentralised identity (DID)
#
# Before you can request access to a protected dataset, you need a
# **decentralised identifier** — a cryptographic identity that stays with you
# across institutions.
#
# ```{admonition} One-time setup
# :class: tip
# You do this **once**. The identity you create here works for every dataset
# request you ever make through the FAIR2Adapt framework.
# ```
#
# ## What is a DID?
#
# A DID is a URL-like string that points to a small JSON document containing
# your **public key**. Anyone who knows your DID can look up your public key
# and encrypt things specifically for you.
#
# Example: `did:web:yourname.github.io:my-did:researcher`
#
# This resolves to: `https://yourname.github.io/my-did/researcher/did.json`
#
# The JSON file at that URL is your **DID document** — it contains your
# public key but **never** your private key.
#
# ## Why not just use ORCID?
#
# ORCID is great for **attribution** (who published what). But ORCID doesn't
# give you a **cryptographic key** — you can't encrypt a dataset key for an
# ORCID. DIDs add the key management layer that ORCID doesn't provide.
#
# In practice, a researcher has both: ORCID for citations, DID for data access.

# %% [markdown]
# ## Step 1 — Generate your keypair
#
# This creates an EC P-256 keypair. The private key stays on your machine.
# The public key goes into your DID document.
#
# ```{warning}
# Your **private key is your identity**. Anyone with it can impersonate you
# and decrypt data meant for you. Treat it like a password. If you lose it,
# generate a new keypair and update your DID document.
# ```

# %%
from pathlib import Path
from fair_data_access.keys import generate_did_keypair

KEYS_DIR = Path("keys")

# For this walkthrough we use the pre-generated example consumer identity.
# To create your own, uncomment the block below.

CONSUMER_PRIVATE_KEY = KEYS_DIR / "example-consumer-private.pem"
CONSUMER_PUBLIC_KEY = KEYS_DIR / "example-consumer-public.pem"

if CONSUMER_PRIVATE_KEY.exists():
    print(f"Using existing keypair at {CONSUMER_PRIVATE_KEY}")
    private_pem = CONSUMER_PRIVATE_KEY.read_bytes()
    public_pem = CONSUMER_PUBLIC_KEY.read_bytes()
else:
    print("Generating a new consumer keypair...")
    private_pem, public_pem = generate_did_keypair()
    CONSUMER_PRIVATE_KEY.write_bytes(private_pem)
    CONSUMER_PUBLIC_KEY.write_bytes(public_pem)
    print(f"Saved private key to {CONSUMER_PRIVATE_KEY} (gitignored)")
    print(f"Saved public key to {CONSUMER_PUBLIC_KEY}")

# %%
# Show the public key (this is safe to share — it's public by design)
print("=== Public key (safe to share) ===")
print(public_pem.decode())

# %% [markdown]
# ## Step 2 — Create your DID document
#
# The DID document is a small JSON-LD file that maps your DID string to your
# public key. It follows the [W3C DID Core](https://www.w3.org/TR/did-core/)
# specification.

# %%
import json
from fair_data_access.did import create_did_document

# For the walkthrough, we use a DID under the fair2adapt GitHub Pages domain.
# When you create your own, replace this with your domain.
CONSUMER_DID = "did:web:fair2adapt.github.io:fair-data-access:example-consumer"

did_document = create_did_document(CONSUMER_DID, public_pem)

print("=== DID Document ===")
print(json.dumps(did_document, indent=2))

# %% [markdown]
# The document above is what the world sees when they resolve your DID. It
# contains:
#
# - **`id`** — your DID string (the identifier)
# - **`verificationMethod`** — your public key in JWK format
# - **`authentication`** / **`assertionMethod`** — which key to use for
#   authentication and signing
#
# Notice: **no private key anywhere in the document.**

# %% [markdown]
# ## Step 3 — Publish the DID document
#
# "Publishing" means putting the JSON file at the URL your DID resolves to.
# For `did:web:yourname.github.io:my-did:researcher`, the URL is:
#
# ```
# https://yourname.github.io/my-did/researcher/did.json
# ```
#
# ### Option A: GitHub Pages (recommended, free, 5 minutes)
#
# ```bash
# # One-time setup
# gh repo create my-did --public --description "My DID document"
# cd my-did
# mkdir -p researcher
# # Copy the DID document generated above
# cp /path/to/did.json researcher/did.json
# git add . && git commit -m "Publish DID document"
# git push
# # Enable GitHub Pages on the repo (main branch, root directory)
# gh repo edit --enable-pages --pages-branch main --pages-path /
# ```
#
# After a minute, your DID is live at
# `https://yourname.github.io/my-did/researcher/did.json`
#
# ### Option B: Institutional web server
#
# Ask your IT department to serve `did.json` at an institutional URL, e.g.
# `https://university.edu/researchers/alice/did.json`. Your DID becomes
# `did:web:university.edu:researchers:alice`.
#
# ### Option C: Personal website
#
# If you have `https://alice.example.com`, put `did.json` at the root. Your
# DID is `did:web:alice.example.com`.
#
# ---
#
# For this walkthrough, the example DID documents are already committed in
# `keys/did/` and would be served via GitHub Pages at:
# - `https://fair2adapt.github.io/fair-data-access/example-provider/did.json`
# - `https://fair2adapt.github.io/fair-data-access/example-consumer/did.json`

# %% [markdown]
# ## Step 4 — Verify your DID resolves
#
# Once published, anyone can resolve your DID and retrieve your public key.
# The `fair_data_access` library does this automatically when wrapping keys.

# %%
# For the walkthrough, we load the DID document from a local file
# instead of resolving it over the network (since the GitHub Pages
# hosting may not be set up yet for this walkthrough).

did_doc_path = KEYS_DIR / "did" / "example-consumer.json"
resolved_doc = json.loads(did_doc_path.read_text())

print("=== Resolved DID Document ===")
print(f"DID: {resolved_doc['id']}")
print(f"Key type: {resolved_doc['verificationMethod'][0]['type']}")
print(f"Curve: {resolved_doc['verificationMethod'][0]['publicKeyJwk']['crv']}")
print()
print("The provider will use the public key above to wrap the dataset")
print("key specifically for you. Only your private key can unwrap it.")

# %% [markdown]
# ## Summary
#
# You now have:
#
# | What | Where | Who can see it |
# |------|-------|----------------|
# | **Private key** | `keys/example-consumer-private.pem` (your machine, gitignored) | Only you |
# | **Public key** | `keys/example-consumer-public.pem` (committed) | Everyone |
# | **DID document** | `keys/did/example-consumer.json` (published via web) | Everyone |
# | **DID string** | `did:web:fair2adapt.github.io:fair-data-access:example-consumer` | Everyone |
#
# This identity is permanent and portable. You can use it to request access
# to **any dataset** protected by the FAIR2Adapt framework — or any other
# system that supports `did:web` resolution.
#
# **Next:** [Chapter 1 — Provider: encrypt and publish a policy](01_provider.ipynb)
