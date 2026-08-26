# Making `fair-data-access` a fully FORRT-compliant, reproducible repo

**Status:** planning + Phase 2 (engine port) in progress
**Owner:** Anne Fouilloux (ORCID 0000-0002-1784-2920), FAIR2Adapt
**Target:** Open Research Europe (ORE) **Method Article** + reproducible companion

---

## 0. Framing decision (agreed)

Two papers, not one:

- **Paper A (this repo, now):** the `fair-data-access` **method** — ODRL policies +
  nanopublication grants + DIDs + authenticated encryption — plus its reproducible
  *synthetic* demo. The access-control method is fully validated by the synthetic
  walkthrough (toy data stands in for private data by design). → ORE Method Article.
- **Paper B (later, separate):** the **end-to-end** unification with the
  `urban_pfr_toolbox_hamburg` flood-risk pipeline (its `feature/v3-paper-scientific-validation`
  branch already validates the pipeline on a synthetic small dataset). That is a bigger
  *applied / case-study* paper and the natural home for a genuine FORRT **replication**
  chain of the flood pipeline.

### This repo is a *self-originating* FORRT-compliant object

`fair-data-access` is **not** replicating a prior published claim, so the classic
paper-rooted FORRT chain (`Quote → AIDA → Claim → Study → Outcome → Citation`) does not
apply verbatim. Instead we make the repo **fully FORRT-compliant at creation**: it adopts
the entire FORRT template engine and conventions, but anchors its nanopublication
constellation on a **research question** (PCC/PICO), not a quote. The repo *originates*
a method claim and the software + artefacts that substantiate it.

This is a legitimate, self-contained FORRT profile:
> a reproducible research object whose constellation is question-rooted and whose apex
> artefact is **Research Software** rather than a Replication Outcome.

---

## 1. What already exists (do not rebuild)

| Piece | Location | State |
|---|---|---|
| Working Python method | `fair_data_access/` (encrypt, keys, did, policy, grant, nanopub_utils, rocrate, cli) | ✅ production code |
| Reproducible synthetic demo | `examples/walkthrough/` (`00_setup_did` → `01_provider` → `02_consumer`, jupytext `.py`) | ✅ runs; MyST book |
| CI | `.github/workflows/` (`walkthrough.yml` runs the demo, `deploy-pages.yml`, `access-request.yml`) | ✅ working |
| Two MyST books | `docs/`, `examples/walkthrough/` | ✅ |
| Per-dataset RO-Crate | `fair_data_access/rocrate.py`, policy registry | ✅ |
| **4 live nanopubs** | Hamburg policy `RAir7ke…` + grant `RAABfWG…`; demo policy `RATzaPL…` + grant `RARNOf2…` | ✅ resolvable |
| ORE draft | `paper/FAIR2Adapt_ODRL_Nanopub_MethodArticle_draft.docx` | ✅ near-submittable |

## 2. Gap to full FORRT compliance

| FORRT engine component | Have? | Action | Phase |
|---|---|---|---|
| `pixi.toml` + `pixi.lock` (pinned env) | ❌ (pip only) | **added** `pixi.toml`; run `pixi install` to mint lock | 2 |
| `Snakefile` (one rule / stage) | ❌ (bash loop) | **added** (`setup_keys → provider → consumer`) | 2 |
| `CITATION.cff` / `codemeta.json` / repo-level `ro-crate-metadata.json` | ❌ | **added** | 2 |
| Archived DOI (Zenodo / Software Heritage) | ❌ | tag release + mint DOI; add to CITATION.cff | 4 |
| FORRT `nanopubs/` workspace (`drafts/` + `PUBLISHED.md` + `templates/`) | partial (creation notebooks only) | restructure to FORRT layout; author **question-rooted** chain | 3 |
| `verify-chain` check | ❌ | adapt template's verify-chain to the methods constellation | 3 |
| `docs/fair4rs-checklist.md` gate | ❌ | port checklist; tick before declaring done | 3 |
| Manuscript form | docx (kept) | MyST book stays the reproducible **companion**; docx is the ORE submission | 1 |

## 3. Methods-shaped nanopublication constellation (question-rooted)

```
[PCC / PICO Research Question]   "Under what conditions may controlled-access FDOs for
   │                              climate adaptation be expressed & enforced machine-actionably?"
   ▼
[AIDA Sentence] → [FORRT-style Method Claim]
   │        "ODRL policy + nanopub grant + DID + AEAD enforces access without a central authority."
   ├──▶ [Research Software nanopub] → fair-data-access (Apache-2.0, Zenodo DOI)   ← apex artefact
   ├──▶ [ODRL Policy nanopub]   RATzaPL…   (already live — becomes a node)
   ├──▶ [Access Grant nanopub]  RARNOf2…   (already live — becomes a node)
   └──▶ [CiTO Citations] → Kuhn 2021, Schultes 2022, ODRL, DID-core, RO-Crate
```

The four existing nanopubs stop being loose URLs in prose and become **cited members of one
navigable constellation** — the paper's own "knowledge graph, not a PDF" argument, made
reflexively.

## 4. Phased plan

1. **Paper text pass** — tighten prose; fix Figures 2/3 (re-render Science Live screenshots as
   RDF/table figures we own); fill archival/reproducibility sections; sharpen contribution vs prior FDO work.
2. **Engine port (this phase)** — `pixi.toml`, `Snakefile`, `scripts/generate_example_keys.py`,
   `CITATION.cff`, `codemeta.json`, repo-level `ro-crate-metadata.json`; then extend CI to a
   `pixi run run` reproducibility gate.
3. **FORRT constellation + compliance** — restructure `nanopubs/` to FORRT layout; author the
   question-rooted chain drafts; publish via Science Live; adapt `verify-chain`; port the
   fair4rs checklist.
4. **Archive + submit** — Zenodo DOIs (code + synthetic CSV), wire everything, assemble ORE package.

## 5. Open decisions

- **Example consumer identity:** the demo needs a consumer keypair whose private half is not
  committed (`.gitignore` excludes `*-private.pem`; CI injects it from a secret). For a
  zero-secret local `pixi run run`, `scripts/generate_example_keys.py` **regenerates the matched
  triple (private + public + DID doc) when the private key is absent** — this dirties the two
  committed example files locally. Alternative: commit a clearly-labelled *demo* private key so
  runs are deterministic and git-clean. **Decision needed.**
- **Author line / CRediT:** confirm with consortium (draft has placeholders).
- **Synthetic CSV DOI:** deposit separately on Zenodo, or reference via GitHub path only?

## 6. Local commands (after `pixi install` mints the lock)

```bash
pixi install            # solve env + generate pixi.lock (commit both)
pixi run run            # snakemake --cores 1  → runs setup_keys → provider → consumer
pixi run run -- -n      # dry run (DAG only)
pixi run book           # build the MyST companion book
pixi run -e tests test  # pytest
```
