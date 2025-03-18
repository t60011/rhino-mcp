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

1. Open Rhino
2. Run the Python script editor
3. Open and run the `rhino_script.py` file

### Running the MCP Server

The MCP server will be started automatically by Claude Desktop using the configuration in `claude_desktop_config.json`. You don't need to start it manually.

### Starting the Connection

1. Open Rhino
2. Run the Python script editor
3. Open and run the `rhino_script.py` file to start the Rhino socket server
4. Open Claude Desktop - it will automatically start the MCP server when needed

### Claude Integration

Configure Claude Desktop by adding the following to your `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "rhino": {
            "command": "uvx",
            "args": ["rhino-mcp"]
        }
    }
}
```

Make sure you:
1. Have activated the conda environment: `conda activate rhino_mcp`
2. Are in the project directory where you installed the package
3. Have installed the package in development mode: `uv pip install -e .`

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

- **Connection issues**: Make sure the Rhino script is running before starting the MCP server
- **Package not found**: Ensure you're in the correct directory and have installed the package in development mode
- **Python path issues**: Verify that the Python path in `claude_desktop_config.json` matches your conda environment's Python path
- **Timeout errors**: Try simplifying your requests or breaking them into smaller steps

## Limitations

- The `execute_rhino_code` tool allows running arbitrary Python code in Rhino, which can be powerful but potentially dangerous. Use with caution.
- This is a minimal implementation focused on basic functionality. Advanced features may require additional development.

## Extending

To add new functionality, you need to:

1. Add new command handlers in the `RhinoMCPServer` class in `rhino_script.py`
2. Add corresponding MCP tools in `server.py`

## License

This project is open source and available under the MIT License. 