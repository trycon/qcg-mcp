"""Tool annotations (MCP ToolAnnotations) used by registry.py's descriptors.

Hosts use them to decide what needs confirmation; the spec treats annotations
as hints from a trusted server, so keep them accurate: anything that deletes
or removes is destructive.
"""

READ_ONLY_TOOL_ANNOTATIONS_JSON = {
    "readOnlyHint": True,
    "openWorldHint": True,
    "destructiveHint": False,
}
WRITE_TOOL_ANNOTATIONS_JSON = {
    "readOnlyHint": False,
    "openWorldHint": True,
    "destructiveHint": False,
}
DESTRUCTIVE_TOOL_ANNOTATIONS_JSON = {
    "readOnlyHint": False,
    "openWorldHint": True,
    "destructiveHint": True,
}
