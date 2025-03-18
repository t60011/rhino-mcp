"""
Rhino MCP - Rhino Model Context Protocol Integration

This script runs inside Rhino and provides a socket server to receive commands from the external MCP server.
"""

import socket
import threading
import json
import traceback
import System
import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs
import System.Drawing.Color as Color

# Configuration
HOST = 'localhost'
PORT = 9876

class RhinoMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None
    
    def start(self):
        if self.running:
            print("Server is already running")
            return
            
        self.running = True
        
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            
            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            print(f"RhinoMCP server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start server: {str(e)}")
            self.stop()
            
    def stop(self):
        self.running = False
        
        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Wait for thread to finish
        if self.server_thread:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
            except:
                pass
            self.server_thread = None
        
        print("RhinoMCP server stopped")
    
    def _server_loop(self):
        """Main server loop in a separate thread"""
        print("Server thread started")
        self.socket.settimeout(1.0)  # Timeout to allow for stopping
        
        while self.running:
            try:
                # Accept new connection
                try:
                    client, address = self.socket.accept()
                    print(f"Connected to client: {address}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    # Just check running condition
                    continue
                except Exception as e:
                    print(f"Error accepting connection: {str(e)}")
                    System.Threading.Thread.Sleep(500)
            except Exception as e:
                print(f"Error in server loop: {str(e)}")
                if not self.running:
                    break
                System.Threading.Thread.Sleep(500)
        
        print("Server thread stopped")
    
    def _handle_client(self, client):
        """Handle connected client"""
        print("Client handler started")
        client.settimeout(None)  # No timeout
        buffer = b''
        
        try:
            while self.running:
                # Receive data
                try:
                    data = client.recv(8192)
                    if not data:
                        print("Client disconnected")
                        break
                    
                    buffer += data
                    try:
                        # Try to parse command
                        command = json.loads(buffer.decode('utf-8'))
                        buffer = b''
                        
                        # Execute command in Rhino's main thread
                        def execute_wrapper():
                            try:
                                response = self.execute_command(command)
                                response_json = json.dumps(response)
                                try:
                                    client.sendall(response_json.encode('utf-8'))
                                except:
                                    print("Failed to send response - client disconnected")
                            except Exception as e:
                                print(f"Error executing command: {str(e)}")
                                traceback.print_exc()
                                try:
                                    error_response = {
                                        "status": "error",
                                        "message": str(e)
                                    }
                                    client.sendall(json.dumps(error_response).encode('utf-8'))
                                except:
                                    print("Failed to send error response - client disconnected")
                        
                        # Run in Rhino's main thread
                        Rhino.RhinoApp.InvokeOnMainThread(execute_wrapper)
                        
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        pass
                        
                except Exception as e:
                    print(f"Error receiving data: {str(e)}")
                    break
        except Exception as e:
            print(f"Error in client handler: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass
            
        print("Client handler stopped")
    
    def execute_command(self, command):
        """Execute a command received from the client"""
        try:
            command_type = command.get("type")
            params = command.get("params", {})
            
            print(f"Executing command: {command_type} with params: {params}")
            
            # Dispatch to appropriate method
            result = self._execute_command_internal(command_type, params)
            
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            print(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _execute_command_internal(self, command_type, params):
        """Internal method to execute a command based on its type"""
        # Define the command handlers
        command_handlers = {
            "get_simple_info": self.get_simple_info,
            "get_scene_info": self.get_scene_info,
            "create_cube": self.create_cube,
            "get_layers": self.get_layers,
            "execute_code": self.execute_code,
            # Add more command handlers here
        }
        
        # Get the handler for this command type
        handler = command_handlers.get(command_type)
        
        if handler:
            # Call the handler with the params
            return handler(**params)
        else:
            raise ValueError(f"Unknown command type: {command_type}")
    
    def get_simple_info(self):
        """Get simple information about the Rhino environment"""
        return {
            "rhino_version": Rhino.RhinoApp.Version,
            "file_path": sc.doc.Path,
            "units": str(sc.doc.ModelUnitSystem)
        }
    
    def get_scene_info(self):
        """Get detailed information about the current Rhino scene"""
        # Get the document
        doc = sc.doc
        
        # Collect information about objects in the scene
        objects = []
        for obj in doc.Objects:
            if obj.IsValid:
                obj_info = {
                    "id": str(obj.Id),
                    "name": obj.Name or "Unnamed",
                    "type": obj.ObjectType.ToString(),
                    "layer": doc.Layers.FindIndex(obj.Attributes.LayerIndex).Name,
                    "is_visible": obj.IsVisible
                }
                objects.append(obj_info)
        
        # Collect information about layers
        layers = []
        for layer in doc.Layers:
            if layer.IsValid:
                layer_info = {
                    "name": layer.Name,
                    "id": str(layer.Id),
                    "color": [layer.Color.R, layer.Color.G, layer.Color.B],
                    "is_visible": layer.IsVisible,
                    "is_locked": layer.IsLocked
                }
                layers.append(layer_info)
        
        # Collect information about the scene
        scene_info = {
            "rhino_version": Rhino.RhinoApp.Version,
            "file_path": doc.Path,
            "units": str(doc.ModelUnitSystem),
            "objects_count": len(objects),
            "layers_count": len(layers),
            "objects": objects,
            "layers": layers
        }
        
        return scene_info
    
    def create_cube(self, size=1.0, location=None, name=None):
        """
        Create a cube in the Rhino scene
        
        Args:
            size: The size of the cube
            location: [x, y, z] coordinates for position
            name: Optional name for the cube
        """
        if location is None:
            location = [0, 0, 0]
        
        # Create a cube
        point1 = Rhino.Geometry.Point3d(location[0], location[1], location[2])
        point2 = Rhino.Geometry.Point3d(location[0] + size, location[1] + size, location[2] + size)
        
        box = Rhino.Geometry.Box(
            Rhino.Geometry.Plane.WorldXY,
            Rhino.Geometry.Interval(location[0], location[0] + size),
            Rhino.Geometry.Interval(location[1], location[1] + size),
            Rhino.Geometry.Interval(location[2], location[2] + size)
        )
        
        # Add the cube to the document
        obj_id = sc.doc.Objects.AddBox(box)
        
        if obj_id == System.Guid.Empty:
            raise Exception("Failed to create cube")
        
        # Set the name if provided
        if name:
            sc.doc.Objects.Find(obj_id).Name = name
        
        # Update the document
        sc.doc.Views.Redraw()
        
        # Return information about the created cube
        return {
            "id": str(obj_id),
            "name": name or "Cube",
            "type": "Box",
            "size": size,
            "location": location
        }
    
    def get_layers(self):
        """Get information about all layers in the Rhino scene"""
        doc = sc.doc
        
        # Collect information about layers
        layers = []
        for layer in doc.Layers:
            if layer.IsValid:
                layer_info = {
                    "name": layer.Name,
                    "id": str(layer.Id),
                    "color": [layer.Color.R, layer.Color.G, layer.Color.B],
                    "is_visible": layer.IsVisible,
                    "is_locked": layer.IsLocked,
                    "is_current": layer.Index == doc.Layers.CurrentLayerIndex
                }
                layers.append(layer_info)
        
        return {
            "layers": layers,
            "count": len(layers),
            "current_layer": doc.Layers.CurrentLayer.Name
        }
    
    def execute_code(self, code):
        """Execute arbitrary Python code in Rhino"""
        try:
            # Create a local dictionary for variables
            local_vars = {
                "sc": sc,
                "rs": rs,
                "Rhino": Rhino,
                "doc": sc.doc
            }
            
            # Execute the code
            exec(code, globals(), local_vars)
            
            # Get the result if it's assigned to a variable named 'result'
            result = local_vars.get("result", None)
            
            # If result is None, try to get the last expression
            if result is None and "\n" in code:
                last_line = code.strip().split("\n")[-1]
                if not last_line.startswith(("if", "for", "while", "def", "class")) and "=" not in last_line:
                    # Try to evaluate the last line as an expression
                    try:
                        result = eval(last_line, globals(), local_vars)
                    except:
                        pass
            
            # Return the result
            return {
                "success": True,
                "result": str(result) if result is not None else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

# Create a global server instance
server = None

def start_server():
    """Start the RhinoMCP server"""
    global server
    if server is None:
        server = RhinoMCPServer()
        server.start()
        print("RhinoMCP server started")
    else:
        print("RhinoMCP server is already running")

def stop_server():
    """Stop the RhinoMCP server"""
    global server
    if server is not None:
        server.stop()
        server = None
        print("RhinoMCP server stopped")
    else:
        print("RhinoMCP server is not running")

# Automatically start the server when this script is loaded
start_server()
print("RhinoMCP script loaded. Server started automatically.")
print("To stop the server, run: stop_server()") 