#!/usr/bin/env python3
"""Build the RO-Crate for the Hamburg example FDO, ready for deposit in ROHub.

The crate is the *open* half of the object: anyone may fetch and read it, and it
declares -- machine-actionably -- what may be done with the data and how to ask.
The data itself travels only as ciphertext, so publishing the crate publicly does
not publish the data.

    crate (public)  --hasPolicy-->  ODRL policy nanopub (signed)
          |                                   ^
          +--distribution--> *.gpkg.enc       |
                                    access grant nanopub (signed) --underPolicy--+

Source data: Vogelbacher et al. (2026), Zenodo 10.5281/zenodo.19860733 (CC BY 4.0).
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

from fair_data_access.encrypt import encrypt_file, generate_key
from fair_data_access.rocrate import add_encrypted_file_to_crate

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "examples" / "walkthrough" / "data" / "hamburg-buildings-example.gpkg"
BUILD = REPO / "build" / "fdo-hamburg-buildings-example"

SOURCE_DATA_DOI = "https://doi.org/10.5281/zenodo.19860733"
METHOD_PAPER_DOI = "https://doi.org/10.5194/nhess-26-2765-2026"
KEY_SERVER = "https://fair2adapt.github.io/fair-data-access/"
AUTHOR_ORCID = "https://orcid.org/0000-0002-1784-2920"
ENC_NAME = "hamburg-buildings-example.gpkg.enc"


ROHUB_RO = "https://w3id.org/ro-id/542c8767-2563-44c1-b9df-be0a56d38a84"


def base_crate(dataset_uri: str, rohub_ro: str = ROHUB_RO) -> dict:
    """Minimal RO-Crate 1.1 root. The encrypted file is added by rocrate.py."""
    return {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
                "about": {"@id": "./"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                # `identifier` is what the ODRL policy names as odrl:target. Its prefix is
                # fixed by the nanopub template (nt:hasPrefix https://fair2adapt.eu/data/) and
                # that domain does not currently resolve -- so `sameAs` carries the location
                # where this object can actually be retrieved.
                "identifier": dataset_uri,
                "sameAs": {"@id": rohub_ro},
                "name": "Hamburg building-level pluvial flood-risk example layer (controlled access)",
                "description": (
                    "A FAIR Digital Object demonstrating controlled access to building-level "
                    "pluvial flood-risk data. The metadata in this crate is open; the data "
                    "distribution is encrypted with AES-256-GCM and released only under the "
                    "ODRL policy referenced by hasPolicy. The payload is the openly licensed "
                    "example layer published with the Hamburg flood-risk methodology paper, "
                    "standing in for the protected FAIR2Adapt CS3 layer, which has the same "
                    "schema and building-level granularity."
                ),
                "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
                "datePublished": date.today().isoformat(),
                "author": {"@id": AUTHOR_ORCID},
                "isBasedOn": {"@id": SOURCE_DATA_DOI},
                "citation": {"@id": METHOD_PAPER_DOI},
                "hasPart": [],
            },
            {
                "@id": AUTHOR_ORCID,
                "@type": "Person",
                "name": "Anne Fouilloux",
                "affiliation": {"@id": "https://ror.org/01ggx4157"},
            },
            {
                "@id": SOURCE_DATA_DOI,
                "@type": "Dataset",
                "name": "Urban Pluvial Flood Risk Toolbox (example data)",
                "creditText": (
                    "Vogelbacher, A., von Szombathely, M., Lennartz, M., Poschlod, B. & "
                    "Sillmann, J. (2025). Urban Pluvial Flood Risk Toolbox. Zenodo."
                ),
                "license": {"@id": "https://creativecommons.org/licenses/by/4.0/"},
            },
            {
                "@id": METHOD_PAPER_DOI,
                "@type": "ScholarlyArticle",
                "name": "A high-resolution framework for urban pluvial flood risk mapping",
                "creditText": (
                    "Vogelbacher, A., von Szombathely, M., Lennartz, M., Poschlod, B. & "
                    "Sillmann, J. (2026). Nat. Hazards Earth Syst. Sci. 26, 2765-2783."
                ),
            },
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset-uri", required=True,
                    help="The dataset's own persistent identifier -- the same URI the policy "
                         "nanopublication names as odrl:target. Not a repository location.")
    ap.add_argument("--policy-nanopub", required=True,
                    help="URI of the published ODRL policy nanopublication (the authority)")
    ap.add_argument("--grant-nanopub", default=None,
                    help="URI of a published access grant nanopublication, if any")
    ap.add_argument("--rohub-ro", default=ROHUB_RO,
                    help="ROHub Research Object PID -- the resolvable location (crate sameAs)")
    ap.add_argument("--key-out", default=None,
                    help="Write the AES-256 dataset key here (default: print only)")
    args = ap.parse_args()

    checked = [(args.dataset_uri, "--dataset-uri"), (args.policy_nanopub, "--policy-nanopub")]
    if args.grant_nanopub:
        checked.append((args.grant_nanopub, "--grant-nanopub"))
    for value, label in checked:
        if "{{" in value or value.strip() in {"", "TBD"}:
            raise SystemExit(f"{label} looks like a placeholder ({value!r}) -- refusing to build")

    if not SOURCE.exists():
        raise SystemExit(f"missing {SOURCE.relative_to(REPO)} -- run scripts/fetch_example_data.py first")

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)

    dataset_key = generate_key()
    encrypt_file(str(SOURCE), output_path=str(BUILD / ENC_NAME), key=dataset_key)

    crate_path = BUILD / "ro-crate-metadata.json"
    crate_path.write_text(json.dumps(base_crate(args.dataset_uri, args.rohub_ro), indent=2))

    add_encrypted_file_to_crate(
        crate_metadata_path=crate_path,
        encrypted_file_id=ENC_NAME,
        original_name="Hamburg building-level flood-risk example layer (AES-256-GCM encrypted)",
        description=(
            "37 building footprints across 2 statistical units, with the residency and "
            "socioeconomic indicator fields used by the urban_pfr pipeline. Same schema and "
            "granularity as the protected FAIR2Adapt CS3 layer."
        ),
        encoding_format="application/geopackage+sqlite3",
        policy_nanopub_uri=args.policy_nanopub,
        key_server_url=KEY_SERVER,
        distribution_urls=[{"name": "ROHub", "contentUrl": ENC_NAME}],
    )

    # The grant is recorded as provenance: the crate points at the decision, it does
    # not restate it. The nanopublication remains the authority.
    if args.grant_nanopub:
        crate = json.loads(crate_path.read_text())
        for entry in crate["@graph"]:
            if entry.get("@id") == ENC_NAME:
                entry["accessGrant"] = {"@id": args.grant_nanopub}
        crate["@graph"].append({
            "@id": args.grant_nanopub,
            "@type": "CreativeWork",
            "name": "ODRL access grant (nanopublication)",
            "description": "Signed, immutable record of an access decision over this dataset.",
        })
        crate_path.write_text(json.dumps(crate, indent=2))

    print(f"[crate] identifier {args.dataset_uri}")
    print(f"[crate] resolves at {args.rohub_ro}")
    print(f"[crate] {BUILD.relative_to(REPO)}/")
    print(f"[crate]   ro-crate-metadata.json  (hasPolicy -> {args.policy_nanopub})")
    if args.grant_nanopub:
        print(f"[crate]                           (accessGrant -> {args.grant_nanopub})")
    print(f"[crate]   {ENC_NAME}  ({(BUILD / ENC_NAME).stat().st_size:,} bytes, ciphertext)")
    if args.key_out:
        Path(args.key_out).write_text(dataset_key.hex())
        print(f"[crate]   dataset key -> {args.key_out}  (KEEP SECRET; store as a GitHub Secret)")
    else:
        print(f"[crate]   dataset key (hex): {dataset_key.hex()}")
        print("[crate]   ^ KEEP SECRET -- store as a GitHub Secret, never commit")


if __name__ == "__main__":
    main()
