# fair-data-access

ODRL-based access control for FAIR data with nanopublication policies and encrypted data packages.

## Overview

This tool provides automated access control for research data that is private but not sensitive -- data that can be shared under specific conditions (e.g., academic research only) but should not be openly published.

It combines:
- **ODRL** (Open Digital Rights Language) for machine-readable access policies
- **Nanopublications** for immutable, verifiable policy records and audit trails
- **AES-256-GCM encryption** for data-at-rest protection
- **DIDs** (Decentralized Identifiers) for requester identity
- **GitHub Actions** for automated policy evaluation and key distribution

## Architecture

```
Nanopub Network          GitHub Pages/Actions       Zenodo / S3 Pangeo@EOSC
 ├─ ODRL policies         ├─ Wrapped keys            ├─ Encrypted data files
 ├─ Access grants          ├─ Policy evaluation       └─ RO-Crate metadata
 └─ I-ADOPT variables     └─ Key wrapping                (unencrypted)
```

### Access request flow

1. Researcher finds a dataset via its RO-Crate metadata (on RO-Hub, Dataverse, etc.)
2. Metadata references the ODRL policy (nanopub URI) and the key server (GitHub Pages)
3. Researcher opens a GitHub Issue using the access request template
4. GitHub Actions automatically:
   - Resolves the requester's DID to get their public key
   - Fetches the ODRL policy nanopub
   - Evaluates the policy against the request
   - If approved: wraps the dataset key, publishes it to GitHub Pages, records the grant as a nanopub
5. Researcher downloads the wrapped key, decrypts the data, runs their analysis

## Installation

```bash
pip install -e .
```

## Usage

### Data provider workflow

```bash
# 1. Generate a keypair for your DID
fair-data-access keygen -d ~/.fair-data-access/

# 2. Create a DID document (serve at your domain)
fair-data-access did-doc did:web:fair2adapt.eu public_key.pem

# 3. Create an ODRL policy
fair-data-access policy \
  --uid "https://fair2adapt.eu/policy/hamburg-buildings" \
  --target "https://fair2adapt.eu/data/hamburg-buildings" \
  --permit-actions use reproduce \
  --prohibit-actions distribute commercialize \
  --purpose AcademicResearch \
  --require-attribution \
  -o policies/hamburg-buildings.jsonld

# 4. Encrypt your data
fair-data-access encrypt buildings.gpkg --save-key dataset_key.txt

# 5. Upload encrypted data to Zenodo/S3
# 6. Store dataset_key.txt content as a GitHub Secret (KEY_HAMBURG_BUILDINGS)
# 7. Publish ODRL policy as nanopub (updates registry.json with nanopub URI)
```

### Data consumer workflow

```bash
# 1. Generate your DID keypair
fair-data-access keygen -d ~/.fair-data-access/

# 2. Set up did:web (serve did.json at your domain)
fair-data-access did-doc did:web:myuni.edu:me public_key.pem

# 3. Open an access request issue on GitHub
#    (use the issue template at the data-access repo)

# 4. After approval, download and decrypt
curl -o wrapped_key.json https://fair2adapt.github.io/fair-data-access/keys/<did-hash>/hamburg-buildings.key
fair-data-access decrypt buildings.gpkg.enc -k <unwrapped-key>
```

### Integration with urban_pfr pipeline

In FDO mode, the pipeline can automatically handle encrypted inputs:

```python
from fair_data_access import decrypt_file, evaluate_policy, fetch_policy
from fair_data_access.keys import unwrap_key
from fair_data_access.rocrate import load_encrypted_input
```

## Project structure

```
fair-data-access/
  fair_data_access/
    encrypt.py          # AES-256-GCM encryption/decryption
    keys.py             # ECDH key wrapping/unwrapping
    did.py              # DID resolution and document creation
    policy.py           # ODRL policy creation and evaluation
    nanopub_utils.py    # Nanopub publishing (policies + access grants)
    rocrate.py          # RO-Crate integration for encrypted data
    cli.py              # Command-line interface
  scripts/              # GitHub Actions helper scripts
  policies/             # ODRL policy files and registry
  .github/
    workflows/          # Automated access request processing
    ISSUE_TEMPLATE/     # Access request form
  docs/                 # GitHub Pages (served key files)
```

## Migrating to other platforms

The GitHub Pages/Actions setup is a lightweight starting point. The same components work on:

- **LifeWatch/EOSC**: Replace GitHub Actions with a FastAPI service
- **University server**: Same FastAPI service behind institutional auth
- **Hamburg municipality**: Fork this repo, add their own dataset keys

The ODRL policies (as nanopubs), encrypted data packages, and RO-Crate metadata remain unchanged across platforms.

## Related

- [urban_pfr_toolbox_hamburg](https://github.com/FAIR2Adapt/urban_pfr_toolbox_hamburg) -- Flood risk pipeline that consumes this data
- [ODRL](https://www.w3.org/TR/odrl-model/) -- W3C standard for digital rights
- [Nanopublications](https://nanopub.net/) -- Decentralized, verifiable scientific assertions
- [RO-Crate](https://www.researchobject.org/ro-crate/) -- Research Object packaging
- [FAIR2Adapt](https://fair2adapt.eu/) -- FAIR data for climate adaptation
