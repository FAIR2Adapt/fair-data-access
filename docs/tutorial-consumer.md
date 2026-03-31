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

- Python 3.12+
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

## Step 2: Find a dataset and check its policy

Datasets are discoverable through their RO-Crate metadata, which is always unencrypted and public.

You can inspect the ODRL policy before requesting access:

```python
from fair_data_access.policy import fetch_policy
import json

policy = fetch_policy('https://w3id.org/np/RAir7keZs8Jy7i8...')
print(json.dumps(policy, indent=2))
```

This tells you:
- **Permitted actions**: e.g., `use`, `reproduce`
- **Constraints**: e.g., `purpose = AcademicResearch`
- **Prohibitions**: e.g., `distribute`, `commercialize`
- **Duties**: e.g., `attribute` (you must cite the data provider)

## Step 3: Request access

Open an [access request issue](https://github.com/FAIR2Adapt/fair-data-access/issues/new?template=access-request.yml) on GitHub:

| Field | Example |
|-------|---------|
| Dataset ID | `hamburg-buildings` |
| Your DID | `did:web:myuniversity.edu:researcher` |
| Purpose | Academic Research |
| Affiliation | University of Oslo |
| Justification | Validating flood risk model for coastal cities... |

## Step 4: Wait for the data provider to review

Unlike automated systems, the data provider **manually reviews** each request and decides whether to approve it. If approved, they publish an **ODRL Access Grant for FAIR Data** nanopub — a cryptographically signed, immutable record that you have been authorized.

The GitHub Actions workflow then automatically:

1. Verifies the grant nanopub (checks signature and that the grant was published by the policy owner)
2. Wraps the dataset key with your public key (from your DID)
3. Deploys the wrapped key to GitHub Pages
4. Comments on your issue with the download URL

:::{note}
You will receive a GitHub notification when the issue is updated. If denied, the comment will explain why and suggest next steps.
:::

## Step 5: Download and decrypt

After approval, the issue comment will contain your wrapped key URL.

### Download the wrapped key

```bash
curl -o wrapped_key.json \
  "https://fair2adapt.github.io/fair-data-access/keys/<did-hash>/hamburg-buildings.key"
```

The exact URL is provided in the GitHub issue comment.

### Download the encrypted data

From S3 Pangeo@EOSC:

```python
import s3fs

fs = s3fs.S3FileSystem(
    anon=True,
    client_kwargs={'endpoint_url': 'https://pangeo-eosc-minioapi.vm.fedcloud.eu/'}
)
fs.get('afouilloux-fair2adapt/buildings.fgb.enc', 'buildings.fgb.enc')
```

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
decrypt_file('buildings.fgb.enc', key=dataset_key)
print('Decrypted: buildings.fgb')
```

### Or decrypt in memory (no temp files)

```python
from fair_data_access.encrypt import decrypt_bytes

# Read encrypted data (from local file or S3)
encrypted_data = fs.cat('afouilloux-fair2adapt/buildings.fgb.enc')

# Decrypt in memory
decrypted_data = decrypt_bytes(encrypted_data, dataset_key)

# Load directly into GeoPandas
import geopandas as gpd
import io
gdf = gpd.read_file(io.BytesIO(decrypted_data))
```

## Step 6: Verify your access grant

You can independently verify that your access grant is legitimate:

```python
from fair_data_access.grant import verify_access

result = verify_access(
    dataset_uri='https://fair2adapt.eu/data/hamburg-buildings',
    requester_did='did:web:myuniversity.edu:researcher',
    policy_nanopub_uri='https://w3id.org/np/RAir7keZs8Jy7i8...',
)

print(f"Access granted: {result['granted']}")
print(f"Grant nanopub: {result['grant_nanopub']}")
print(f"Signature valid, creator authorized: {result['granted']}")
```

This checks:
1. A valid grant nanopub exists on the nanopub network
2. The grant's cryptographic signature is valid
3. The grant was published by the same identity that published the policy

## Troubleshooting

### Access denied

The GitHub issue comment will explain why. Common reasons:

- **No grant found**: The data provider has not yet published an ODRL Access Grant for your request. Contact them directly.
- **DID not resolvable**: Your `did.json` is not accessible at the expected URL.
- **Dataset not found**: The dataset ID doesn't exist in the policy registry.

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
- Verify the wrapped key file downloaded correctly (should be valid JSON with an `algorithm` field)
