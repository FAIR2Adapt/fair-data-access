# FAIR2Adapt walkthrough — ODRL access control end-to-end

A reproducible walkthrough of the **FAIR2Adapt access control framework**.
Shows how a real ODRL policy nanopublication protects a dataset, and how
a researcher requests access and decrypts the data using their DID.

> **The framework is production-ready. Only the dataset is synthetic.**
> Everything in this walkthrough uses the actual FAIR2Adapt encryption,
> key-wrapping, DID resolution, and nanopublication signing pipelines —
> the same code paths used for the Hamburg urban pluvial flood risk dataset.
> The biodiversity observations in
> [`data/synthetic-biodiversity-observations.csv`](data/README.md) are
> fabricated so the example is fully reproducible without licensing or
> privacy concerns. To adapt this walkthrough to real data, replace the
> dataset file and update the policy URI — no code changes needed.

## What this walkthrough shows

1. How to establish a **decentralized identity (DID)** for a researcher
2. How a **provider** encrypts a dataset and publishes a machine-readable
   access policy as a signed nanopublication
3. How a **consumer** requests access and decrypts the data using their DID
4. How every step produces a signed, auditable nanopublication

## Published nanopublications

These nanopublications were created as part of this walkthrough and are
live on the nanopub network:

- [ODRL Policy](https://platform.sciencelive4all.org/np/?uri=https://w3id.org/np/RATzaPLmaUtrmZ6w9WILh8jxF3F-e23xPrFHJQFO3-U6Y)
- [Access Grant](https://platform.sciencelive4all.org/np/?uri=https://w3id.org/np/RARNOf26WWMYa0BkLWpMURNRqjwSVGXj-4A9r9iCBpruM)

## Run it

The walkthrough uses [MyST](https://mystmd.org/) for documentation and
[jupytext](https://jupytext.readthedocs.io/) to sync notebooks. Only the
`.py` files are committed — `.ipynb` files are generated on demand.

```bash
pip install -e . jupytext pandas
cd examples/walkthrough

# Convert .py to .ipynb
for nb in 00_setup_did 01_provider 02_consumer; do
  jupytext --to notebook "${nb}.py"
done

# Open in Jupyter
jupyter lab
```

Then open the notebooks in order:

1. **[`00_setup_did.ipynb`](00_setup_did.py)** — Generate your own DID, one
   time (optional for reading the walkthrough but required to go beyond it)
2. **[`01_provider.ipynb`](01_provider.py)** — Encrypt the dataset, publish
   the ODRL policy, wrap the dataset key for a specific consumer DID
3. **[`02_consumer.ipynb`](02_consumer.py)** — Receive the grant, unwrap the
   key, decrypt the data

## Build as a website

```bash
npm install -g mystmd
jupytext --to notebook *.py
myst build --html
```

Or view online at
[fair2adapt.github.io/fair-data-access/walkthrough/](https://fair2adapt.github.io/fair-data-access/walkthrough/)

## File layout

```
examples/walkthrough/
├── myst.yml                            # MyST site config
├── README.md                           # This file
├── intro.md                            # Walkthrough intro page
├── 00_setup_did.py                     # Chapter 0 (jupytext format)
├── 01_provider.py                      # Chapter 1
├── 02_consumer.py                      # Chapter 2
├── data/
│   ├── synthetic-biodiversity-observations.csv
│   └── README.md
├── images/
│   ├── how-it-works-simplified.svg     # Overview diagram
│   ├── sciencelive-odrl-policy-create.png
│   ├── sciencelive-odrl-policy-view.png
│   └── sciencelive-odrl-grant-view.png
├── keys/
│   ├── example-provider-public.pem     # Committed — provider identity
│   ├── example-consumer-public.pem     # Committed — consumer identity
│   ├── did/
│   │   ├── example-provider.json       # DID document
│   │   └── example-consumer.json       # DID document
│   └── README.md                       # Why private keys are NOT here
└── policies/
    └── example-policy.jsonld           # Example generated ODRL policy
```

## Private keys

**Private keys are never in this repository.** The notebooks generate a
throwaway private key on first run and save it locally to the gitignored
`keys/*_private.pem`. Delete it anytime — the walkthrough is idempotent.

In CI, private keys are injected from GitHub Secrets
(`EXAMPLE_CONSUMER_PRIVATE_KEY`, `EXAMPLE_PROVIDER_PRIVATE_KEY`).

If you want to go beyond the walkthrough and use this framework for real
research data, see `00_setup_did.ipynb` for how to publish your own DID
document to GitHub Pages (or any web server you control).

## Using your own data

Replace `data/synthetic-biodiversity-observations.csv` with your dataset,
update `datasetUri` in `policies/example-policy.jsonld` (or regenerate it
in `01_provider.ipynb`), and re-run the notebooks. The workflow is
data-agnostic — it encrypts and gates access to whatever file you give it.
