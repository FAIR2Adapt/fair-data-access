# Published artefacts

Every URI below is live and independently resolvable. Nanopublications are cited in the
`https://w3id.org/np/<code>` form because that is the one that content-negotiates to RDF; the
Science Live platform also mints `https://w3id.org/sciencelive/np/<code>`, which currently
returns an HTML view for every RDF media type. Both denote the same nanopublication — the
trusty-URI artifact code is a hash of the content.

## Hamburg building-level flood-risk example FDO (the paper's demonstration)

| Artefact | URI |
|---|---|
| Research Object (RO-A) | https://w3id.org/ro-id/542c8767-2563-44c1-b9df-be0a56d38a84 |
| ODRL policy | https://w3id.org/np/RAkCc5ernqtkD4bGumI2wsJOC14-jy1sbYtWwukTL_bgM |
| Access grant | https://w3id.org/np/RAhUhIjOyF36Pc2gXquYf2JP4QWmrdPLiBrJcwJubIU2U |
| Source data | https://doi.org/10.5281/zenodo.19860733 (CC BY 4.0) |
| Method paper | https://doi.org/10.5194/nhess-26-2765-2026 |

Policy: `odrl:Offer` on `https://fair2adapt.eu/data/hamburg-buildings-example`; permits `use`
and `reproduce` constrained to `dpv:AcademicResearch`; prohibits `distribute` and
`commercialize`; duty to attribute `https://fair2adapt-eosc.eu`. Field-for-field identical to
the production Hamburg policy apart from the two URIs, so the demonstration exercises the same
constraint as the real deployment.

Grant: `odrl:Agreement` granting `use` and `reproduce` to
`https://fair2adapt.github.io/fair-data-access/example-consumer/did.json`, under the policy
above, generated 2026-08-26T19:10:58Z.

Verified end-to-end against the live nanopub network: signature valid, grant creator matches the
policy publisher, and an unauthorised DID is refused.

## Hamburg deployment (real, protected data)

| Artefact | URI |
|---|---|
| ODRL policy | https://w3id.org/np/RAir7keZs8Jy7i8HvRI7X4SmefJtY3jG2WgyFlsZa9-iw |
| Access grant | https://w3id.org/np/RAABfWGtaYJE4YiMfzetpUe_KOupSEAiulFwMRcLcgZys |

The grant's assignee is the project's own repository DID rather than an external researcher's,
so this is a signed validation that the policy-to-grant chain executes on the real dataset, not
evidence of a third-party access request.

## Biodiversity quickstart (first published instance)

| Artefact | URI |
|---|---|
| ODRL policy | https://w3id.org/np/RATzaPLmaUtrmZ6w9WILh8jxF3F-e23xPrFHJQFO3-U6Y |
| Access grant | https://w3id.org/np/RARNOf26WWMYa0BkLWpMURNRqjwSVGXj-4A9r9iCBpruM |

Retained as the minimal example and as the first instance of the pattern; a second data shape
through the same mechanism supports the generalisability claim.

## Templates

| Template | URI |
|---|---|
| ODRL Access Policy for FAIR Data | https://w3id.org/np/RA61D4c7dB5t0B1mLhc78bN2vagqYTXQiJDKY0yImRULI |
| ODRL Access Grant for FAIR Data | https://w3id.org/np/RAoLSOhZx_dLX6xnGBN8o1aQSiD8HSrwBshfCjXXSslhE |

The grant template is the one the Science Live platform offers. An earlier version,
`RAeRMv6jOibLPIYBMOGu_FsX6NQ6B59KJCgCFkue4z7Ac`, signed the two grants above it in this file;
records stay pinned to whichever template version signed them, because nanopublications are
immutable.
