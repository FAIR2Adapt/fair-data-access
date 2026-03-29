---
title: Architecture
description: Technical architecture of the FAIR2Adapt data access system
---

# Architecture

## Overview

The system uses four independent components that together provide automated, policy-driven access control without requiring a central authority or blockchain.

```{mermaid}
flowchart TB
    subgraph "Trust Layer (Nanopub Network)"
        NP1["ODRL Policy\n(immutable, signed)"]
        NP2["Access Grant\n(audit trail)"]
        NP3["I-ADOPT Variables\n(semantics)"]
    end

    subgraph "Key Server (GitHub)"
        GHA["GitHub Actions\n(policy evaluation)"]
        GHP["GitHub Pages\n(wrapped keys)"]
        GHS["GitHub Secrets\n(dataset keys)"]
    end

    subgraph "Data Storage"
        ZEN["Zenodo\n(archival, DOI)"]
        S3["S3 Pangeo@EOSC\n(cloud access)"]
    end

    subgraph "Metadata"
        RC["RO-Crate\n(discoverability)"]
    end

    RC -->|hasPolicy| NP1
    RC -->|variableMeasured| NP3
    RC -->|distribution| ZEN
    RC -->|distribution| S3
    GHA -->|evaluates| NP1
    GHA -->|reads| GHS
    GHA -->|publishes| NP2
    GHA -->|writes| GHP
```

## Standards used

| Standard | Role | Specification |
|----------|------|---------------|
| **ODRL** | Access policies (permissions, prohibitions, duties) | [W3C Recommendation](https://www.w3.org/TR/odrl-model/) |
| **Nanopublications** | Immutable, signed policy and audit records | [nanopub.net](https://nanopub.net/) |
| **DID** | Decentralized identity (did:web) | [W3C Recommendation](https://www.w3.org/TR/did-core/) |
| **RO-Crate** | Research object packaging and metadata | [RO-Crate 1.1](https://w3id.org/ro/crate/1.1) |
| **I-ADOPT** | Variable semantics for automatic column mapping | [I-ADOPT](https://i-adopt.github.io/) |
| **AES-256-GCM** | Authenticated encryption | [NIST SP 800-38D](https://csrc.nist.gov/publications/detail/sp/800-38d/final) |
| **ECDH + HKDF** | Key agreement for wrapping | [RFC 6090](https://www.rfc-editor.org/rfc/rfc6090) |

## Encryption scheme

### Data encryption

Each dataset is encrypted with a unique AES-256-GCM symmetric key:

```text
Plaintext file                  Encrypted file
buildings.gpkg     ──AES-256-GCM──►  [12B nonce][ciphertext + 16B GCM tag]
                     │
                     key (32 bytes, stored as GitHub Secret)
```

- **AES-256-GCM** provides both confidentiality and integrity
- The 12-byte nonce is randomly generated and prepended to the ciphertext
- The 16-byte GCM authentication tag detects any tampering

### Key wrapping

The dataset key is wrapped (encrypted) for each authorized recipient using an ECIES-like scheme:

```text
1. Generate ephemeral EC P-256 keypair
2. ECDH shared secret = ephemeral_private × recipient_public
3. Wrapping key = HKDF-SHA256(shared_secret)
4. Wrapped key = AES-256-GCM(wrapping_key, dataset_key)
5. Output: { ephemeral_public_key, nonce, wrapped_key }
```

Only the holder of the recipient's private key can reverse step 2 to derive the wrapping key and unwrap the dataset key.

## Access request flow

```{mermaid}
sequenceDiagram
    participant R as Researcher
    participant GH as GitHub Issues
    participant GA as GitHub Actions
    participant DID as DID Resolver
    participant NP as Nanopub Network
    participant GP as GitHub Pages

    R->>GH: Open access request issue
    GH->>GA: Trigger workflow
    GA->>DID: Resolve requester DID
    DID-->>GA: Public key + credentials
    GA->>NP: Fetch ODRL policy nanopub
    NP-->>GA: Policy (JSON-LD)
    GA->>GA: Evaluate policy
    alt Policy permits
        GA->>GA: Wrap dataset key with requester's public key
        GA->>GP: Publish wrapped key
        GA->>NP: Publish access grant nanopub
        GA->>GH: Comment: approved + key URL
    else Policy denies
        GA->>GH: Comment: denied + reason
    end
    R->>GP: Download wrapped key
    R->>R: Unwrap key + decrypt data
```

## Why not blockchain?

The nanopublication network provides the same guarantees often attributed to blockchain:

| Property | Blockchain | Nanopublications |
|----------|-----------|-----------------|
| Immutability | Hash-chain consensus | Content-addressed URI + cryptographic signature |
| Decentralization | Distributed ledger | Peer-to-peer nanopub servers |
| Verifiability | Public ledger | Signed RDF, independently verifiable |
| Audit trail | Transaction log | Access grant nanopubs |
| Cost | Gas fees | Free |
| Science-ready | No | Yes (designed for scholarly communication) |

## Migration paths

The architecture is modular — each component can be replaced independently:

| Component | Current | Alternative |
|-----------|---------|-------------|
| Key server | GitHub Pages + Actions | FastAPI on LifeWatch / university server |
| Data storage | Zenodo + S3 | Any HTTP/S3-compatible storage |
| Identity | did:web | did:key, did:ethr, institutional SSO |
| Policy store | Nanopub network | Local JSON-LD files |
| Pipeline | urban_pfr | Any tool that reads GeoPackage/FlatGeobuf |
