# Third-party notices

The code in this repository (`src/`, `tests/`, and `scripts/`) is covered by [LICENSE](LICENSE) (BSD-3-Clause). It bundles no third-party code. Third-party software and data keep their own terms and are not relicensed.

## saenopy

The server calls [saenopy](https://github.com/rgerum/saenopy) at run time. saenopy is developed by Richard Gerum, David Böhringer, and colleagues, and is distributed under the MIT license, except for modules under `saenopy/gui/common/`, which are GPL-3.0-or-later. Cite saenopy as described in its repository (Böhringer et al., *Nature Physics*, 2024).

## Public organoid example

The integration test uses the `4_OrganoidTFM` dataset from the saenopy project: the raw stacks (`4_OrganoidTFM.zip`) and the evaluated result (`4_OrganoidTFM_evaluated.zip`) from the [saenopy v0.7.4 release](https://github.com/rgerum/saenopy/releases/tag/v0.7.4), as listed in saenopy's [examples.py](https://github.com/rgerum/saenopy/blob/master/saenopy/examples.py). The data are not stored in this repository; `scripts/fetch_organoid_example.py` downloads them from that release. They remain subject to the saenopy authors' terms.

The stored test run in `examples/organoid/test-run/` contains results computed from that dataset: the before-and-after figure, the comparison summary, the ordered tool calls, and the methods text. They document the test and credit the saenopy project as the source of the images.

## Runtime dependencies

Installing the server installs these packages under their own licenses:

- `saenopy` (MIT; GPL-3.0-or-later modules under `saenopy/gui/common/`)
- `openpiv` and `compactionanalyzer` (GPL-3.0-or-later)
- `PySide6` (LGPL-3.0-only, GPL-2.0-only, or GPL-3.0-only)
- `gmsh` (GPL-2.0-or-later)
- `mcp`, `numpy`, `scipy`, `tifffile`, and `matplotlib` (MIT or BSD)

Anyone who distributes a frozen binary that combines these packages must meet the copyleft terms of the GPL-licensed ones.

## Walkthrough poster

The logo and images in `walkthrough/poster.pdf` and `walkthrough/poster.png` keep their own terms; [walkthrough/SOURCES.md](walkthrough/SOURCES.md) lists each source and license.
