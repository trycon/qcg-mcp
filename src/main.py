"""Run the Scanova MCP server locally.

    uv run src/main.py            # Streamable HTTP on :8000 (same app as production)
    uv run src/main.py --stdio    # stdio, credential from MCP_ACCESS_TOKEN
"""

import os
import sys

import anyio


def _stdio() -> None:
    from mcp.server.stdio import stdio_server

    from server import server

    async def run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    anyio.run(run)


if __name__ == "__main__":
    if "--stdio" in sys.argv:
        _stdio()
    else:
        import uvicorn

        from cloud_server import app

        uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)))
