"""Start the saenopy MCP server on stdio."""
import os
import sys

from .server import mcp


def main() -> None:
    # Keep native-library and PIV progress output off the stdio JSON-RPC stream.
    wire = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf8", buffering=1)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    import asyncio
    from mcp.server.stdio import stdio_server
    import anyio
    async def serve():
        async with stdio_server(stdout=anyio.wrap_file(wire)) as (reader, writer):
            await mcp._mcp_server.run(reader, writer, mcp._mcp_server.create_initialization_options())
    try:
        asyncio.run(serve())
    finally:
        wire.close()



if __name__ == "__main__":
    main()
