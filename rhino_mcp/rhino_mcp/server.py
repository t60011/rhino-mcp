"""Rhino integration through the Model Context Protocol."""
from mcp.server.fastmcp import FastMCP, Context, Image
import logging
import os
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional
import json
import io
from PIL import Image as PILImage
from pathlib import Path

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logging.info(f"Loaded environment variables from {env_path}")
except ImportError:
    logging.warning("python-dotenv not installed. Install it to use .env files: pip install python-dotenv")

# Import our tool modules
from .replicate_tools import ReplicateTools
from .rhino_tools import RhinoTools, get_rhino_connection
from .grasshopper_tools import GrasshopperTools, get_grasshopper_connection
from .utility_tools import UtilityTools

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RhinoMCPServer")

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    rhino_conn = None
    gh_conn = None
    
    try:
        logger.info("RhinoMCP server starting up")
        
        # Try to connect to Rhino script
        try:
            rhino_conn = get_rhino_connection()
            rhino_conn.connect()
            logger.info("Successfully connected to Rhino script")
        except Exception as e:
            logger.warning("Could not connect to Rhino script: {0}".format(str(e)))
        
        # Try to connect to Grasshopper script
        try:
            gh_conn = get_grasshopper_connection()
            # Just check if the server is available - don't connect yet
            if gh_conn.check_server_available():
                logger.info("Grasshopper server is available")
            else:
                logger.warning("Grasshopper server is not available. Start the GHPython component in Grasshopper to enable Grasshopper integration.")
        except Exception as e:
            logger.warning("Error checking Grasshopper server availability: {0}".format(str(e)))
        
        yield {}
    finally:
        logger.info("RhinoMCP server shut down")
        
        # Clean up connections
        if rhino_conn:
            try:
                rhino_conn.disconnect()
                logger.info("Disconnected from Rhino script")
            except Exception as e:
                logger.warning("Error disconnecting from Rhino: {0}".format(str(e)))
        
        if gh_conn:
            try:
                gh_conn.disconnect()
                logger.info("Disconnected from Grasshopper script")
            except Exception as e:
                logger.warning("Error disconnecting from Grasshopper: {0}".format(str(e)))

# Create the MCP server with lifespan support
#if fastmcp support description
try:
    app = FastMCP(
        "RhinoMCP",
        description="Rhino integration through the Model Context Protocol",
        lifespan=server_lifespan
    )
#if fastmcp don't support description
except TypeError as e:
    app = FastMCP(
        "RhinoMCP",
        #description="Rhino integration through the Model Context Protocol",
        lifespan=server_lifespan
    )

# Initialize tool collections
replicate_tools = ReplicateTools(app)
rhino_tools = RhinoTools(app)
grasshopper_tools = GrasshopperTools(app)
utility_tools = UtilityTools(app)

@app.prompt()
def rhino_creation_strategy() -> str:
    """Defines the preferred strategy for creating and managing objects in Rhino"""
    return """When working with Rhino through MCP, follow these guidelines:

    Especially when working with geometry, iterate with smaller steps and check the scene state from time to time.
    Act strategically with a long-term plan, think about how to organize the data and scene objects in a way that is easy to maintain and extend, by using layers and metadata (name, description),
    with the get_objects_with_metadata() function you can filter and select objects based on this metadata. You can access objects, and with the "type" attribute you can check their geometry type and
    access the geometry specific properties (such as corner points etc.) to create more complex scenes with spatial consistency. Start from sparse to detail (e.g. first the building plot, then the wall, then the window etc. - it is crucial to use metadata to be able to do that)

    1. Scene Context Awareness:
       - Always start by checking the scene using get_scene_info() for basic overview
       - Use the capture_viewport to get an image from viewport to get a quick overview of the scene
       - Use get_objects_with_metadata() for detailed object information and filtering
       - The short_id in metadata can be displayed in viewport using capture_viewport()

    2. Object Creation and Management:
       - When creating objects, ALWAYS call add_object_metadata() after creation (The add_object_metadata() function is provided in the code context)   
       - Use meaningful names for objects to help with you with later identification, organize the scenes with layers (but not too many layers)
       - Think about grouping objects (e.g. two planes that form a window)
    
    3. Always check the bbox for each item so that (it's stored as list of points in the metadata under the key "bbox"):
            - Ensure that all objects that should not be clipping are not clipping.
            - Items have the right spatial relationship.

    4. Code Execution:
       - This is Rhino 7 with IronPython 2.7 - no f-strings or modern Python features etc
       - DONT FORGET NO f-strings! No f-strings, No f-strings!
       - Prefer automated solutions over user interaction, unless its requested or it makes sense or you struggle with errors
       - You can use rhino command syntax to ask the user questions e.g. "should i do "A" or "B"" where A,B are clickable options

    5. Best Practices:
       - Keep objects organized in appropriate layers
       - Use meaningful names and descriptions
       - Use viewport captures to verify visual results
    """

@app.prompt()
def grasshopper_usage_strategy() -> str:
    """Defines the preferred strategy for working with Grasshopper through MCP"""
    return """When working with Grasshopper through MCP, follow these guidelines:

    2. Document Exploration:
       - Use get_gh_context() to get an overview of all components and their connections
       - Use simplified=True for basic info, False for detailed properties (otherwise it get get very very long)
       - Use get_selected() to examine currently selected components
       - Use get_objects() with GUIDs to examine specific components
       - Use context_depth parameter (0-3) to include connected components in the response

    3. Script Component Management:
       - Use update_script() to modify existing script components:
         - Only use  proper IronPython 2.7 syntax (no f-strigns)
         - Add descriptions for better documentation
         - Include user messages to explain changes or suggest next steps
         - Define or modify component parameters:
           * When changing parameters, provide ALL desired parameters (even existing ones)
           * Specify input/output type, name, and optional properties
           * Consider access type (item/list/tree) for inputs
           * Be aware that changing parameters may affect existing connections

    4. Code Execution Guidelines:
       - Always use IronPython 2.7 compatible code (no f-strings, walrus operator, etc.)
       - Include all required imports in your code
       - Use 'result = value' instead of 'return value' to return data as component output
       - You can create Grasshopper components via code
       - You can access Rhino objects by referencing them

    5. Rhino Integration:
       - Grasshopper is closely integrated with Rhino
       - Grasshopper-generated geometry appears in Rhino viewport

    6. Best Practices:
       - remember the Guid / Uuid of components you want to modify / need regular access to
       - work in small steps, break down the problem into smaller parts
       - Keep script components well-documented with clear descriptions
       - Use meaningful names for components and parameters
       - Test changes incrementally to ensure stability
       - When modifying scripts:
         * If not changing parameters, maintain existing input/output structure
         * If changing parameters, carefully plan the new parameter set
         * Document parameter changes in the user message
    """

def main():
    """Run the MCP server"""
    app.run(transport='stdio')

if __name__ == "__main__":
    main()
