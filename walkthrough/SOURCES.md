# Walkthrough poster

[poster.pdf](poster.pdf) and [poster.png](poster.png) are a one-page, step-by-step tutorial for first-time users: what saenopy does, what you need, how to set up this server, what to ask at each step, and what to check. The poster text and layout are covered by this repository's [license](../LICENSE); the logo and images keep their own terms.

| Content | Source | Terms |
| --- | --- | --- |
| saenopy logo | [saenopy repository](https://github.com/rgerum/saenopy), `saenopy/img/Logo.png` | MIT |
| Organoid image | saenopy's public `4_OrganoidTFM` example, [release v0.7.4](https://github.com/rgerum/saenopy/releases/tag/v0.7.4), plane z26 of the deformed stack | saenopy authors' terms |
| Movement arrows, point count, median and largest movement, and the match to saenopy | The recorded run of `tests/test_public_organoid.py` ([calls](../examples/organoid/test-run/calls.json), [comparison](../examples/organoid/test-run/comparison.json)) | This repository |
| Plot of movement against distance | Drawn from the `piv.csv` table that the test exports with `export_field`. Distance is measured from the point the movement converges on (a weighted least-squares fit); the line is the median in 50 µm bins | This repository |
| Force arrows, iterations, run time, largest force, and the match to saenopy | A fit through this server on 2026-11-19: `reconstruct_forces` on the test's displacement result with saenopy's published settings for this organoid (30 µm mesh spacing, 738 µm mesh, stiffness 6062 Pa, buckling strain 0.0025, stiffening strain 0.0804, stiffening scale 0.034, alpha 1e10, 1,400 iterations, step size 0.33), then `export_field`. It ran all 1,400 iterations in 9,881 s; the largest force was 65 nN. Across all 15,625 mesh nodes its force components correlate with saenopy's published evaluation of the same organoid (`4_OrganoidTFM_evaluated`) at 0.97. The arrows show the largest fifth of the in-plane forces in the central plane | This repository |
