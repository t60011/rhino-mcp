"""Rhino integration through the Model Context Protocol."""
from mcp.server.fastmcp import FastMCP, Context
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
import json

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RhinoMCPServer")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("RhinoMCP server starting up")
        yield {}
    finally:
        logger.info("RhinoMCP server shut down")

# Create the MCP server with lifespan support
app = FastMCP(
    "RhinoMCP",
    description="Rhino integration through the Model Context Protocol",
    lifespan=server_lifespan
)

@app.tool()
def get_scene_info(ctx: Context) -> str:
    """Get information about the current Rhino scene"""
    try:
        # TODO: Implement actual Rhino connection
        return json.dumps({"status": "success", "message": "Scene info retrieved"}, indent=2)
    except Exception as e:
        logger.error(f"Error getting scene info from Rhino: {str(e)}")
        return f"Error getting scene info: {str(e)}"

@app.tool()
def create_cube(ctx: Context, size: float = 1.0) -> str:
    """Create a cube in Rhino"""
    try:
        # TODO: Implement actual Rhino connection
        return json.dumps({
            "status": "success",
            "message": f"Created cube with size {size}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Error creating cube in Rhino: {str(e)}")
        return f"Error creating cube: {str(e)}"

@app.tool()
def get_layers(ctx: Context) -> str:
    """Get list of layers in Rhino"""
    try:
        # TODO: Implement actual Rhino connection
        return json.dumps({
            "status": "success",
            "layers": ["Default", "Layer 01", "Layer 02"]
        }, indent=2)
    except Exception as e:
        logger.error(f"Error getting layers from Rhino: {str(e)}")
        return f"Error getting layers: {str(e)}"

@app.tool()
def execute_rhino_code(ctx: Context, code: str) -> str:
    """Execute arbitrary Python code in Rhino"""
    try:
        # TODO: Implement actual Rhino connection
        return json.dumps({
            "status": "success",
            "message": f"Executed code: {code}"
        }, indent=2)
    except Exception as e:
        logger.error(f"Error executing code in Rhino: {str(e)}")
        return f"Error executing code: {str(e)}"

def main():
    """Run the MCP server"""
    app.run(transport='stdio')

if __name__ == "__main__":
    main()