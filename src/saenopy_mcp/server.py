"""MCP tools for 3D traction force microscopy with saenopy.

The tools follow saenopy's order of work: estimate_displacement, then
reconstruct_forces, then export_field; inspect_result can run at any point.
"""
from __future__ import annotations

import os
import shutil
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("saenopy")
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Index = Annotated[int, Field(ge=0)]
FieldName = Literal["piv", "target deformations", "fitted deformations", "fitted forces"]


def local_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("Supply an absolute local path.")
    return Path(os.path.abspath(path))


def read_result(value):
    import saenopy
    path = local_path(value)
    if path.suffix != ".saenopy" or not path.is_file():
        raise ValueError("Expected an existing 3D .saenopy result.")
    return saenopy.Result.load(path)


@contextmanager
def new_file(value, suffix):
    """Publish a finished file without replacing a pre-existing result."""
    dest = local_path(value)
    if dest.suffix != suffix or not dest.parent.is_dir():
        raise ValueError(f"Output must end in {suffix} and have an existing parent directory.")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(dest)
    # Keep the native result at the final directory depth for relative stack paths.
    staged = dest.with_name(f".{uuid.uuid4().hex}{suffix}")
    try:
        yield staged
        try:
            os.link(staged, dest)
        except OSError:
            fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as out_f, staged.open("rb") as in_f:
                shutil.copyfileobj(in_f, out_f)
    finally:
        staged.unlink(missing_ok=True)


def measured_field(result, name, time_index):
    mesh, vectors = result.get_field_data(name, time_index)
    if mesh is None or vectors is None:
        raise ValueError(f"No {name} field at index {time_index}.")
    vectors = np.asarray(vectors)
    if vectors.shape != mesh.nodes.shape or vectors.ndim != 2 or vectors.shape[1] != 3:
        raise ValueError("Node coordinates and vectors must both be N x 3.")
    return mesh.nodes, vectors


def stats(vectors):
    valid = np.isfinite(vectors).all(axis=1)
    norm = np.linalg.norm(vectors[valid], axis=1)
    return dict(nodes=len(vectors), finite_vectors=int(valid.sum()),
                median_magnitude=float(np.median(norm)) if norm.size else None,
                max_magnitude=float(np.max(norm)) if norm.size else None)


@mcp.tool()
def estimate_displacement(reference_template: str, deformed_template: str, output_path: str,
                          voxel_size_um: tuple[Positive, Positive, Positive], window_um: Positive,
                          spacing_um: Positive, signal_to_noise: Positive, drift_correction: bool) -> dict:
    """Step 1. Measure the 3D matrix displacement between one relaxed and one deformed z-stack (PIV). Templates are absolute single-channel TIFF paths with {z}, or a multipage .tif[z]. Voxel spacing is x, y, z in micrometres. Writes a new .saenopy file for reconstruct_forces or export_field."""
    import saenopy
    from saenopy.stack import Stack, format_glob
    ref, active = map(local_path, (reference_template, deformed_template))
    if ref == active or spacing_um > window_um:
        raise ValueError("Use distinct input stacks and grid spacing no larger than the window.")
    for p in (ref, active):
        if any(c in str(p.parent) for c in ("*", "?", "{", "}")) or not p.parent.is_dir():
            raise ValueError("Parent directory must exist and contain no wildcards or template placeholders.")
        if any(c in p.name for c in ("*", "?", "{t", "{c")) or not ("{z}" in p.name or p.name.endswith(".tif[z]")):
            raise ValueError("Select one time point and channel per template; use {z} in the filename or .tif[z].")
        if format_glob(str(p))[0].empty:
            raise ValueError(f"No matching TIFF planes found for template: {p.name}")
    piv = dict(window_size=window_um, element_size=spacing_um,
               signal_to_noise=signal_to_noise, drift_correction=drift_correction)
    with new_file(output_path, ".saenopy") as stage:
        relaxed, deformed = [Stack(str(p), tuple(voxel_size_um)) for p in (ref, active)]
        shape = deformed.shape
        if len(relaxed.shape) != 4 or len(shape) != 4 or relaxed.shape[3] != 1 or shape[3] != 1:
            raise ValueError("Expected single-channel 3D z-stacks.")
        field = saenopy.get_displacements_from_stacks(relaxed, deformed, **piv)
        summary = stats(field.displacements_measured)
        if not summary["finite_vectors"]:
            raise ValueError("No finite displacement vectors were recovered.")
        r = saenopy.Result(output=str(stage), template=str(active), stack=[deformed], stack_reference=relaxed)
        r.piv_parameters, r.mesh_piv, r.solvers = piv, [field], [None]
        r.save()
    return dict(path=output_path, shape_yxzc=list(shape), unit="m", **summary)


