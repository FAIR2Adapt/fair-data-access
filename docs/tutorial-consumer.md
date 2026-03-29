---
title: "Tutorial: Data Consumer"
description: How to set up a DID, request access, and decrypt data for analysis
---

# Tutorial: Data Consumer

This tutorial shows how to request and use private FAIR2Adapt datasets — for instance, to validate flood risk models against building-level data, or to run the urban pluvial flood risk pipeline.

:::{admonition} Who is a data consumer?
:class: tip

Any researcher who wants to use a private FAIR2Adapt dataset that is protected by an ODRL policy and encrypted at rest.
:::

## Prerequisites

- Python 3.9+
- A GitHub account
- A web domain where you can serve a `did.json` file

```bash
pip install git+https://github.com/FAIR2Adapt/fair-data-access.git
```

## Step 1: Set up your DID

You need a [Decentralized Identifier](https://www.w3.org/TR/did-core/) so the key server can verify your identity and encrypt the dataset key specifically for you.

```bash
# Generate keypair
fair-data-access keygen -d ~/.fair-data-access/

# Create DID document
fair-data-access did-doc did:web:myuniversity.edu:researcher \
  ~/.fair-data-access/public_key.pem \
  -o did.json
```

Upload `did.json` so it's accessible at:

```text
https://myuniversity.edu/researcher/did.json
```

:::{tip}
For `did:web`, the DID maps to a URL:
- `did:web:example.com` → `https://example.com/.well-known/did.json`
- `did:web:example.com:path:to` → `https://example.com/path/to/did.json`
:::

## Step 2: Find a dataset

Datasets are discoverable through their RO-Crate metadata, which is always unencrypted and public. You can find them on:

- [RO-Hub](https://www.rohub.org/)
- [Dataverse](https://dataverse.org/)
- [Zenodo](https://zenodo.org/)

The RO-Crate metadata tells you:

- What the dataset contains (`name`, `description`, `variableMeasured`)
- The access policy (`hasPolicy` → nanopub URI)
- Where to download (`distribution` → Zenodo / S3 URLs)
- Where to request a key (`contentEncryption.keyServer`)

## Step 3: Check the ODRL policy

Before requesting access, you can inspect the policy:

```python
from fair_data_access.policy import fetch_policy
import json

# Fetch the ODRL policy from the nanopub network
policy = fetch_policy('https://w3id.org/np/RA-abc123...')
print(json.dumps(policy, indent=2))
```

This tells you:
- **Permitted actions**: e.g., `use`, `reproduce`
- **Constraints**: e.g., `purpose = AcademicResearch`
- **Prohibitions**: e.g., `distribute`, `commercialize`
- **Duties**: e.g., `attribute` (you must cite the data provider)

## Step 4: Request access

Open an [access request issue](https://github.com/FAIR2Adapt/fair-data-access/issues/new?template=access-request.yml) on GitHub and fill in the form:

| Field | Example |
|-------|---------|
| Dataset ID | `hamburg-buildings` |
| Your DID | `did:web:myuniversity.edu:researcher` |
| Purpose | AcademicResearch |
| Affiliation | University of Oslo |
| Justification | Validating flood risk model for coastal cities... |

The GitHub Actions workflow will automatically:

1. Resolve your DID to get your public key
2. Evaluate the dataset's ODRL policy against your request
3. If approved: wrap the dataset key with your public key
4. Record the access grant as a nanopublication (audit trail)
5. Comment on the issue with your wrapped key URL

:::{note}
The evaluation is fully automated. If your request matches the policy constraints (e.g., your stated purpose matches the required purpose), access is granted immediately.
:::

## Step 5: Download and decrypt

After approval, the issue comment will contain your wrapped key URL.

### Download the encrypted data

```bash
# From Zenodo
curl -L -o buildings.gpkg.enc \
  https://zenodo.org/records/XXXXX/files/buildings.gpkg.enc
```

Or from S3 Pangeo@EOSC:

```bash
# Using s3cmd
s3cmd get s3://fair2adapt/hamburg/buildings.gpkg.enc \
  --host=s3.pangeo-eosc.eu
```

### Download your wrapped key

```bash
curl -o wrapped_key.json \
  https://fair2adapt.github.io/fair-data-access/keys/<did-hash>/hamburg-buildings.key
```

The `<did-hash>` is the SHA-256 hash of your DID. The exact URL is provided in the GitHub issue comment.

### Decrypt

```python
from fair_data_access.keys import unwrap_key, load_wrapped_key
from fair_data_access.encrypt import decrypt_file
from pathlib import Path

# Unwrap the dataset key using your DID private key
wrapped = load_wrapped_key('wrapped_key.json')
private_key = Path('~/.fair-data-access/private_key.pem').expanduser().read_bytes()
dataset_key = unwrap_key(wrapped, private_key)

# Decrypt the data file
decrypt_file('buildings.gpkg.enc', key=dataset_key)
print('Decrypted: buildings.gpkg')
```

You now have `buildings.gpkg` ready to use.

## Step 6: Use with the flood risk pipeline

The [urban_pfr](https://github.com/FAIR2Adapt/urban_pfr_toolbox_hamburg) pipeline can handle encrypted inputs automatically in FDO mode:

```bash
# Place encrypted RO-Crate inputs in a directory
# Each input has: ro-crate-metadata.json + *.enc files

urban-pfr fdo --input-dir ./encrypted-inputs/ --output-dir ./outputs/
```

The pipeline will:
1. Read each RO-Crate's `hasPolicy` → check the ODRL nanopub
2. Fetch your wrapped key from the key server
3. Decrypt inputs in memory
4. Run the analysis
5. Produce public (HEALPix-aggregated) and private (building-level) outputs

## Cloud-native access via S3

For large datasets, you can stream encrypted data directly from S3 without downloading the full file:

```python
from fair_data_access.rocrate import load_encrypted_input

# crate_entry is the @graph entry for the encrypted file
data_bytes = load_encrypted_input(
    crate_entry=crate_entry,
    private_key_pem=my_private_key,
    s3_endpoint='https://s3.pangeo-eosc.eu',
)

# Load into GeoPandas
import geopandas as gpd
import io
gdf = gpd.read_file(io.BytesIO(data_bytes))
```

## Troubleshooting

### Access denied

If your request is denied, the GitHub issue comment will explain why. Common reasons:

- **Purpose mismatch**: Your stated purpose doesn't match the policy constraint (e.g., you said "Other" but the policy requires "AcademicResearch")
- **DID not resolvable**: Your `did.json` is not accessible at the expected URL
- **Dataset not found**: The dataset ID doesn't exist in the policy registry

### DID resolution fails

Make sure your `did.json` is served with:
- HTTPS (not HTTP)
- Correct `Content-Type: application/json` header
- No authentication required (must be publicly accessible)

Test it:

```bash
curl https://myuniversity.edu/researcher/did.json
```

### Decryption fails

- Make sure you're using the correct private key (the one matching the DID you used in the request)
- Verify the wrapped key file downloaded correctly (should be valid JSON)
