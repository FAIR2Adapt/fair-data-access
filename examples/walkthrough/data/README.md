# Demo biodiversity observations

**This is synthetic demo data.** It is not real biodiversity data from any
actual survey. It is designed to look realistic enough to be a meaningful
demonstration of FAIR2Adapt's access-control workflow, but every row is
fabricated.

## What it represents

A small Mediterranean coastal biodiversity survey, with 20 observations of
species across three habitats (seagrass meadow, rocky reef/seabed, coastal
open water). The location (near Marseille, France) and species are plausible
for the region but no observations are real.

## Why synthetic?

The FAIR2Adapt public demo needs a dataset that:

1. **Can be distributed freely** — no licensing, privacy, or rights concerns
2. **Is small** — fits in git, easy to download, quick to encrypt/decrypt
3. **Is clearly labeled as demo** — avoids any confusion with real research data
4. **Has a plausible shape** — so the access control workflow looks realistic

Synthetic data meets all four requirements without requiring us to curate a
public dataset and track its licence terms.

## Parsing note

The CSV starts with comment lines prefixed with `#` that reinforce the
synthetic nature of the data. Most parsers read these as data rows by
default. To skip them, pass a comment argument:

```python
import pandas as pd
df = pd.read_csv("biodiversity-observations.csv", comment="#")
```

```bash
csvkit:  csvlook --skip-lines 4 biodiversity-observations.csv
```

## Columns

| Column | Description |
| --- | --- |
| `observation_id` | Unique ID (`obs-NNN`) |
| `scientific_name` | Scientific species name |
| `common_name` | Common species name |
| `latitude` | Observation latitude (decimal degrees) |
| `longitude` | Observation longitude (decimal degrees) |
| `observation_date` | YYYY-MM-DD |
| `observer_id` | Anonymised observer (`obs-A`, `obs-B`, `obs-C`) |
| `count` | Number of individuals observed |
| `habitat` | Habitat type |
| `notes` | Free-text observation notes |

## Using real data instead

If you want to adapt this demo for real data, replace `biodiversity-observations.csv`
with your own file and update the `datasetUri` in `../policies/demo_policy.jsonld`
to point to the real dataset's URI. The access-control workflow is agnostic
to the data's shape — it encrypts and gates access to whatever file you
give it.
