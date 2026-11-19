# Changelog

## [0.1.0] - 2026-11-19

First public release.

- Four tools for saenopy's 3D solver, listed in the order of work: `estimate_displacement`, `reconstruct_forces`, `export_field`, and `inspect_result`. Each tool description names the step that must come before it.
- Absolute paths only, and outputs are written as new files: a failed run leaves no partial file and never replaces an existing one.
- `src/` package layout with the `saenopy-mcp` command, fast input-handling tests, and an integration test that runs all four tools through an MCP client on saenopy's public organoid example and compares the displacement with saenopy's published result.
- The example data are downloaded by `scripts/fetch_organoid_example.py` instead of being stored in the repository.
