"""
Rhino MCP - Rhino-side Script
Handles communication with external MCP server and executes Rhino commands.
"""

import socket
import threading
import json
import time
import System
import Rhino
import scriptcontext as sc
import os
import platform
import traceback
import sys

# Configuration
HOST = 'localhost'
PORT = 9876

def get_log_dir():
    """Get the appropriate log directory based on the platform"""
    home_dir = os.path.expanduser("~")
    
    # Platform-specific log directory
    if platform.system() == "Darwin":  # macOS
        log_dir = os.path.join(home_dir, "Library", "Application Support", "RhinoMCP", "logs")
    elif platform.system() == "Windows":
        log_dir = os.path.join(home_dir, "AppData", "Local", "RhinoMCP", "logs")
    else:  # Linux and others
        log_dir = os.path.join(home_dir, ".rhino_mcp", "logs")
    
    return log_dir

def log_message(message):
    """Log a message to both Rhino's command line and log file"""
    # Print to Rhino's command line
    Rhino.RhinoApp.WriteLine(message)
    
    # Log to file
    try:
        log_dir = get_log_dir()
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, "rhino_mcp.log")
        
        # Log platform info on first run
        if not os.path.exists(log_file):
            with open(log_file, "w") as f:
                f.write("=== RhinoMCP Log ===\n")
                f.write("Platform: {0}\n".format(platform.system()))
                f.write("Python Version: {0}\n".format(sys.version))
                f.write("Rhino Version: {0}\n".format(Rhino.RhinoApp.Version))
                f.write("==================\n\n")
        
        with open(log_file, "a") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write("[{0}] {1}\n".format(timestamp, message))
    except Exception as e:
        Rhino.RhinoApp.WriteLine("Failed to write to log file: {0}".format(str(e)))

