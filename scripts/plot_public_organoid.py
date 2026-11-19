"""Render matched raw and displacement panels from the public MCP test run."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("data", type=Path)
ap.add_argument("run", type=Path)
args = ap.parse_args()
image = tifffile.imread(args.data/"raw/4_OrganoidTFM/Pos007_S001_t50_z26_ch00.tif")
field = np.loadtxt(args.run/"piv.csv", delimiter=",", skiprows=1) * 1e6
plane = field[(np.abs(field[:, 2]) < 1e-6) & np.isfinite(field[:, 3:]).all(axis=1)]
lo, hi = np.percentile(image, [1, 99])
height, width = image.shape
fig = plt.figure(figsize=(8.5, 4), layout="constrained")
grid = fig.add_gridspec(1,3,width_ratios=[1,1,.035])
a, b, bar = (fig.add_subplot(grid[0, i]) for i in range(3))
for ax, name in ((a, "A   Raw image"), (b, "B   Matrix displacement")):
    ax.imshow(image, cmap="gray", vmin=lo, vmax=hi)
    ax.set_title(name, loc="left", fontsize=12)
    ax.plot([width*.06, width*.06+100/1.444],[height*.93]*2, color="white", linewidth=2)
    ax.text(width*.06,height*.90,"100 μm",color="white",fontsize=9)
    ax.set(xlim=(-.5,width-.5),ylim=(height-.5,-.5))
    ax.set_axis_off()
# Match saenopy's 2-D renderer: node y maps to image column, node x to row.
marks = b.scatter(width/2+plane[:,1]/1.444,height/2+plane[:,0]/1.444,
                  c=np.linalg.norm(plane[:,3:],axis=1), s=9, vmin=0, vmax=9,
                  cmap="viridis", linewidths=0)
fig.colorbar(marks, cax=bar, label="Displacement (μm)")
fig.savefig(args.run/"before-and-after.png",dpi=190)
print(f"Central plane: {len(plane)} finite nodes; raw gray limits {lo:g}–{hi:g}.")
