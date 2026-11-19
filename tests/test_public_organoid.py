"""Exercise the installed stdio server against saenopy's public OrganoidTFM pair."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import numpy as np
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def exercise(server, data, output):
    raw = data / "raw" / "4_OrganoidTFM"
    reference, = (data / "reference").glob("*.saenopy")
    output.mkdir(parents=True, exist_ok=False)
    params = StdioServerParameters(command=str(server), args=[],
                                   env={"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"})
    with (output / "server.log").open("w") as log:
        async with stdio_client(params, errlog=log) as (read, write), ClientSession(read, write) as client:
            await client.initialize()
            names = [tool.name for tool in (await client.list_tools()).tools]
            assert set(names) == {"inspect_result", "estimate_displacement", "reconstruct_forces", "export_field"}
            calls = []
            async def call(tool, args, expect_error=False):
                response = await client.call_tool(tool, args)
                if bool(response.isError) != expect_error:
                    raise RuntimeError(f"{tool}: {response.content!s}"[:1500])
                result = None if expect_error else (response.structuredContent or json.loads(response.content[0].text))
                calls.append(dict(tool=tool, arguments=args, result=result, expected_error=expect_error))
                (output/"calls.json").write_text(json.dumps(calls,indent=2))
                print(tool, "expected rejection" if expect_error else result, flush=True)
                return result
            await call("inspect_result", dict(result_path=str(reference)))
            measured = output / "organoid-piv.saenopy"
            await call("estimate_displacement", dict(
                reference_template=str(raw/"Pos007_S001_t6_z{z}_ch00.tif"),
                deformed_template=str(raw/"Pos007_S001_t50_z{z}_ch00.tif"), output_path=str(measured),
                voxel_size_um=[1.444,1.444,1.976],window_um=40.,spacing_um=30.,
                signal_to_noise=1.3,drift_correction=True))
            await call("inspect_result",dict(result_path=str(measured)))
            async def export(source,name,filename):
                return await call("export_field",dict(result_path=str(source),field=name,time_index=0,output_csv=str(output/filename)))
            await export(measured,"piv","piv.csv")
            await export(reference,"piv","reference-piv.csv")
            await export(reference,"fitted forces","reference-forces.csv")
            rejected=dict(result_path=str(measured),field="piv",time_index=0,output_csv=str(output/"piv.csv"))
            await call("export_field",rejected,True)
            await call("export_field",dict(rejected,time_index=30,output_csv=str(output/"absent.csv")),True)
            assert not (output/"absent.csv").exists()
            computed, ref = [np.loadtxt(output/name,delimiter=",",skiprows=1) for name in ("piv.csv","reference-piv.csv")]
            assert np.allclose(computed[:,:3],ref[:,:3],atol=1e-12,rtol=0)
            a,b=computed[:,3:],ref[:,3:]
            valid = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
            correlation=float(np.corrcoef(a[valid].ravel(),b[valid].ravel())[0,1])
            rmse=float(np.sqrt(np.mean((a[valid]-b[valid])**2))*1e6)
            comp=dict(nodes=len(a), jointly_finite=int(valid.sum()), pearson_r=correlation, component_rmse_um=rmse)
            print("Reference comparison",comp,flush=True)
            (output/"comparison.json").write_text(json.dumps(comp,indent=2))
            fitted = output/"organoid-force-fit.saenopy"
            await call("reconstruct_forces",dict(result_path=str(measured),output_path=str(fitted),
                mesh_spacing_um=60.,mesh_size_um=[480.,480.,240.],stiffness_pa=6062.,buckling_strain=.0025,
                stiffening_strain=.0804,stiffening_scale=.034,alpha=1e10,max_iterations=80,
                relative_convergence=.01,step_size=.33))
            await call("inspect_result",dict(result_path=str(fitted)))
            forces = await export(fitted,"fitted forces","forces.csv")
            assert forces["max_magnitude"]>0 and forces["finite_vectors"]==forces["nodes"]
            assert valid.sum() > 0 and correlation > .95, comp
            print("PASS: all four MCP tools; public reference comparison and two error cases.",flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("data",type=Path,help="Folder with raw/4_OrganoidTFM and reference/*.saenopy")
    ap.add_argument("output",type=Path,help="New run directory")
    opts=ap.parse_args()
    asyncio.run(exercise(Path(sys.executable).parent / "saenopy-mcp", opts.data.resolve(), opts.output.resolve()))
