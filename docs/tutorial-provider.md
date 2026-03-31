---
title: "Tutorial: Data Provider"
description: How to encrypt data, create ODRL policies, publish access grants, and set up the key server
---

# Tutorial: Data Provider

This tutorial walks through the complete workflow for protecting private research data with ODRL policies and encrypted data packages, using the Hamburg flood risk assessment as an example.

:::{admonition} Who is a data provider?
:class: tip

Anyone who holds private data that should be shared under controlled conditions. In FAIR2Adapt, this includes municipalities providing building data with demographics, or researchers producing building-level risk outputs.
:::

## Prerequisites

- Python 3.12+
- A GitHub account
- A web domain where you can serve a `did.json` file (for `did:web`), or use GitHub Pages

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
fair-data-access keygen -d ~/.fair-data-access/
```

```text
→ Private key: ~/.fair-data-access/private_key.pem
→ Public key:  ~/.fair-data-access/public_key.pem
```

### Create a DID document

```bash
fair-data-access did-doc did:web:fair2adapt.github.io:fair-data-access \
  ~/.fair-data-access/public_key.pem \
  -o did.json
```

Upload `did.json` to your web server or GitHub Pages so it's accessible at:

```text
https://fair2adapt.github.io/fair-data-access/did.json
```

:::{warning}
Keep `private_key.pem` secret. Never commit it to a repository.
:::

## Step 2: Encrypt your data

Each data file is encrypted with AES-256-GCM. A unique symmetric key is generated per dataset.

```bash
fair-data-access encrypt buildings.fgb --save-key buildings_key.txt
```

```text
→ Encrypted: buildings.fgb.enc
→ Key saved to: buildings_key.txt
```

:::{warning}
Save the key securely. You will add it as a GitHub Secret in [Step 6](#step-6-set-up-the-github-key-server). Then delete the key file from disk.
:::

## Step 3: Upload encrypted data

The encrypted files can be stored on any public repository — they are useless without the decryption key.

```bash
# Upload to S3 Pangeo@EOSC
s3cmd put buildings.fgb.enc \
  s3://afouilloux-fair2adapt/buildings.fgb.enc \
  --host=pangeo-eosc-minioapi.vm.fedcloud.eu \
  --host-bucket="%(bucket)s.pangeo-eosc-minioapi.vm.fedcloud.eu"
```

## Step 4: Publish an ODRL Access Policy

The access policy defines who can do what with your data. Policies are published as [nanopublications](https://nanopub.net/) — immutable, cryptographically signed, and independently verifiable.

### Create the policy via Nanodash

Use the **ODRL Access Policy for FAIR Data** template on Nanodash:

**[Create ODRL Access Policy](https://nanodash.knowledgepixels.com/publish?template=https://w3id.org/np/RA61D4c7dB5t0B1mLhc78bN2vagqYTXQiJDKY0yImRULI)**

Fill in:

| Field | Example |
|-------|---------|
| Policy URI | `hamburg-buildings` |
| Type | Offer |
| Dataset URI | `hamburg-buildings` |
| Permitted action | Use |
| Purpose constraint | Academic Research |
| Prohibited action | Distribute |
| Duty action | Attribute |
| Attribution party | `https://fair2adapt-eosc.eu` |

Click the **+** button on the permission group to add multiple permitted actions (e.g., Use and Reproduce), and on the prohibition group for multiple prohibited actions (e.g., Distribute and Commercialize).

:::{tip}
The policy nanopub is signed with your ORCID. Only you can publish grants against it — the system verifies that the grant publisher matches the policy publisher.
:::

### Update the policy registry

After publishing, update `policies/registry.json` with the nanopub URI:

```{code-block} json
:caption: policies/registry.json

{
  "hamburg-buildings": {
    "description": "Hamburg building footprints with demographic indicators",
    "policy_nanopub": "https://w3id.org/np/RAir7keZs8Jy7i8...",
    "encrypted_files": ["buildings.fgb.enc"],
    "distributions": [
      {
        "name": "S3 Pangeo@EOSC",
        "contentUrl": "s3://afouilloux-fair2adapt/buildings.fgb.enc",
        "endpointUrl": "https://pangeo-eosc-minioapi.vm.fedcloud.eu/"
      }
    ]
  }
}
```

## Step 5: Review requests and publish grants

When a researcher requests access (via a GitHub Issue), you review their request and decide whether to approve it.

### Review the request

The researcher's GitHub Issue contains:
- Their DID (identity)
- Stated purpose and affiliation
- Justification for access

### Publish an access grant via Nanodash

If you approve, publish a grant using the **ODRL Access Grant for FAIR Data** template:

**[Create ODRL Access Grant](https://nanodash.knowledgepixels.com/publish?template=https://w3id.org/np/RAeRMv6jOibLPIYBMOGu_FsX6NQ6B59KJCgCFkue4z7Ac)**

Fill in:

| Field | Example |
|-------|---------|
| Grant identifier | `hamburg-buildings-grant-001` |
| Action | Use |
| Assignee | Requester's DID URL (e.g., `https://myuniversity.edu/researcher/did.json`) |
| Under policy | The policy nanopub URI |
| Dataset URI | `hamburg-buildings` |
| Timestamp | Current date and time |

:::{note}
Nanodash requires HTTP(S) URIs for the assignee field. Convert `did:web:myuniversity.edu:researcher` to `https://myuniversity.edu/researcher/did.json`. The system handles both formats.
:::

### Trigger the key release

After publishing the grant, add the `access-request` label to the researcher's GitHub Issue. The workflow will:

1. **Verify** the grant nanopub (signature + creator match against policy)
2. **Wrap** the dataset key with the requester's public key
3. **Deploy** the wrapped key to GitHub Pages
4. **Comment** on the issue with the download URL

:::{important}
Only grants signed by the same identity that published the policy are accepted. If someone else tries to publish a grant for your data, it will be rejected.
:::

## Step 6: Set up the GitHub key server

### Add dataset keys as GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add a secret for each dataset:

| Dataset | Secret name | Value |
|---------|-------------|-------|
| `hamburg-buildings` | `KEY_HAMBURG_BUILDINGS` | Hex-encoded key from Step 2 |

The secret name follows the pattern `KEY_<DATASET_ID>` with hyphens replaced by underscores.

### Enable GitHub Pages

Go to **Settings → Pages** and set the source to **GitHub Actions**.

### Commit and push

Push `policies/registry.json` and the workflow files. The system is now ready to process access requests.

## Revoking access

To revoke a researcher's access, retract their grant nanopub:

1. Find the grant nanopub URI (from the issue comment or nanopub network)
2. Use `nanopubs/disapprove_nanopub.ipynb` to retract it
3. Future key wrapping requests for that researcher will be denied

:::{note}
Revocation prevents new key distribution but does not invalidate already-downloaded wrapped keys. For full revocation, re-encrypt the data with a new key and update the GitHub Secret.
:::
