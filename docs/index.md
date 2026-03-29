---
title: FAIR2Adapt Data Access
description: ODRL-based access control for FAIR climate adaptation data
---

# FAIR2Adapt Data Access

This service manages access to private FAIR2Adapt datasets using **ODRL** policies published as **nanopublications**, with data encrypted via **AES-256-GCM** and identity verified through **DIDs** (Decentralized Identifiers).

:::{note}
This tool is designed for data that is **private but not sensitive** — data that can be shared under specific conditions (e.g., academic research only) but should not be openly published.
:::

## How it works

```{mermaid}
%%{init: {'theme': 'base', 'themeVariables': {'fontSize': '16px', 'fontFamily': 'Quicksand'}, 'flowchart': {'nodeSpacing': 30, 'rankSpacing': 40, 'padding': 15}}}%%

flowchart LR
    subgraph P["<b>1. Data Provider</b>"]
        direction TB
        A["Encrypt data\n(AES-256-GCM)"] --> B["Publish ODRL policy\n(nanopublication)"] --> C["Upload to\nZenodo / S3 Pangeo"]
    end

    subgraph G["<b>2. GitHub Actions</b>"]
        direction TB
        D["Researcher requests\naccess (GitHub Issue)"] --> E["Resolve DID +\nevaluate ODRL policy"] --> F["Wrap key +\npublish access grant"]
    end

    subgraph R["<b>3. Data Consumer</b>"]
        direction TB
        H["Download wrapped key\n(GitHub Pages)"] --> I["Decrypt with\nDID private key"] --> J["Run analysis"]
    end

    C --> D
    F --> H
```

## Quick start

::::{grid} 1 1 2 2

:::{card} I have data to share
:link: tutorial-provider.md

**Data Provider Tutorial** — Encrypt your data, create ODRL policies, and set up automated access control.
:::

:::{card} I want to access data
:link: tutorial-consumer.md

**Data Consumer Tutorial** — Set up a DID, request access, and decrypt data for your analysis.
:::
::::

## Available datasets

| Dataset | Description | Policy |
|---------|-------------|--------|
| `hamburg-buildings` | Building footprints with demographic indicators | Academic research only |
| `hamburg-statistical-units` | Statistical units with social vulnerability indicators | Academic research only |
| `hamburg-risk-private` | Building-level pluvial flood risk outputs (PFRMA, PFRWB) | Academic research only |

## Components

| Component | Where | Purpose |
|-----------|-------|---------|
| ODRL policies | Nanopub network | Access terms (immutable, signed) |
| Access grants | Nanopub network | Audit trail (immutable, signed) |
| Encrypted data | Zenodo / S3 Pangeo@EOSC | Storage (publicly downloadable, encrypted) |
| Key server | GitHub Pages + Actions | Key distribution + policy enforcement |
| Pipeline code | [urban_pfr_toolbox_hamburg](https://github.com/FAIR2Adapt/urban_pfr_toolbox_hamburg) | Flood risk processing |

## Links

- [Source code](https://github.com/FAIR2Adapt/fair-data-access)
- [Flood risk toolbox](https://github.com/FAIR2Adapt/urban_pfr_toolbox_hamburg)
- [FAIR2Adapt project](https://fair2adapt-eosc.eu)
- [ODRL specification](https://www.w3.org/TR/odrl-model/)
- [Nanopublications](https://nanopub.net/)
