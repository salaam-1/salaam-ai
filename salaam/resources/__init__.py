"""
MCP Resources — expose static or dynamic data to the client.
"""

from salaam.resources import data


def register_all_resources(mcp):
    data.register(mcp)
