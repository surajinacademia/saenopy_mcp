"""Download saenopy's public OrganoidTFM example for the integration test.

The data are not stored in this repository. They are fetched from the saenopy
project's v0.7.4 release (the URLs in saenopy/examples.py) into:

    <folder>/raw/4_OrganoidTFM/*.tif
    <folder>/reference/Pos007_S001_t50_z{z}_ch00_eval.saenopy
"""
import argparse
import io
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://github.com/rgerum/saenopy/releases/download/v0.7.4/"
EVALUATED = "Pos007_S001_t50_z{z}_ch00_eval.saenopy"


def download(name: str) -> zipfile.ZipFile:
    with urllib.request.urlopen(BASE + name, timeout=300) as response:
        return zipfile.ZipFile(io.BytesIO(response.read()))


def safe_target(root: Path, member: str) -> Path:
    target = (root / member).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Refusing to extract outside {root}: {member}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, help="Destination, for example examples/organoid")
    folder = parser.parse_args().folder
    raw = folder / "raw"
    reference = folder / "reference"
    raw.mkdir(parents=True, exist_ok=True)
    reference.mkdir(parents=True, exist_ok=True)

    archive = download("4_OrganoidTFM.zip")
    stacks = [m for m in archive.infolist() if m.filename.endswith(".tif")]
    for member in stacks:
        name = "4_OrganoidTFM/" + Path(member.filename).name
        safe_target(raw, name).parent.mkdir(parents=True, exist_ok=True)
        safe_target(raw, name).write_bytes(archive.read(member))
    print(f"{len(stacks)} TIFF planes -> {raw / '4_OrganoidTFM'}")

    evaluated = download("4_OrganoidTFM_evaluated.zip")
    member = next(m for m in evaluated.namelist() if m.endswith(EVALUATED))
    safe_target(reference, EVALUATED).write_bytes(evaluated.read(member))
    print(f"Evaluated reference -> {reference / EVALUATED}")


if __name__ == "__main__":
    main()
