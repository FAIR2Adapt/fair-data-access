# Snakefile — reproducible end-to-end demo of the fair-data-access method.
#
# One rule per stage of the synthetic walkthrough; each rule (except key setup)
# wraps a jupytext notebook executed in place, so the notebook stays the source
# of truth and Snakemake just sequences the DAG:
#
#   setup_keys  → generate a matched consumer identity if none exists (zero secrets)
#   provider    → encrypt the dataset, author the ODRL policy, wrap the key   (01_provider.py)
#   consumer    → unwrap the key, decrypt, verify integrity                   (02_consumer.py)
#
# Usage:
#   pixi run run             # everything (= snakemake --cores 1)
#   pixi run run -- -n       # dry run (DAG only)
#
# Executed .ipynb files are gitignored artefacts (only the .py are committed).

WT = "examples/walkthrough"
RESULTS = "results"


rule all:
    input:
        f"{WT}/02_consumer.ipynb",
        f"{RESULTS}/walkthrough-verified.txt",


# ---------- 0: Consumer identity (self-contained, zero secrets) ----------
# The private half of the example identity is never committed. On a fresh clone
# this rule mints a matched (private, public, DID document) triple so the demo
# runs with no GitHub Secret. See scripts/generate_example_keys.py.
rule setup_keys:
    output:
        f"{WT}/keys/example-consumer-private.pem",
    shell:
        "python scripts/generate_example_keys.py"


# ---------- 1: Provider ----------
# Encrypts the synthetic dataset, loads the ODRL policy, wraps the dataset key
# for the consumer DID. Produces the .enc file and the wrapped-key envelope.
rule provider:
    input:
        key=f"{WT}/keys/example-consumer-private.pem",
        data=f"{WT}/data/synthetic-biodiversity-observations.csv",
        policy=f"{WT}/policies/example-policy.jsonld",
        did=f"{WT}/keys/did/example-consumer.json",
    output:
        enc=f"{WT}/data/synthetic-biodiversity-observations.csv.enc",
        wrapped=f"{WT}/keys/wrapped-dataset-key.json",
        nb=f"{WT}/01_provider.ipynb",
    shell:
        f"( cd {WT} && jupytext --to notebook --execute 01_provider.py )"


# ---------- 2: Consumer ----------
# Unwraps the dataset key with the consumer private key, decrypts, and asserts
# byte-for-byte integrity against the original. Writes a verification marker.
rule consumer:
    input:
        enc=f"{WT}/data/synthetic-biodiversity-observations.csv.enc",
        wrapped=f"{WT}/keys/wrapped-dataset-key.json",
        key=f"{WT}/keys/example-consumer-private.pem",
    output:
        nb=f"{WT}/02_consumer.ipynb",
        marker=f"{RESULTS}/walkthrough-verified.txt",
    shell:
        f"( cd {WT} && jupytext --to notebook --execute 02_consumer.py ) "
        f'&& echo "walkthrough integrity check passed" > {RESULTS}/walkthrough-verified.txt'
