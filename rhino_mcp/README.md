# RhinoMCP - Rhino Model Context Protocol Integration

RhinoMCP connects Rhino to Claude AI through the Model Context Protocol (MCP), allowing Claude to directly interact with and control Rhino. This integration enables prompt-assisted 3D modeling, scene creation, and manipulation.

## Features

- **Two-way communication**: Connect Claude AI to Rhino through a socket-based server
- **Object manipulation**: Create and modify 3D objects in Rhino
- **Layer management**: View and interact with Rhino layers
- **Scene inspection**: Get detailed information about the current Rhino scene
- **Code execution**: Run arbitrary Python code in Rhino from Claude

## Components

The system consists of two main components:

1. **Rhino-side Script (`rhino_script.py`)**: A Python script that runs inside Rhino to create a socket server that receives and executes commands
2. **MCP Server (`rhino_mcp/server.py`)**: A Python server that implements the Model Context Protocol and connects to the Rhino script

## Installation

### Prerequisites

- Rhino 7 or newer
- Python 3.10 or newer
- Conda (for environment management)

### Setting up the Python Environment

1. Create a new conda environment with Python 3.10:
   ```bash
   conda create -n rhino_mcp python=3.10
   conda activate rhino_mcp
   ```

2. Install the `uv` package manager:
   ```bash
   pip install uv
   ```

3. Install the package in development mode:
   ```bash
   cd rhino_mcp  # Navigate to the package directory
   uv pip install -e .
   ```

### Installing the Rhino-side Script

1. Open Rhino 7
2. Open the Python Editor:
   - Click on the "Tools" menu
   - Select "Python Editor" (or press Ctrl+Alt+P / Cmd+Alt+P)
3. In the Python Editor:
   - Click "File" > "Open"
   - Navigate to and select `rhino_script.py`
   - Click "Run" (or press F5)
4. The script will start automatically and you should see these messages in the Python Editor:
   ```
   RhinoMCP script loaded. Server started automatically.
   To stop the server, run: stop_server()
   ```

### Running the MCP Server

The MCP server will be started automatically by Claude Desktop using the configuration in `claude_desktop_config.json`. You don't need to start it manually.

### Starting the Connection

1. First, start the Rhino script:
   - Open Rhino 7
   - Open the Python Editor
   - Open and run `rhino_script.py`
   - Verify you see the startup messages in the Python Editor

2. Then start Claude Desktop:
   - It will automatically start the MCP server when needed
   - The connection between Claude and Rhino will be established automatically

### Managing the Connection

- To stop the Rhino script server:
  - In the Python Editor, type `stop_server()` and press Enter
  - You should see "RhinoMCP server stopped" in the output

- To restart the Rhino script server:
  - In the Python Editor, type `start_server()` and press Enter
  - You should see "RhinoMCP server started on localhost:9876" in the output

### Claude Integration

To integrate with Claude Desktop:

1. Go to Claude Desktop > Settings > Developer > Edit Config 
2. Open the `claude_desktop_config.json` file and add the following configuration:

```json
{
    "mcpServers": {
        "rhino": {
            "command": "/Users/Joo/miniconda3/envs/rhino_mcp/bin/python",
            "args": [
                "-m", "rhino_mcp.server"
            ]
        }
    }
}
```

Make sure to:
- Replace the Python path with the path to Python in your conda environment
- Save the file and restart Claude Desktop

> **Important Note:** If you're using a conda environment, you must specify the full path to the Python interpreter as shown above. Using the `uvx` command might not work properly with conda environments.

## Usage

### Starting the Connection

1. Open Rhino
2. Run the Python script editor
3. Open and run the `rhino_script.py` file to start the Rhino socket server
4. Open Claude Desktop - it will automatically start the MCP server when needed

### Using with Claude

Once connected, you can use the following MCP tools from Claude:

- `get_scene_info()`: Get detailed information about the current Rhino scene
- `create_cube(size=1.0, location=[0,0,0], name="Cube")`: Create a cube in the Rhino scene
- `get_layers()`: Get information about all layers in the Rhino scene
- `execute_rhino_code(code)`: Run arbitrary Python code in Rhino

### Example Commands

Here are some examples of what you can ask Claude to do:

- "Get information about the current Rhino scene"
- "Create a cube at the origin"
- "Get all layers in the Rhino document"
- "Execute this Python code in Rhino: ..."

## Troubleshooting

- **Connection issues**: 
  - Make sure the Rhino script is running (check Python Editor output)
  - Verify port 9876 is not in use by another application
  - Check that both Rhino and Claude Desktop are running

- **Script not starting**:
  - Make sure you're using Rhino 7 or newer
  - Check the Python Editor for any error messages
  - Try closing and reopening the Python Editor

- **Package not found**: 
  - Ensure you're in the correct directory and have installed the package in development mode
  - Verify your conda environment is activated

- **Python path issues**: 
  - Verify that the Python path in `claude_desktop_config.json` matches your conda environment's Python path
  - Make sure you're using the full path to the Python interpreter

- **Timeout errors**: 
  - Try simplifying your requests or breaking them into smaller steps
  - Check if the Rhino script is still running (try `start_server()` again)

## Limitations

- The `execute_rhino_code` tool allows running arbitrary Python code in Rhino, which can be powerful but potentially dangerous. Use with caution.
- This is a minimal implementation focused on basic functionality. Advanced features may require additional development.

## Extending

To add new functionality, you need to:

1. Add new command handlers in the `RhinoMCPServer` class in `rhino_script.py`
2. Add corresponding MCP tools in `server.py`

## License

This project is open source and available under the MIT License. 