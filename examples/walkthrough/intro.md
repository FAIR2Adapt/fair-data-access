# FAIR data access control — a reproducible walkthrough

This walkthrough demonstrates how the **FAIR2Adapt access control framework**
protects research data using machine-readable ODRL policies published as
signed nanopublications.

## The framework is production-ready

Everything here uses the same code, the same encryption, and the same
nanopublication infrastructure that protects the Hamburg urban pluvial flood
risk dataset in FAIR2Adapt. Only the dataset is synthetic — so the walkthrough
is fully reproducible without licensing or privacy concerns.

## What you will learn

```{admonition} Chapter 0 — Set up your identity
:class: tip
Generate a decentralised identifier (DID) — a cryptographic identity that
stays with you across institutions. You do this once and reuse it for every
dataset request you ever make.
```

```{admonition} Chapter 1 — Provider: encrypt and publish a policy
:class: note
Encrypt a dataset with AES-256-GCM, publish an ODRL access policy as a signed
nanopublication, and wrap the dataset key for a specific consumer's DID.
```

```{admonition} Chapter 2 — Consumer: request access and decrypt
:class: note
Receive a cryptographically wrapped key, unwrap it with your private key,
and decrypt the dataset. Verify the access grant nanopublication for audit.
```

## How ODRL access control works

![How it works: Data Provider encrypts and publishes, the framework evaluates the ODRL policy and wraps the key, Data Consumer decrypts and runs analysis](images/how-it-works.svg)

Every step that produces a nanopublication creates a **signed, immutable,
auditable record** on the decentralised nanopub network. The provider can
prove they published the policy. The consumer can prove they were granted
access. Anyone can verify the chain.

## Adapting this to your own data

This walkthrough uses a synthetic biodiversity dataset, but the framework is
data-agnostic. To protect your own research data:

1. Replace the CSV with your file
2. Change the `datasetUri` in the ODRL policy
3. Re-run the notebooks

No code changes needed. The encryption, key wrapping, DID resolution, and
nanopublication signing all work identically regardless of what data you
protect.

## Prerequisites

```bash
pip install fair-data-access jupytext jupyter-book
```

You also need Python ≥ 3.12 and a working internet connection (for DID
resolution and nanopub network queries, if you publish for real).
