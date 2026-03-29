---
title: "Tutorial: Data Provider"
description: How to encrypt data, create ODRL policies, and set up automated access control
---

# Tutorial: Data Provider

This tutorial walks through the complete workflow for protecting private research data with ODRL policies and encrypted data packages, using the Hamburg flood risk assessment as an example.

:::{admonition} Who is a data provider?
:class: tip

Anyone who holds private data that should be shared under controlled conditions. In FAIR2Adapt, this includes municipalities providing building data with demographics, or researchers producing building-level risk outputs.
:::

## Prerequisites

- Python 3.9+
- A GitHub account
- A web domain where you can serve a `did.json` file (for `did:web`)

```bash
# Install fair-data-access
pip install git+https://github.com/FAIR2Adapt/fair-data-access.git

# Verify
fair-data-access --help
```

## Step 1: Set up your DID

A [Decentralized Identifier](https://www.w3.org/TR/did-core/) (DID) proves your identity without a central authority. We use `did:web`, which works by serving a JSON file at your domain.

### Generate a keypair

```bash
# Generate an EC P-256 keypair
fair-data-access keygen -d ~/.fair-data-access/
```

```text
→ Private key: ~/.fair-data-access/private_key.pem
→ Public key:  ~/.fair-data-access/public_key.pem
```

### Create a DID document

```bash
fair-data-access did-doc did:web:fair2adapt.eu \
  ~/.fair-data-access/public_key.pem \
  -o did.json
```

Upload `did.json` to your web server so it's accessible at:

```text
https://your-domain.eu/.well-known/did.json
```

:::{tip}
If you use GitHub Pages for your project website, you can place `did.json` in a `.well-known/` directory in your pages repository.
:::

:::{warning}
Keep `private_key.pem` secret. Never commit it to a repository. The private key is used to prove your identity and decrypt wrapped keys.
:::

## Step 2: Encrypt your data

Each data file is encrypted with AES-256-GCM. A unique symmetric key is generated per dataset. The key is stored as a GitHub Secret — never alongside the data.

### Encrypt a single file

```bash
fair-data-access encrypt buildings.gpkg --save-key buildings_key.txt
```

```text
→ Encrypted: buildings.gpkg.enc
→ Key (base64, store securely): k7B2x9...
```

### Encrypt multiple files

```bash
fair-data-access encrypt statistical_units.gpkg --save-key stats_key.txt
fair-data-access encrypt buildings_with_risk.gpkg --save-key risk_key.txt
```

You now have:

```text
buildings.gpkg.enc          ← encrypted (safe to publish anywhere)
buildings_key.txt           ← symmetric key (keep secret!)
statistical_units.gpkg.enc
stats_key.txt
buildings_with_risk.gpkg.enc
risk_key.txt
```

:::{warning}
Store the key files securely and then delete them from disk. You will add them as GitHub Secrets in [Step 7](#step-7-set-up-the-github-key-server).
:::

## Step 3: Create an ODRL policy

The [ODRL](https://www.w3.org/TR/odrl-model/) policy defines who can do what with your data.

### Common patterns

| Pattern | Permissions | Prohibitions |
|---------|-------------|-------------|
| Academic only | use, reproduce (purpose = AcademicResearch) | distribute, commercialize |
| Consortium only | use, reproduce, distribute (assignee = consortium) | commercialize |
| Government planning | use (purpose = GovernmentPlanning) | distribute, commercialize |

### Create a policy

```bash
fair-data-access policy \
  --uid "https://fair2adapt.eu/policy/hamburg-buildings" \
  --target "https://fair2adapt.eu/data/hamburg-buildings" \
  --permit-actions use reproduce \
  --prohibit-actions distribute commercialize \
  --purpose AcademicResearch \
  --require-attribution \
  -o policies/hamburg-buildings.jsonld
```

This generates:

```{code-block} json
:caption: policies/hamburg-buildings.jsonld

{
  "@context": "http://www.w3.org/ns/odrl.jsonld",
  "@type": "Offer",
  "uid": "https://fair2adapt.eu/policy/hamburg-buildings",
  "permission": [{
    "target": "https://fair2adapt.eu/data/hamburg-buildings",
    "action": ["use", "reproduce"],
    "constraint": [{
      "leftOperand": "purpose",
      "operator": "eq",
      "rightOperand": "AcademicResearch"
    }],
    "duty": [{ "action": "attribute" }]
  }],
  "prohibition": [{
    "target": "https://fair2adapt.eu/data/hamburg-buildings",
    "action": ["distribute", "commercialize"]
  }]
}
```

## Step 4: Publish the policy as a nanopublication

Publishing the policy as a [nanopublication](https://nanopub.net/) makes it immutable, cryptographically signed, and independently verifiable. No one (including you) can silently change the access terms after publishing.

```python
from fair_data_access.policy import load_policy
from fair_data_access.nanopub_utils import publish_policy

policy = load_policy('policies/hamburg-buildings.jsonld')
uri = publish_policy(policy, author_orcid='https://orcid.org/YOUR-ORCID')
print(f'Published: {uri}')
```

```text
→ Published: https://w3id.org/np/RA-abc123...
```

Save the returned nanopub URI and update `policies/registry.json`:

```{code-block} json
:caption: policies/registry.json

{
  "hamburg-buildings": {
    "description": "Hamburg building footprints with demographic indicators",
    "policy_file": "hamburg-buildings.jsonld",
    "policy_nanopub": "https://w3id.org/np/RA-abc123..."
  }
}
```

## Step 5: Update your RO-Crate metadata

The RO-Crate metadata (always unencrypted and public) links the encrypted data to its ODRL policy, download locations, and variable descriptions. This is what makes the data **discoverable**.

```python
from fair_data_access.rocrate import add_encrypted_file_to_crate

add_encrypted_file_to_crate(
    crate_metadata_path='ro-crate-metadata.json',
    encrypted_file_id='buildings.gpkg.enc',
    original_name='Hamburg building footprints',
    description='227k buildings with demographic indicators',
    encoding_format='application/geopackage+sqlite3',
    policy_nanopub_uri='https://w3id.org/np/RA-abc123...',
    key_server_url='https://fair2adapt.github.io/fair-data-access',
    distribution_urls=[
        {
            'name': 'Zenodo',
            'contentUrl': 'https://zenodo.org/records/XXXXX/files/buildings.gpkg.enc',
            'identifier': 'https://doi.org/10.5281/zenodo.XXXXX',
        },
        {
            'name': 'S3 Pangeo@EOSC',
            'contentUrl': 's3://fair2adapt/hamburg/buildings.gpkg.enc',
        },
    ],
    variable_measured=[
        {'@id': 'https://w3id.org/np/RA-iadopt-elderly-singles-placeholder'},
        {'@id': 'https://w3id.org/np/RA-iadopt-children-under-10-placeholder'},
    ],
)
```

This adds an entry like this to your `ro-crate-metadata.json`:

```{code-block} json
:caption: ro-crate-metadata.json (excerpt)

{
  "@id": "buildings.gpkg.enc",
  "@type": "File",
  "name": "Hamburg building footprints",
  "encodingFormat": "application/geopackage+sqlite3",
  "contentEncryption": {
    "algorithm": "AES-256-GCM",
    "keyServer": "https://fair2adapt.github.io/fair-data-access"
  },
  "hasPolicy": {
    "@id": "https://w3id.org/np/RA-abc123..."
  },
  "distribution": [
    {
      "@type": "DataDownload",
      "name": "Zenodo",
      "contentUrl": "https://zenodo.org/records/XXXXX/files/buildings.gpkg.enc"
    },
    {
      "@type": "DataDownload",
      "name": "S3 Pangeo@EOSC",
      "contentUrl": "s3://fair2adapt/hamburg/buildings.gpkg.enc"
    }
  ]
}
```

## Step 6: Upload encrypted data

The encrypted files can be stored on any public repository — they are useless without the decryption key.

### Zenodo (for archival + DOI)

Upload via the [Zenodo web interface](https://zenodo.org/deposit/new) or API:

- Upload `buildings.gpkg.enc` and `ro-crate-metadata.json` (unencrypted)
- Set the license to match your ODRL policy
- Note the DOI for your RO-Crate metadata

### S3 Pangeo@EOSC (for cloud-native access)

```bash
# Upload using s3cmd
s3cmd put buildings.gpkg.enc \
  s3://fair2adapt/hamburg/buildings.gpkg.enc \
  --host=s3.pangeo-eosc.eu \
  --host-bucket="%(bucket)s.s3.pangeo-eosc.eu"

# Make publicly readable (it's encrypted, so public access is safe)
s3cmd setacl s3://fair2adapt/hamburg/buildings.gpkg.enc --acl-public
```

## Step 7: Set up the GitHub key server

The dataset encryption keys are stored as GitHub Secrets and used by GitHub Actions to wrap keys for approved requesters.

### A. Fork or use the repository

If you're part of the FAIR2Adapt organisation, use [FAIR2Adapt/fair-data-access](https://github.com/FAIR2Adapt/fair-data-access) directly. Otherwise, fork it.

### B. Add dataset keys as GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add a secret for each dataset:

| Dataset | Secret name | Value |
|---------|-------------|-------|
| `hamburg-buildings` | `KEY_HAMBURG_BUILDINGS` | Contents of `buildings_key.txt` |
| `hamburg-statistical-units` | `KEY_HAMBURG_STATISTICAL_UNITS` | Contents of `stats_key.txt` |
| `hamburg-risk-private` | `KEY_HAMBURG_RISK_PRIVATE` | Contents of `risk_key.txt` |

The secret name follows the pattern `KEY_<DATASET_ID>` with hyphens replaced by underscores.

### C. Enable GitHub Pages

Go to **Settings → Pages** and set the source to **GitHub Actions**.

### D. Update the policy registry

Edit `policies/registry.json` to add your datasets with their nanopub URIs. Commit and push.

:::{admonition} Done!
:class: tip

When a researcher opens an access request issue, the GitHub Actions workflow will automatically evaluate the ODRL policy, wrap the key, and publish the result. Each access grant is also recorded as a nanopublication for an immutable audit trail.
:::
