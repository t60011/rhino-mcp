"""Rhino integration through the Model Context Protocol."""
from mcp.server.fastmcp import FastMCP, Context
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List, Optional
import json
import socket
import time

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RhinoMCPServer")

class RhinoConnection:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.socket = None
        self.timeout = 30.0  # 30 second timeout
        self.buffer_size = 65536  # 64KB buffer size
    
    def connect(self):
        """Connect to the Rhino script's socket server"""
        if self.socket is None:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self.timeout)
                self.socket.connect((self.host, self.port))
                logger.info("Connected to Rhino script")
            except Exception as e:
                logger.error("Failed to connect to Rhino script: {0}".format(str(e)))
                self.disconnect()
                raise
    
    def disconnect(self):
        """Disconnect from the Rhino script"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a command to the Rhino script and wait for response"""
        if self.socket is None:
            self.connect()
        
        try:
            # Prepare command
            command = {
                "type": command_type,
                "params": params or {}
            }
            
            # Send command
            command_json = json.dumps(command)
            logger.debug("Sending command: {0}".format(command_json))
            self.socket.sendall(command_json.encode('utf-8'))
            
            # Receive response with timeout and larger buffer
            buffer = b''
            start_time = time.time()
            
            while True:
                try:
                    # Check timeout
                    if time.time() - start_time > self.timeout:
                        raise Exception("Response timeout after {0} seconds".format(self.timeout))
                    
                    # Receive data
                    data = self.socket.recv(self.buffer_size)
                    if not data:
                        break
                        
                    buffer += data
                    
                    # Try to parse JSON
                    try:
                        response = json.loads(buffer.decode('utf-8'))
                        logger.debug("Received response: {0}".format(response))
                        
                        # Check for error response
                        if response.get("status") == "error":
                            raise Exception(response.get("message", "Unknown error from Rhino"))
                            
                        return response
                    except json.JSONDecodeError:
                        # If we have a complete response, it should be valid JSON
                        if len(buffer) > 0:
                            continue
                        else:
                            raise Exception("Invalid JSON response from Rhino")
                            
                except socket.timeout:
                    raise Exception("Socket timeout while receiving response")
                    
            raise Exception("Connection closed by Rhino script")
            
        except Exception as e:
            logger.error("Error communicating with Rhino script: {0}".format(str(e)))
            self.disconnect()  # Disconnect on error to force reconnection
            raise

# Global connection instance
rhino_connection = None

