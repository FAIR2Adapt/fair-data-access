#!/usr/bin/env python3
"""Deposit the Hamburg example FDO in ROHub as RO-A.

Completes the reproducible chain:

    fetch_example_data.py   Zenodo DOI            -> plaintext example layer
    (publish nanopubs)      policy + grant        -> the authority for access
    build_fdo_crate.py      encrypt + RO-Crate    -> build/fdo-.../
    deposit_rohub_fdo.py    this script           -> ROHub RO + w3id PID

What goes in, and what deliberately does not:

  IN   ro-crate-metadata.json      the open metadata (hasPolicy -> policy nanopub)
  IN   *.gpkg.enc                  the data, ciphertext only
  IN   policy + grant nanopubs     as typed `Nanopublication` resources
  IN   source data DOI, method paper DOI, code repo, key server   (external links)
  OUT  plaintext data              never
  OUT  the AES dataset key         never -- it lives only in a GitHub Secret

Credentials are read from ~/rohub_username and ~/rohub_pwd (or the ROHUB_USERNAME /
ROHUB_PASSWORD environment variables, which take precedence). They are never logged,
never passed as arguments, and never written anywhere by this script.

Run --dry-run first: it prints the exact deposit plan without touching the network.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CRATE_DIR = REPO / "build" / "fdo-hamburg-buildings-example"

TITLE = "Hamburg building-level pluvial flood-risk example layer (controlled access FDO)"
DESCRIPTION = (
    "A FAIR Digital Object demonstrating machine-actionable controlled access. The metadata "
    "in this Research Object is open; the data distribution is encrypted with AES-256-GCM and "
    "is released only under the ODRL policy recorded in the linked policy nanopublication. "
    "Access decisions are recorded as signed grant nanopublications. The payload is the openly "
    "licensed example layer published with the Hamburg pluvial flood-risk methodology paper, "
    "standing in for the protected FAIR2Adapt CS3 layer, which has the same schema and "
    "building-level granularity. Produced by github.com/FAIR2Adapt/fair-data-access."
)
ROS_TYPE = "Data-centric Research Object"
RESEARCH_AREAS = ["Hydrology", "Environmental research", "Geographical information system"]

SOURCE_DATA_DOI = "https://doi.org/10.5281/zenodo.19860733"
METHOD_PAPER_DOI = "https://doi.org/10.5194/nhess-26-2765-2026"
CODE_REPO = "https://github.com/FAIR2Adapt/fair-data-access"
KEY_SERVER = "https://fair2adapt.github.io/fair-data-access/"

CRED_USER = Path.home() / "rohub_username"
CRED_PASS = Path.home() / "rohub_pwd"


def _credentials() -> tuple[str, str]:
    """Environment first, then the credential files in $HOME. Never echoed."""
    user = os.environ.get("ROHUB_USERNAME")
    pw = os.environ.get("ROHUB_PASSWORD")
    if not user and CRED_USER.exists():
        user = CRED_USER.read_text().strip()
    if not pw and CRED_PASS.exists():
        pw = CRED_PASS.read_text().strip()
    if not user or not pw:
        raise SystemExit(
            "no ROHub credentials: set ROHUB_USERNAME/ROHUB_PASSWORD, or place them in "
            f"{CRED_USER} and {CRED_PASS}"
        )
    return user, pw


def external_resources(policy_np: str, grant_np: str | None) -> list[dict]:
    res = [
        {
            "res_type": "Nanopublication",
            "input_url": policy_np,
            "title": "ODRL access policy (signed nanopublication)",
            "description": (
                "The authority for this dataset's access conditions: permitted actions, purpose "
                "constraint, prohibitions and attribution duty. The RO-Crate references it and "
                "restates nothing; if the two ever disagree, the nanopublication wins."
            ),
        },
        {
            "res_type": "Journal article",
            "input_url": METHOD_PAPER_DOI,
            "title": "Vogelbacher et al. (2026), A high-resolution framework for urban pluvial flood risk mapping",
            "description": "The methodology paper this example layer was published alongside. NHESS 26, 2765-2783.",
        },
        {
            "res_type": "Dataset",
            "input_url": SOURCE_DATA_DOI,
            "title": "Urban Pluvial Flood Risk Toolbox (source of the example layer)",
            "description": "Zenodo record, CC BY 4.0, from which the plaintext example layer is derived.",
        },
        {
            "res_type": "Software source code",
            "input_url": CODE_REPO,
            "title": "fair-data-access",
            "description": "Reference implementation: encryption, DID resolution, policy evaluation, key wrapping.",
        },
        {
            "res_type": "Web Service",
            "input_url": KEY_SERVER,
            "title": "Key server (wrapped keys and DID documents)",
            "description": "Serves per-recipient wrapped dataset keys and the DID documents grants are issued against.",
        },
    ]
    if grant_np:
        res.insert(1, {
            "res_type": "Nanopublication",
            "input_url": grant_np,
            "title": "ODRL access grant (signed nanopublication)",
            "description": (
                "An auditable access decision over this dataset: assignee DID, granted actions, "
                "governing policy and timestamp."
            ),
        })
    return res


def internal_resources() -> list[dict]:
    crate = CRATE_DIR / "ro-crate-metadata.json"
    enc = next(CRATE_DIR.glob("*.enc"), None)
    if not crate.exists():
        raise SystemExit(
            f"missing {crate.relative_to(REPO)} -- run scripts/build_fdo_crate.py first"
        )
    if enc is None:
        raise SystemExit(f"no *.enc ciphertext in {CRATE_DIR.relative_to(REPO)}")
    for stray in CRATE_DIR.iterdir():
        if stray.suffix in {".gpkg", ".csv", ".shp"}:
            raise SystemExit(
                f"refusing to deposit: {stray.name} looks like plaintext data. "
                "Only ciphertext belongs in this Research Object."
            )
    return [
        {"res_type": "File", "file_path": str(crate),
         "title": "ro-crate-metadata.json",
         "description": "RO-Crate 1.1 metadata. hasPolicy points at the ODRL policy nanopublication."},
        {"res_type": "Dataset", "file_path": str(enc),
         "title": enc.name,
         "description": "The example building layer, AES-256-GCM ciphertext. Unusable without a key wrapped for your DID."},
    ]


LICENSE_ID = "cc-by-4.0"
KEYWORDS = ["FAIR Digital Object", "ODRL", "nanopublication", "access control",
            "pluvial flood risk", "climate change adaptation", "FAIR2Adapt", "Hamburg"]
# Canonical values from rohub.zenodo_list_grants(query="101188256") -- not hand-typed.
GRANT_ID = "00k4n6c32::101188256"
GRANT_NAME = "FAIR2Adapt"
GRANT_TITLE = "FAIR to Adapt to Climate Change"
FUNDER_NAME = "European Commission"
FUNDER_DOI = "00k4n6c32"


def _finalise(identifier: str, access_mode: str) -> None:
    """Make the RO openly readable and give it the metadata FAIR/ORE expect."""
    username, password = _credentials()
    import rohub

    rohub.login(username=username, password=password)
    print(f"[rohub] authenticated as {username}")

    # Each step is independent -- one unsupported call should not abort the rest.
    def step(label, fn):
        try:
            fn()
            print(f"[rohub] {label}")
        except (Exception, SystemExit) as exc:  # rohub exits on HTTP errors
            print(f"[rohub] {label} FAILED: {type(exc).__name__}: {str(exc)[:160]}")

    step(f"access mode -> {access_mode}",
         lambda: rohub.ros_update(identifier=identifier, title=TITLE,
                                  research_areas=RESEARCH_AREAS, description=DESCRIPTION,
                                  ros_type=ROS_TYPE, access_mode=access_mode))
    step(f"licence -> {LICENSE_ID}",
         lambda: rohub.ros_set_license(ros_id=identifier, license_id=LICENSE_ID))
    step("keywords",
         lambda: rohub.ros_set_keywords(identifier=identifier, keywords=KEYWORDS))
    # ros_add_funding creates the record; ros_update_funding needs one to exist already.
    step(f"funding -> {GRANT_NAME} ({GRANT_ID})",
         lambda: rohub.ros_add_funding(identifier=identifier, grant_identifier=GRANT_ID,
                                       grant_name=GRANT_NAME, grant_title=GRANT_TITLE,
                                       funder_name=FUNDER_NAME, funder_doi=FUNDER_DOI))
    print()
    print(f"[rohub] https://w3id.org/ro-id/{identifier}")


def _create_only(args) -> None:
    """Create the RO shell so its w3id PID exists before the nanopubs are signed."""
    print(f"Research Object : {TITLE}")
    print(f"Type            : {ROS_TYPE}   Access: {args.access_mode}")
    print(f"Research areas  : {', '.join(RESEARCH_AREAS)}")
    print("Uploads         : none (--create-only)")
    print()
    if args.dry_run:
        print("--dry-run: nothing sent to ROHub.")
        return

    username, password = _credentials()
    import rohub

    rohub.login(username=username, password=password)
    print(f"[rohub] authenticated as {username}")
    ro = rohub.ros_create(title=TITLE, research_areas=RESEARCH_AREAS,
                          description=DESCRIPTION, ros_type=ROS_TYPE,
                          access_mode=args.access_mode)
    identifier = ro["identifier"] if isinstance(ro, dict) else ro.identifier
    pid = f"https://w3id.org/ro-id/{identifier}"
    print(f"[rohub] created RO {identifier}  (access: {args.access_mode})")
    print()
    print(f"    DATASET URI -> {pid}")
    print()
    print("Next: use that as the dataset URI in both nanopublications")
    print("      (nanopubs/drafts/hamburg-buildings-example.md), then re-run this")
    print(f"      script with --identifier {identifier} to upload the crate.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--policy-nanopub", required=False,
                    help="Required unless --create-only")
    ap.add_argument("--grant-nanopub", default=None)
    ap.add_argument("--identifier", default=None,
                    help="Existing RO identifier -- add resources to it instead of creating a new RO")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the deposit plan and exit without contacting ROHub")
    ap.add_argument("--create-only", action="store_true",
                    help="Create the RO shell and print its w3id PID, uploading nothing. "
                         "Use this first: the PID is the dataset URI the nanopubs need.")
    ap.add_argument("--access-mode", default="PUBLIC", choices=["PRIVATE", "PUBLIC", "OPEN"],
                    help="PUBLIC by default. The crate metadata is meant to be openly readable -- "
                         "only ciphertext goes in, so publishing it is safe, and a policy "
                         "nanopublication whose odrl:target 404s would defeat the purpose.")
    ap.add_argument("--finalise", action="store_true",
                    help="Set access mode, licence, authors, keywords and funding on an "
                         "existing RO (use with --identifier). Uploads nothing.")
    args = ap.parse_args()

    if args.create_only:
        _create_only(args)
        return

    if args.finalise:
        if not args.identifier:
            raise SystemExit("--finalise needs --identifier")
        _finalise(args.identifier, args.access_mode)
        return

    if not args.policy_nanopub:
        raise SystemExit("--policy-nanopub is required (or use --create-only)")

    internal = internal_resources()
    external = external_resources(args.policy_nanopub, args.grant_nanopub)

    print(f"Research Object : {TITLE}")
    print(f"Type            : {ROS_TYPE}")
    print(f"Research areas  : {', '.join(RESEARCH_AREAS)}")
    print()
    print("Files to upload:")
    for r in internal:
        size = Path(r["file_path"]).stat().st_size
        print(f"  [{r['res_type']:<8}] {Path(r['file_path']).name}  ({size:,} bytes)")
    print()
    print("Linked resources:")
    for r in external:
        print(f"  [{r['res_type']:<20}] {r['input_url']}")
    print()

    if args.dry_run:
        print("--dry-run: nothing sent to ROHub.")
        return

    username, password = _credentials()

    import rohub

    rohub.login(username=username, password=password)
    print(f"[rohub] authenticated as {username}")

    if args.identifier:
        identifier = args.identifier
        print(f"[rohub] adding to existing RO {identifier}")
    else:
        ro = rohub.ros_create(title=TITLE, research_areas=RESEARCH_AREAS,
                              description=DESCRIPTION, ros_type=ROS_TYPE,
                              access_mode=args.access_mode)
        identifier = ro["identifier"] if isinstance(ro, dict) else ro.identifier
        print(f"[rohub] created RO {identifier}")

    for r in internal:
        rohub.ros_add_internal_resource(identifier=identifier, res_type=r["res_type"],
                                        file_path=r["file_path"], title=r["title"],
                                        description=r["description"])
        print(f"[rohub] uploaded {Path(r['file_path']).name}")

    for r in external:
        rohub.ros_add_external_resource(identifier=identifier, res_type=r["res_type"],
                                        input_url=r["input_url"], title=r["title"],
                                        description=r["description"])
        print(f"[rohub] linked {r['input_url']}")

    pid = f"https://w3id.org/ro-id/{identifier}"
    print()
    print(f"[rohub] done. Persistent identifier: {pid}")
    print("[rohub] Record it in nanopubs/PUBLISHED.md and use it as the dataset URI.")
    print("[rohub] Snapshot with rohub.ros_snapshot(..., create_doi=True) when you want a DOI.")


if __name__ == "__main__":
    main()
