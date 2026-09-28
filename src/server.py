try:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("computer-use-tool")
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("computer-use-tool")

from src.registry import DeviceRegistry
from src.router import ToolRouter
from src.tools.observe import register_observe_tools
from src.tools.interact import register_interact_tools
from src.tools.safety import register_safety_tools

registry = DeviceRegistry()
router = ToolRouter(registry)

register_observe_tools(mcp, router, registry)
register_interact_tools(mcp, router)
register_safety_tools(mcp)

if __name__ == "__main__":
    mcp.run()
