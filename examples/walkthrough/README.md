# FAIR2Adapt walkthrough — ODRL access control end-to-end

A reproducible walkthrough of the **FAIR2Adapt access control framework**.
Shows how a real ODRL policy nanopublication protects a dataset, and how
a researcher requests access and decrypts the data using their DID.

> **The framework is production-ready. Only the dataset is synthetic.**
> Everything in this walkthrough uses the actual FAIR2Adapt encryption,
> key-wrapping, DID resolution, and nanopublication signing pipelines —
> the same code paths used for the Hamburg pluvial flood risk dataset.
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

## Run it

The walkthrough is a Jupyter-book with three notebooks, paired to Python
scripts via [jupytext](https://jupytext.readthedocs.io/) so only the `.py`
files are committed. Regenerate the `.ipynb` files on first run:

```bash
pip install -e .[dev] jupytext jupyter-book
cd examples/walkthrough
jupytext --sync *.py
jupyter lab
```

Then open the notebooks in order:

1. **[`00_setup_did.ipynb`](00_setup_did.py)** — Generate your own DID, one
   time (optional for reading the walkthrough but required to go beyond it)
2. **[`01_provider.ipynb`](01_provider.py)** — Encrypt the dataset, publish
   the ODRL policy, wrap the dataset key for a specific consumer DID
3. **[`02_consumer.ipynb`](02_consumer.py)** — Receive the grant, unwrap the
   key, decrypt the data

Or run them all at once:

```bash
jupyter nbconvert --execute --to notebook *.ipynb
```

## Build as a book

```bash
jupyter-book build .
```

The rendered HTML lands in `_build/html`.

## File layout

```
examples/walkthrough/
├── _config.yml                         # Jupyter-book config
├── _toc.yml                            # Table of contents
├── README.md                           # This file
├── intro.md                            # Book intro page
├── 00_setup_did.py                     # (jupytext pair)
├── 01_provider.py                      # (jupytext pair)
├── 02_consumer.py                      # (jupytext pair)
├── data/
│   ├── synthetic-biodiversity-observations.csv
│   └── README.md
├── keys/
│   ├── example-provider-public.pem     # Committed — provider identity
│   ├── example-consumer-public.pem     # Committed — consumer identity
│   ├── did/
│   │   ├── example-provider.json       # Committed — DID document
│   │   └── example-consumer.json       # Committed — DID document
│   └── README.md                       # Why private keys are NOT here
└── policies/
    └── example-policy.jsonld           # Example generated ODRL policy
```

## Private keys

**Private keys are never in this repository.** The notebooks generate a
throwaway private key on first run and save it locally to the gitignored
`keys/*_private.pem`. Delete it anytime — the walkthrough is idempotent.

If you want to go beyond the walkthrough and use this framework for real
research data, see `00_setup_did.ipynb` for how to publish your own DID
document to GitHub Pages (or any web server you control).

## Using your own data

Replace `data/synthetic-biodiversity-observations.csv` with your dataset,
update `datasetUri` in `policies/example-policy.jsonld` (or regenerate it
in `01_provider.ipynb`), and re-run the notebooks. The workflow is
data-agnostic — it encrypts and gates access to whatever file you give it.
