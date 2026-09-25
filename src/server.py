"""The Scanova MCP server for local use (``main.py --stdio``).

Same tools as production (``mcp_http/sdk_server.py``); the credential comes
from MCP_ACCESS_TOKEN in the environment instead of request headers.
"""

from mcp_http.sdk_server import build_server

server = build_server()
