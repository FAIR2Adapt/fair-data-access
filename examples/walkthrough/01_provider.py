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
# # Chapter 1 — Provider: encrypt data and publish an ODRL policy
#
# This notebook walks through the **provider side** of the FAIR2Adapt access
# control workflow. You will:
#
# 1. **Encrypt** a dataset with AES-256-GCM
# 2. **Create** an ODRL access policy (JSON-LD)
# 3. **Wrap** the dataset key for a specific consumer's DID
#
# ```{admonition} Production-ready framework
# :class: important
# Every function called below is the same code used to protect the Hamburg
# urban pluvial flood risk dataset. Only the data is synthetic.
# ```

# %% [markdown]
# ## Step 1 — Load and inspect the dataset
#
# The dataset is a small CSV of synthetic Mediterranean biodiversity
# observations. In a real scenario, this would be your sensitive research
# data.

# %%
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")
DATASET_PATH = DATA_DIR / "synthetic-biodiversity-observations.csv"

df = pd.read_csv(DATASET_PATH, comment="#")
print(f"Dataset: {DATASET_PATH}")
print(f"Rows: {len(df)}, Columns: {list(df.columns)}")
df.head()

# %% [markdown]
# ## Step 2 — Encrypt the dataset
#
# The provider encrypts the dataset with a random AES-256-GCM key. The
# encrypted file can be hosted anywhere (S3, Zenodo, GitHub) — without the
# key, it's unreadable.
#
# ```{note}
# AES-256-GCM provides both **confidentiality** (the data is unreadable) and
# **integrity** (any tampering is detected on decryption). The nonce is
# randomly generated per encryption.
# ```

# %%
from fair_data_access.encrypt import encrypt_file, generate_key

KEYS_DIR = Path("keys")

# Generate a random 256-bit symmetric key
dataset_key = generate_key()

# Encrypt the CSV — produces a .enc file alongside the original
encrypted_path, _ = encrypt_file(str(DATASET_PATH), key=dataset_key)
encrypted_path = Path(encrypted_path)

print(f"Original:  {DATASET_PATH} ({DATASET_PATH.stat().st_size:,} bytes)")
print(f"Encrypted: {encrypted_path} ({encrypted_path.stat().st_size:,} bytes)")
print()
print("The encrypted file is safe to host publicly.")
print("Without the dataset key, it is computationally infeasible to decrypt.")

# %% [markdown]
# ## Step 3 — Create the ODRL access policy
#
# The policy declares, in machine-readable form, **who** can do **what** with
# this dataset, under **which conditions**. It uses the
# [ODRL](https://www.w3.org/TR/odrl-model/) (Open Digital Rights Language)
# standard with purpose constraints from the
# [W3C Data Privacy Vocabulary](https://w3id.org/dpv).
#
# This policy says:
# - ✅ **Permitted:** Use and Reproduce — for Public Benefit purposes
# - ❌ **Prohibited:** Commercialise and Sell
# - 📋 **Duty:** Attribute to FAIR2Adapt
#
# The published nanopublication of this policy is:
# [View on Science Live](https://platform.sciencelive4all.org/np/?uri=https://w3id.org/np/RATzaPLmaUtrmZ6w9WILh8jxF3F-e23xPrFHJQFO3-U6Y)
#
# ```{figure} images/sciencelive-odrl-policy-view.png
# :alt: ODRL Policy rendered in Science Live
# :width: 500px
#
# The same policy rendered in the Science Live platform's ODRL viewer.
# ```

# %%
import json

POLICY_PATH = Path("policies/example-policy.jsonld")
policy = json.loads(POLICY_PATH.read_text())

print("=== ODRL Access Policy ===")
print(json.dumps(policy, indent=2))

# %% [markdown]
# In production, this policy would be **published as a signed
# nanopublication** on the decentralised nanopub network, making it
# immutable, citable, and independently verifiable.
#
# ```{tip}
# You can create and publish ODRL policy nanopublications using the
# **Science Live platform** at
# [platform.sciencelive4all.org/np/create](https://platform.sciencelive4all.org/np/create)
# — select the "ODRL Access Policy" template for a guided, user-friendly
# form.
# ```

# %% [markdown]
# ## Step 4 — Receive an access request
#
# A consumer identifies themselves with a DID and declares their purpose.
# In production, this happens via a GitHub Issue (with automated evaluation).
# Here we simulate it by loading the example consumer's DID document.

# %%
CONSUMER_DID = "did:web:fair2adapt.github.io:fair-data-access:example-consumer"
CONSUMER_DID_DOC_PATH = KEYS_DIR / "did" / "example-consumer.json"

