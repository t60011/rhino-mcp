"""Rhino integration through the Model Context Protocol."""
from mcp.server.fastmcp import FastMCP, Context
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
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
    
    def connect(self):
        """Connect to the Rhino script's socket server"""
        if self.socket is None:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                logger.info("Connected to Rhino script")
            except Exception as e:
                logger.error("Failed to connect to Rhino script: {0}".format(str(e)))
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
            
            # Receive response
            buffer = b''
            while True:
                data = self.socket.recv(8192)
                if not data:
                    break
                buffer += data
                try:
                    response = json.loads(buffer.decode('utf-8'))
                    logger.debug("Received response: {0}".format(response))
                    
                    # Check for error response
                    if response.get("status") == "error":
                        raise Exception(response.get("message", "Unknown error from Rhino"))
                        
                    return response
                except json.JSONDecodeError:
                    continue
            
            raise Exception("Connection closed by Rhino script")
            
        except Exception as e:
            logger.error("Error communicating with Rhino script: {0}".format(str(e)))
            self.disconnect()
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
    """Get information about the current Rhino scene"""
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
def execute_rhino_code(ctx: Context, code: str) -> str:
    """Execute arbitrary Python code in Rhino"""
    try:
        connection = get_rhino_connection()
        result = connection.send_command("execute_code", {"code": code})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error("Error executing code in Rhino: {0}".format(str(e)))
        return "Error executing code: {0}".format(str(e))

def main():
    """Run the MCP server"""
    app.run(transport='stdio')

if __name__ == "__main__":
    main()