@mcp.tool()
def reconstruct_forces(result_path: str, output_path: str, mesh_spacing_um: Positive,
                       stiffness_pa: Positive, buckling_strain: Positive | None,
                       stiffening_strain: Positive | None, stiffening_scale: Positive | None,
                       alpha: Positive, max_iterations: Annotated[int, Field(ge=1)],
                       relative_convergence: Positive, step_size: Annotated[float, Field(gt=0, le=1)],
                       mesh_size_um: tuple[Positive, Positive, Positive] | None = None) -> dict:
    """Step 2. Fit nodal forces to the displacement saved by estimate_displacement, writing a new .saenopy file. Pass all three nonlinear strains as null for a linear material. A null mesh_size_um uses the PIV extent. The result reports whether the iteration limit was reached separately from the force magnitude."""
    import saenopy
    from saenopy.materials import SemiAffineFiberMaterial
    r = read_result(result_path)
    if r.stack_reference is None or len(r.mesh_piv) != 1 or r.mesh_piv[0] is None:
        raise ValueError("This fit requires one measured PIV field and a separate relaxed reference stack.")
    if (stiffening_strain is None) != (stiffening_scale is None):
        raise ValueError("Supply both stiffening parameters or leave both null.")
    grid = dict(element_size=mesh_spacing_um, mesh_size=mesh_size_um or "piv", reference_stack="first")
    material = dict(k=stiffness_pa, d_0=buckling_strain, lambda_s=stiffening_strain, d_s=stiffening_scale)
    fit = dict(alpha=alpha, step_size=step_size, max_iterations=max_iterations, rel_conv_crit=relative_convergence)
    with new_file(output_path, ".saenopy") as stage:
        piv = r.mesh_piv[0]
        solver = saenopy.interpolate_mesh(piv, piv.displacements_measured, grid)
        solver.set_material_model(SemiAffineFiberMaterial(**material))
        history = np.asarray(solver.solve_regularized(**fit))
        if not np.isfinite(history).all():
            raise ValueError("Nonfinite solver objective; review data, material and mesh.")
        r.mesh_parameters, r.material_parameters = grid, material
        r.solve_parameters = dict(fit, prev_t_as_start=False)
        r.solvers = [solver]
        _, forces = measured_field(r, "fitted forces", 0)
        summary = stats(forces)
        if summary["finite_vectors"] != summary["nodes"]:
            raise ValueError("Nonfinite fitted force field.")
        r.save(str(stage))
    steps = len(history) - 1
    return dict(path=output_path, unit="N", iterations=steps,
                reached_iteration_limit=steps >= max_iterations, **summary)


@mcp.tool()
def export_field(result_path: str, field: FieldName, time_index: Index, output_csv: str) -> dict:
    """Step 3. Export node coordinates (m) and one field (m or N) to a new CSV. "piv" needs estimate_displacement; the fitted fields need reconstruct_forces. Invalid entries stay NaN. Fitted forces follow saenopy's displayed sign and regularisation mask."""
    r = read_result(result_path)
    if field in ("fitted forces", "fitted deformations"):
        if time_index >= len(r.solvers) or r.solvers[time_index] is None or r.solvers[time_index].regularisation_results is None:
            raise ValueError("No completed force fit at this index.")
    coords, values = measured_field(r, field, time_index)
    unit, prefix = ("N", "f") if field == "fitted forces" else ("m", "u")
    header = ["x_m", "y_m", "z_m"] + [f"{prefix}{axis}_{unit}" for axis in "xyz"]
    with new_file(output_csv, ".csv") as stage:
        np.savetxt(stage, np.column_stack((coords, values)), delimiter=",", header=",".join(header), comments="")
    return dict(path=output_csv, field=field, unit=unit, **stats(values))


@mcp.tool()
def inspect_result(result_path: str) -> dict:
    """Any step. Report what a 3D .saenopy file holds (voxel size, which fields exist, and the parameters used) without opening its raw image planes."""
    import saenopy
    r = read_result(result_path)
    return dict(saenopy_version=saenopy.__version__, image_stacks=len(r.stacks),
                separate_reference=r.stack_reference is not None, time_interval_s=r.time_delta,
                voxel_size_um=list(r.stacks[0].voxel_size) if r.stacks else None,
                fields=[{"index": i, "piv": p is not None and p.displacements_measured is not None,
                         "force_fit": s is not None and s.regularisation_results is not None}
                        for i, (p, s) in enumerate(zip(r.mesh_piv, r.solvers))],
                piv=r.piv_parameters, mesh=r.mesh_parameters,
                material=r.material_parameters, solver=r.solve_parameters)