consumer_did_doc = json.loads(CONSUMER_DID_DOC_PATH.read_text())

print(f"Access request received from: {CONSUMER_DID}")
print(f"Declared purpose: Academic Research")
print(f"Consumer's public key curve: {consumer_did_doc['verificationMethod'][0]['publicKeyJwk']['crv']}")

# %% [markdown]
# ## Step 5 — Evaluate the policy
#
# The provider (or an automated workflow) checks whether the consumer's
# declared purpose matches the policy's constraints.

# %%
# In production, this is done by fair_data_access.policy.evaluate_policy().
# Here we check manually for clarity.

declared_purpose = "https://w3id.org/dpv#AcademicResearch"
allowed_purposes = [
    c["rightOperand"]["@id"]
    for p in policy["permission"]
    for c in p.get("constraint", [])
]

if declared_purpose in allowed_purposes:
    print(f"✅ PERMIT — purpose '{declared_purpose.split('#')[1]}' matches policy constraint")
else:
    print(f"❌ DENY — purpose not allowed by policy")

# %% [markdown]
# ## Step 6 — Wrap the dataset key for the consumer
#
# The provider wraps the dataset key using the consumer's public key via
# ECDH key agreement + AES-GCM. Only the holder of the consumer's private
# key can unwrap it.
#
# ```{note}
# The dataset key itself is **never transmitted in plain form**. It is
# encrypted specifically for the consumer's public key using an ephemeral
# ECDH shared secret. Even the provider cannot recover the key from the
# wrapped envelope without the consumer's private key.
# ```

# %%
from fair_data_access.did import get_public_key_pem
from fair_data_access.keys import wrap_key, save_wrapped_key

# Extract the consumer's public key from their DID document
consumer_public_pem = get_public_key_pem(consumer_did_doc)

# Wrap the dataset key for this specific consumer
wrapped_envelope = wrap_key(dataset_key, consumer_public_pem)

# Save the wrapped key (in production, this goes to GitHub Pages or S3)
WRAPPED_KEY_PATH = KEYS_DIR / "wrapped-dataset-key.json"
save_wrapped_key(wrapped_envelope, str(WRAPPED_KEY_PATH))

print(f"Wrapped key saved to: {WRAPPED_KEY_PATH}")
print(f"Wrapped envelope size: {len(wrapped_envelope)} bytes")
print()
print("This file is safe to host publicly — only the consumer's private key")
print("can unwrap it.")

# %% [markdown]
# ## Step 7 — Publish the access grant
#
# The grant is a signed nanopublication recording: who was granted access,
# to which dataset, under which policy, and when. It is the **auditable
# proof** of the access decision.
#
# ```{tip}
# You can create and publish access grants using the **Science Live
# platform** — select the "ODRL Access Grant" template, or use the
# automated GitHub Actions workflow in production.
# ```

# %%
from datetime import datetime, timezone

grant_record = {
    "type": "odrl:Agreement",
    "assignee": CONSUMER_DID,
    "target": policy["permission"][0]["target"],
    "policy_nanopub": "https://w3id.org/np/RATzaPLmaUtrmZ6w9WILh8jxF3F-e23xPrFHJQFO3-U6Y",  # view: https://platform.sciencelive4all.org/np/?uri=https://w3id.org/np/RATzaPLmaUtrmZ6w9WILh8jxF3F-e23xPrFHJQFO3-U6Y
    "granted_actions": ["use", "reproduce"],
    "timestamp": datetime.now(timezone.utc).isoformat(),
}

print("=== Access Grant Record ===")
print(json.dumps(grant_record, indent=2))
print()
print("In production, this is published as a signed nanopublication.")
print("Anyone can verify that the grant was issued by the policy publisher.")

# %% [markdown]
# ## Summary
#
# The provider has:
#
# | Step | Artefact | Where it lives |
# |------|----------|----------------|
# | Encrypt dataset | `synthetic-biodiversity-observations.csv.enc` | Public (S3, Zenodo, GitHub) |
# | Dataset key | 256-bit AES key | Provider's secret store (never shared directly) |
# | ODRL policy | `example-policy.jsonld` → nanopublication | Public (nanopub network) |
# | Wrapped key | `wrapped-dataset-key.json` | Public (GitHub Pages) |
# | Access grant | nanopublication | Public (nanopub network) |
#
# The dataset key exists in two forms:
# 1. **Plain** — stored privately by the provider
# 2. **Wrapped** — encrypted for a specific consumer, safe to publish
#
# **Next:** [Chapter 2 — Consumer: request access and decrypt](02_consumer.ipynb)
