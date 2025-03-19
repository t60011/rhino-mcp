"""
Rhino MCP - Minimal Test Script
Basic socket server with logging for testing connection.
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
    """Log a message to both Rhino's command line and a file"""
    # Print to Rhino's command line
    Rhino.RhinoApp.WriteLine(message)
    
    # Try to write to a log file
    try:
        log_dir = get_log_dir()
        
        # Create log directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_path = os.path.join(log_dir, "rhino_mcp_test.log")
        with open(log_path, "a") as f:
            f.write("{0}: {1}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), message))
            
        # Log platform info on first run
        if not os.path.exists(log_path) or os.path.getsize(log_path) == 0:
            f.write("Platform: {0}\n".format(platform.platform()))
            f.write("Python Version: {0}\n".format(platform.python_version()))
            f.write("Rhino Version: {0}\n".format(Rhino.RhinoApp.Version))
            f.write("-" * 50 + "\n")
            
    except Exception as e:
        Rhino.RhinoApp.WriteLine("Failed to write to log file: {0}".format(str(e)))

class TestServer:
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
            
            log_message("Test server started on {0}:{1}".format(self.host, self.port))
        except Exception as e:
            log_message("Failed to start server: {0}".format(str(e)))
            self.stop()
    
    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        log_message("Test server stopped")
    
    def _server_loop(self):
        """Main server loop in a separate thread"""
        log_message("Server thread started")
        self.socket.settimeout(1.0)
        
        while self.running:
            try:
                try:
                    client, address = self.socket.accept()
                    log_message("Connected to client: {0}".format(address))
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    log_message("Error accepting connection: {0}".format(str(e)))
                    time.sleep(0.5)
            except Exception as e:
                log_message("Error in server loop: {0}".format(str(e)))
                if not self.running:
                    break
                time.sleep(0.5)
        
        log_message("Server thread stopped")
    
    def _handle_client(self, client):
        """Handle connected client"""
        log_message("Client handler started")
        client.settimeout(None)
        buffer = b''
        
        try:
            while self.running:
                try:
                    data = client.recv(8192)
                    if not data:
                        log_message("Client disconnected")
                        break
                    
                    buffer += data
                    try:
                        # Try to parse command
                        command = json.loads(buffer.decode('utf-8'))
                        buffer = b''
                        
                        # Simple echo response
                        response = {
                            "status": "success",
                            "message": "Received command: {0}".format(command.get("type", "unknown")),
                            "params": command.get("params", {})
                        }
                        
                        # Send response
                        client.sendall(json.dumps(response).encode('utf-8'))
                        
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        pass
                        
                except Exception as e:
                    log_message("Error receiving data: {0}".format(str(e)))
                    break
        except Exception as e:
            log_message("Error in client handler: {0}".format(str(e)))
        finally:
            try:
                client.close()
            except:
                pass
            
        log_message("Client handler stopped")

# Create a global server instance
server = None

def start_server():
    """Start the test server"""
    global server
    if server is None:
        server = TestServer()
        server.start()
        log_message("Test server started")
    else:
        log_message("Test server is already running")

def stop_server():
    """Stop the test server"""
    global server
    if server is not None:
        server.stop()
        server = None
        log_message("Test server stopped")
    else:
        log_message("Test server is not running")

# Start the server when this script is loaded
start_server()
log_message("Test script loaded. Server started automatically.")
log_message("To stop the server, run: stop_server()") 