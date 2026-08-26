# Nanopublication drafts — Hamburg building-level flood-risk example FDO

Two nanopublications to sign and publish, in this order. They are the **authority** for the
demo's access conditions and access decision; the RO-Crate is built afterwards and only
references them.

Sign as **Anne Fouilloux, ORCID 0000-0002-1784-2920**, licence **CC BY 4.0**.

---

## Dataset URI — fixed by the template, not a free choice

The ODRL Access Policy template hard-codes both prefixes:

```
sub1:datasetUri  nt:hasPrefix "https://fair2adapt.eu/data/"
sub1:policyUri   nt:hasPrefix "https://fair2adapt.eu/policy/"
```

Nanodash displays the prefix and accepts only the suffix, so the values are:

| | |
|---|---|
| Dataset URI | `https://fair2adapt.eu/data/hamburg-buildings-example` |
| Policy URI | `https://fair2adapt.eu/policy/hamburg-buildings-example` |

**These are identifiers, not locators.** `fair2adapt.eu` currently has no DNS records at all
(NXDOMAIN), so they dereference to nothing — as do the dataset URIs in the four
already-published nanopubs. Legitimate in RDF terms, but weak for a paper about FAIR Digital
Objects, and it leaves an unregistered domain in the `odrl:target` of signed, immutable rights
records.

Two consequences, neither blocking:

- **Where the object actually resolves** is the ROHub Research Object
  `https://w3id.org/ro-id/542c8767-2563-44c1-b9df-be0a56d38a84`
  (PUBLIC, LIVE). The RO-Crate carries both — the `fair2adapt.eu` identifier and the ROHub PID
  as its location.
- **Registering `fair2adapt.eu`** and pointing it anywhere sensible would make every existing
  and future nanopub identifier resolve, retroactively. Worth raising with the consortium.

---

## 1 — ODRL Access Policy

Template: **ODRL Access Policy for FAIR Data**
`https://w3id.org/np/RA61D4c7dB5t0B1mLhc78bN2vagqYTXQiJDKY0yImRULI`

| Form field | Value |
|---|---|
| URI of the policy | `https://fair2adapt.eu/policy/hamburg-buildings-example` |
| Type of ODRL policy | `Offer` |
| Applies to dataset | `https://fair2adapt.eu/data/hamburg-buildings-example` |
| Permitted action | `use` |
| Required purpose for access | `Academic Research` (`dpv:AcademicResearch`) |
| Permitted action | `reproduce` |
| Required purpose for access | `Academic Research` (`dpv:AcademicResearch`) |
| Prohibited action | `distribute` |
| Prohibited action | `commercialize` |
| Required duty action | `Attribute` |
| URI of party to attribute | `https://fair2adapt-eosc.eu` |

Auto-generated label: `ODRL policy: https://fair2adapt.eu/data/hamburg-buildings-example`

This is **field-for-field identical** to the production Hamburg policy
`https://w3id.org/np/RAir7keZs8Jy7i8HvRI7X4SmefJtY3jG2WgyFlsZa9-iw`, differing only in the two
URIs — that is deliberate, so the demonstration exercises the same constraint as the real
deployment rather than a softer one.

**Record the returned nanopub URI — step 2 needs it.**

---

## 2 — ODRL Access Grant

Template: **ODRL Access Grant for FAIR Data**
`https://w3id.org/np/RAoLSOhZx_dLX6xnGBN8o1aQSiD8HSrwBshfCjXXSslhE`

> This is the template the Science Live platform offers (`ODRL_ACCESS_GRANT` in its registry).
> It differs from the earlier `RAeRMv…` in exactly two ways: it adds `rdfs:label` for the three
> action URIs so they render as names, and it drops the `FAIR2Adapt` tags and the prefix
> constraints on `datasetUri` / `policyNanopubUri`.
>
> **Because there is no prefix, paste the dataset URI in full and check it character-for-character
> against the policy's target.** A mismatch does not raise an error — it silently produces a grant
> that `verify_access` will never match.

| Form field | Value |
|---|---|
| Grant identifier | `hamburg-buildings-example-grant-001` |
| Grants access to dataset | `https://fair2adapt.eu/data/hamburg-buildings-example` |
| Is granted to (DID) | `https://fair2adapt.github.io/fair-data-access/example-consumer/did.json` |
| For action | `use` |
| For action | `reproduce` |
| Under ODRL policy | *nanopub URI returned by step 1* |
| Granted at time | publication timestamp (`xsd:dateTime`) |

Auto-generated label: `Access grant: https://fair2adapt.eu/data/hamburg-buildings-example -> …/example-consumer/did.json`

### Prerequisite for this one to mean anything

The assignee URL must resolve to the **same** public key the demo actually uses. Three files must
agree:

- `examples/walkthrough/keys/example-consumer-private.pem` (gitignored)
- `examples/walkthrough/keys/did/example-consumer.json`
- `docs/example-consumer/did.json`  ← what the assignee URL resolves to

They agree today, but `scripts/generate_example_keys.py` regenerates the first two on a fresh
clone and **not** the third, so after any fresh clone the published grant would describe an
identity no reader can reproduce. Commit a fixed, clearly-labelled demo keypair (it protects only
openly-licensed example data, so it is not a secret) and drop the regeneration path — then this
grant stays verifiable indefinitely.

---

## Afterwards

```bash
python3 scripts/fetch_example_data.py
python3 scripts/build_fdo_crate.py \
    --dataset-uri   'https://fair2adapt.eu/data/hamburg-buildings-example' \
    --policy-nanopub '<policy nanopub URI from step 1>' \
    --grant-nanopub  '<grant nanopub URI from step 2>' \
    --key-out        dataset-key.hex        # KEEP SECRET, store as a GitHub Secret
```

Then deposit `build/fdo-hamburg-buildings-example/` in ROHub as **RO-A**, and record both URIs in
`nanopubs/PUBLISHED.md`.