def get_rhino_connection() -> RhinoConnection:
    """Get or create the Rhino connection"""
    global rhino_connection
    if rhino_connection is None:
        rhino_connection = RhinoConnection()
    return rhino_connection

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage server startup and shutdown lifecycle"""
    try:
        logger.info("RhinoMCP server starting up")
        # Try to connect to Rhino script
        try:
            get_rhino_connection().connect()
        except Exception as e:
            logger.warning("Could not connect to Rhino script: {0}".format(str(e)))
        yield {}
    finally:
        logger.info("RhinoMCP server shut down")
        # Clean up connection
        if rhino_connection:
            rhino_connection.disconnect()

# Create the MCP server with lifespan support
app = FastMCP(
    "RhinoMCP",
    description="Rhino integration through the Model Context Protocol",
    lifespan=server_lifespan
)

@app.tool()
def get_scene_info(ctx: Context) -> str:
    """Get basic information about the current Rhino scene.
    
    This is a lightweight function that returns basic scene information:
    - List of all objects with their IDs, names, types, and layers
    - No metadata or detailed properties
    - Use this for quick scene overview or when you only need basic object information
    
    Returns:
        JSON string containing basic scene information
    """
    try:
        connection = get_rhino_connection()
        result = connection.send_command("get_scene_info")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Error getting scene info from Rhino: {0}".format(str(e)))
        return "Error getting scene info: {0}".format(str(e))

@app.tool()
def create_cube(ctx: Context, size: float = 1.0, location: List[float] = None, name: str = None) -> str:
    """Create a cube in Rhino"""
    try:
        connection = get_rhino_connection()
        result = connection.send_command("create_cube", {
            "size": size,
            "location": location or [0, 0, 0],
            "name": name
        })
        
        # Check if we got an error response
        if result.get("status") == "error":
            raise Exception(result.get("message", "Unknown error"))
            
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Error creating cube in Rhino: {0}".format(str(e)))
        return "Error creating cube: {0}".format(str(e))

@app.tool()
def get_layers(ctx: Context) -> str:
    """Get list of layers in Rhino"""
    try:
        connection = get_rhino_connection()
        result = connection.send_command("get_layers")
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Error getting layers from Rhino: {0}".format(str(e)))
        return "Error getting layers: {0}".format(str(e))

@app.tool()
def get_objects_with_metadata(ctx: Context, filters: Optional[Dict[str, Any]] = None, metadata_fields: Optional[List[str]] = None) -> str:
    """Get detailed information about objects in the scene with their metadata.
    
    This is a CORE FUNCTION for scene context awareness. It provides:
    1. Full metadata for each object we created via this mcp connection including:
       - short_id (DDHHMMSS format), can be dispalyed in the viewport using capture_viewport
       - created_at timestamp
       - layer information
       - object type
       - bounding box
       - name
       - description
       - user_text data
    
    2. Advanced filtering capabilities:
       - layer: Filter by layer name (supports wildcards, e.g., "Layer*")
       - name: Filter by object name (supports wildcards, e.g., "Cube*")
       - short_id: Filter by exact short ID match
    
    3. Field selection:
       - Can specify which metadata fields to return
       - Useful for reducing response size when only certain fields are needed
    
    Args:
        filters: Optional dictionary of filters to apply
        metadata_fields: Optional list of specific metadata fields to return
    
    Returns:
        JSON string containing filtered objects with their metadata
    """
    try:
        connection = get_rhino_connection()
        result = connection.send_command("get_objects_with_metadata", {
            "filters": filters or {},
            "metadata_fields": metadata_fields
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Error getting objects with metadata: {0}".format(str(e)))
        return "Error getting objects with metadata: {0}".format(str(e))

@app.tool()
def capture_viewport(ctx: Context, layer: Optional[str] = None, show_annotations: bool = True, max_size: int = 800) -> str:
    """Capture the current viewport as an image 
    
    Args:
        layer: Optional layer name to filter annotations
        show_annotations: Whether to show object annotations, this will display the short_id of the object in the viewport and helps you to select specific objects.
    """
    try:
        connection = get_rhino_connection()
        result = connection.send_command("capture_viewport", {
            "layer": layer,
            "show_annotations": show_annotations,
            "max_size": max_size
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Error capturing viewport: {0}".format(str(e)))
        return "Error capturing viewport: {0}".format(str(e))

@app.tool()
def add_object_metadata(ctx: Context, object_id: str, name: Optional[str] = None, description: Optional[str] = None) -> str:
    """Add metadata to a Rhino object"""
    try:
        connection = get_rhino_connection()
        result = connection.send_command("add_metadata", {
            "object_id": object_id,
            "name": name,
            "description": description
        })
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Error adding object metadata: {0}".format(str(e)))
        return "Error adding object metadata: {0}".format(str(e))

@app.tool()
def execute_rhino_code(ctx: Context, code: str) -> str:
    """Execute arbitrary Python code in Rhino.
    
    IMPORTANT NOTES FOR CODE EXECUTION:
    1. This is Rhino 7 with IronPython 2.7 - no f-strings or modern Python features
    2. Always use .format() for string formatting
    3. When creating objects, ALWAYS call add_object_metadata() after creation
    4. For user interaction, you can use RhinoCommon syntax (rs.GetObject, rs.GetPoint, etc.)
       but prefer automated solutions unless user interaction is specifically requested
    
    The add_object_metadata() function is provided in the code context and must be called
    after creating any object. It adds standardized metadata including:
    - short_id (DDHHMMSS format)
    - created_at (timestamp of creation)
    - layer (layer information)
    - type (object type)
    - bbox (bounding box coordinates)
    - name (provided by you)
    - description (provided by you)

    Common Syntax Errors to Avoid:
    1. No f-strings: Use .format() instead
       Bad: f"Value: {value}"
       Good: "Value: {0}".format(value)
    
    2. No walrus operator (:=)
    
    3. No type hints
    
    4. No modern Python features (match/case, etc.)
    
    5. No list/dict comprehensions with multiple for clauses
    
    6. No assignment expressions in if/while conditions

    Example of proper object creation:
    <<<python
    # Create geometry
    cube_id = rs.AddBox(rs.WorldXYPlane(), 5, 5, 5)
    
    # Add metadata - ALWAYS do this after creating an object
    add_object_metadata(cube_id, "My Cube", "A test cube created via MCP")
    
    # You can ask users for input (use sparingly) for using rhino common syntax for example:
    selected_objects = rs.GetObjects("Please select some objects")
    point = rs.GetPoint("Please pick a point")
    >>>
    """
    try:
        connection = get_rhino_connection()
        result = connection.send_command("execute_code", {"code": code})
        
        # Format the response with debug information
        if result.get("status") == "error":
            error_type = result.get("type", "unknown")
            if error_type == "syntax_error":
                return "Syntax Error: {0}\nLine {1}, Offset {2}\n{3}".format(
                    result.get("details", result.get("message", "Unknown syntax error")),
                    result.get("line", "unknown"),
                    result.get("offset", "unknown"),
                    result.get("text", "")
                )
            elif error_type == "runtime_error":
                return "Runtime Error: {0}\nTraceback:\n{1}".format(
                    result.get("details", result.get("message", "Unknown runtime error")),
                    result.get("traceback", "")
                )
            else:
                return "Error: {0}".format(result.get("details", result.get("message", "Unknown error")))
        else:
            # Include debug messages in the response
            debug_messages = result.get("debug_messages", [])
            if debug_messages:
                return "Debug Messages:\n{0}\n\nResult: {1}".format(
                    "\n".join(debug_messages),
                    result.get("result", "Code executed successfully")
                )
            return result.get("result", "Code executed successfully")
            
    except Exception as e:
        logger.error("Error executing code in Rhino: {0}".format(str(e)))
        return "Error executing code: {0}".format(str(e))

@app.prompt()
def rhino_creation_strategy() -> str:
    """Defines the preferred strategy for creating and managing objects in Rhino"""
    return """When working with Rhino through MCP, follow these guidelines:

    1. Scene Context Awareness:
       - Always start by checking the scene using get_scene_info() for basic overview
       - use the capture_viewport to get an image from viewport to get a quick overview of the scene
       - Use get_objects_with_metadata() for detailed object information and filtering
       - The short_id in metadata can be displayed in viewport using capture_viewport()

    2. Object Creation and Management:
       - When creating objects, ALWAYS call add_object_metadata() after creation (The add_object_metadata() function is provided in the code context)   
       - Use meaningful names for objects to help with you with later identification
       - searcha nd select objects, Check object properties using get_objects_with_metadata() after creation/modification

    3. Viewport and Visualization:
       - Use capture_viewport() to get visual feedback
       - Enable annotations (show_annotations=True) to display short_ids
       - Images are automatically resized to 800px max dimension for efficiency

    4. Code Execution:
       - This is Rhino 7 with IronPython 2.7 - no f-strings or modern Python features etc
       - Prefer automated solutions over user interaction, unless  its requested or it makes sense
       - When user interaction is needed, use RhinoCommon syntax (rs.GetObject, rs.GetPoint) and prompt the user what to do 

    5. Error Handling:
       - Always check response status for errors
       - If an operation fails, try to get more information about the scene state

    6. Best Practices:
       - Keep objects organized in appropriate layers
       - Use meaningful names and descriptions
       - Use viewport captures to verify visual results
    """

def main():
    """Run the MCP server"""
    app.run(transport='stdio')

if __name__ == "__main__":
    main()