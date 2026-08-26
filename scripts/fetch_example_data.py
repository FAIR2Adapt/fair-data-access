#!/usr/bin/env python3
"""Fetch the Hamburg pluvial flood-risk **example** building layer.

The demo gates a building-level flood-risk dataset, because that is the shape of
data the FAIR2Adapt Hamburg case study (CS3) must keep under controlled access.
The real CS3 layer is private, so we use the openly published example layer that
the case-study authors released alongside their methodology paper:

    Vogelbacher, A., von Szombathely, M., Lennartz, M., Poschlod, B. &
    Sillmann, J. (2026). A high-resolution framework for urban pluvial flood
    risk mapping. Nat. Hazards Earth Syst. Sci. 26, 2765-2783.
    https://doi.org/10.5194/nhess-26-2765-2026

    Data: https://doi.org/10.5281/zenodo.19860733  (CC BY 4.0)

It carries the same schema and the same building-level granularity as the
protected layer -- 37 buildings across 2 statistical units -- so the demo
exercises the identical access-control path without touching sensitive data.

The extracted GeoPackage is a build artefact (gitignored); this script is the
only source of truth for where it came from.
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

ZENODO_RECORD = "19860733"
ZENODO_DOI = "10.5281/zenodo.19860733"
ARCHIVE = "PluvialFloodRiskMap_Data_V2.zip"
LAYER = "Building_ExampleLayer_V2"

REPO = Path(__file__).resolve().parent.parent
DEST = REPO / "examples" / "walkthrough" / "data" / "hamburg-buildings-example.gpkg"


def fetch() -> None:
    url = f"https://zenodo.org/records/{ZENODO_RECORD}/files/{ARCHIVE}?download=1"
    print(f"[fetch] {ZENODO_DOI} -> {ARCHIVE}")
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        resp = client.get(url)
        resp.raise_for_status()

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            zf.extractall(tmpdir)

        lpkx = next(tmpdir.rglob("*.lpkx"), None)
        if lpkx is None:
            raise SystemExit(f"no .lpkx layer package inside {ARCHIVE}")

        # An ArcGIS layer package is a 7-zip archive wrapping the file geodatabase.
        import py7zr

        with py7zr.SevenZipFile(lpkx, "r") as z:
            z.extractall(tmpdir / "lpkx")

        gdb = next(
            (g for g in sorted((tmpdir / "lpkx").rglob("*.gdb")) if _has_layer(g)), None
        )
        if gdb is None:
            raise SystemExit(f"layer {LAYER!r} not found in any geodatabase")

        import geopandas as gpd

        gdf = gpd.read_file(gdb, layer=LAYER)
        DEST.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(DEST, driver="GPKG")

    print(f"[fetch] wrote {DEST.relative_to(REPO)} ({len(gdf)} buildings, {gdf.crs})")


def _has_layer(gdb: Path) -> bool:
    from pyogrio import list_layers

    try:
        return LAYER in {row[0] for row in list_layers(str(gdb))}
    except Exception:
        return False


def main() -> None:
    if DEST.exists() and "--force" not in sys.argv:
        print(f"[fetch] {DEST.relative_to(REPO)} already present -- skipping (use --force to refetch)")
        return
    fetch()


if __name__ == "__main__":
    main()