class RhinoMCPServer:
    def __init__(self, host='localhost', port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.server_thread = None
    
    def start(self):
        if self.running:
            log_message("Server is already running")
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
            
            log_message("RhinoMCP server started on {0}:{1}".format(self.host, self.port))
        except Exception as e:
            log_message("Failed to start server: {0}".format(str(e)))
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
        
        log_message("RhinoMCP server stopped")
    
    def _server_loop(self):
        """Main server loop that accepts connections"""
        while self.running:
            try:
                client, addr = self.socket.accept()
                log_message("Client connected from {0}:{1}".format(addr[0], addr[1]))
                
                # Handle client in a new thread
                client_thread = threading.Thread(target=self._handle_client, args=(client,))
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    log_message("Error accepting connection: {0}".format(str(e)))
                    time.sleep(0.5)
    
    def _handle_client(self, client):
        """Handle a client connection"""
        try:
            while self.running:
                # Receive command
                data = client.recv(8192)
                if not data:
                    log_message("Client disconnected")
                    break
                    
                try:
                    command = json.loads(data.decode('utf-8'))
                    log_message("Received command: {0}".format(command))
                    
                    # Create a closure to capture the client connection
                    def execute_wrapper():
                        try:
                            response = self.execute_command(command)
                            response_json = json.dumps(response)
                            client.sendall(response_json.encode('utf-8'))
                            log_message("Response sent successfully")
                        except Exception as e:
                            log_message("Error executing command: {0}".format(str(e)))
                            traceback.print_exc()
                            error_response = {
                                "status": "error",
                                "message": str(e)
                            }
                            try:
                                client.sendall(json.dumps(error_response).encode('utf-8'))
                            except Exception as e:
                                log_message("Failed to send error response: {0}".format(str(e)))
                                return False  # Signal connection should be closed
                        return True  # Signal connection should stay open
                    
                    # Use RhinoApp.Idle event for IronPython 2.7 compatibility
                    def idle_handler(sender, e):
                        if not execute_wrapper():
                            # If execute_wrapper returns False, close the connection
                            try:
                                client.close()
                            except:
                                pass
                        # Remove the handler after execution
                        Rhino.RhinoApp.Idle -= idle_handler
                    
                    Rhino.RhinoApp.Idle += idle_handler
                    
                except ValueError as e:
                    # Handle JSON decode error (IronPython 2.7)
                    log_message("Invalid JSON received: {0}".format(str(e)))
                    error_response = {
                        "status": "error",
                        "message": "Invalid JSON format"
                    }
                    try:
                        client.sendall(json.dumps(error_response).encode('utf-8'))
                    except:
                        break  # Close connection on send error
                
        except Exception as e:
            log_message("Error handling client: {0}".format(str(e)))
            traceback.print_exc()
        finally:
            try:
                client.close()
            except:
                pass
    
    def execute_command(self, command):
        """Execute a command received from the client"""
        try:
            command_type = command.get("type")
            params = command.get("params", {})
            
            if command_type == "get_scene_info":
                return self._get_scene_info()
            elif command_type == "create_cube":
                return self._create_cube(params)
            elif command_type == "get_layers":
                return self._get_layers()
            elif command_type == "execute_code":
                return self._execute_code(params)
            else:
                return {"status": "error", "message": "Unknown command type"}
                
        except Exception as e:
            log_message("Error executing command: {0}".format(str(e)))
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    def _get_scene_info(self):
        """Get information about the current scene"""
        try:
            doc = sc.doc
            objects = []
            
            for obj in doc.Objects:
                objects.append({
                    "id": str(obj.Id),
                    "name": obj.Name,
                    "type": obj.Geometry.GetType().Name,
                    "layer": obj.Attributes.LayerIndex
                })
            
            return {
                "status": "success",
                "objects": objects,
                "layer_count": doc.Layers.Count
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _create_cube(self, params):
        """Create a cube in the scene"""
        try:
            size = float(params.get("size", 1.0))
            location = params.get("location", [0, 0, 0])
            name = params.get("name", "Cube")
            
            # Create cube using RhinoCommon
            box = Rhino.Geometry.Box(
                Rhino.Geometry.Plane.WorldXY,
                Rhino.Geometry.Interval(0, size),
                Rhino.Geometry.Interval(0, size),
                Rhino.Geometry.Interval(0, size)
            )
            
            # Move to specified location
            transform = Rhino.Geometry.Transform.Translation(
                location[0] - box.Center.X,
                location[1] - box.Center.Y,
                location[2] - box.Center.Z
            )
            box.Transform(transform)
            
            # Add to document
            id = sc.doc.Objects.AddBox(box)
            if id != System.Guid.Empty:
                obj = sc.doc.Objects.Find(id)
                if obj:
                    obj.Name = name
                    sc.doc.Views.Redraw()
                    return {
                        "status": "success",
                        "message": "Created cube with size {0}".format(size),
                        "id": str(id)
                    }
            
            return {"status": "error", "message": "Failed to create cube"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _get_layers(self):
        """Get information about all layers"""
        try:
            doc = sc.doc
            layers = []
            
            for layer in doc.Layers:
                layers.append({
                    "id": layer.Index,
                    "name": layer.Name,
                    "object_count": layer.ObjectCount,
                    "is_visible": layer.IsVisible,
                    "is_locked": layer.IsLocked
                })
            
            return {
                "status": "success",
                "layers": layers
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _execute_code(self, params):
        """Execute arbitrary Python code"""
        try:
            code = params.get("code", "")
            if not code:
                return {"status": "error", "message": "No code provided"}
            
            # Create a new scope for code execution
            local_dict = {}
            exec(code, globals(), local_dict)
            
            return {
                "status": "success",
                "result": str(local_dict.get("result", "Code executed successfully"))
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Create and start server
server = RhinoMCPServer(HOST, PORT)
server.start()

# Add commands to Rhino
def start_server():
    """Start the RhinoMCP server"""
    server.start()

def stop_server():
    """Stop the RhinoMCP server"""
    server.stop()

# Automatically start the server when this script is loaded
start_server()
log_message("RhinoMCP script loaded. Server started automatically.")
log_message("To stop the server, run: stop_server()") 