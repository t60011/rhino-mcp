# RhinoMCP Installation Guide

This guide will help you set up and run RhinoMCP to connect Claude AI to Rhino.

## Step 1: Install Dependencies

Make sure you have:
- Rhino 7 or newer
- Python 3.8 or newer
- MCP dependencies

```bash
# Install MCP dependencies
pip install mcp-python fastmcp
```

## Step 2: Install RhinoMCP

```bash
# Clone the repository
git clone https://github.com/yourusername/rhino-mcp.git
cd rhino-mcp

# Install the package in development mode
pip install -e .
```

## Step 3: Set Up Rhino

1. Open Rhino
2. Run the Python script editor (Tools > PythonScript > Edit...)
3. Load the `rhino_script.py` file
4. Run the script

You should see a message indicating that the RhinoMCP server has started.

## Step 4: Run the MCP Server

Open a terminal and run:

```bash
rhino-mcp
```

Or, if that doesn't work:

```bash
python -m rhino_mcp.server
```

You should see log messages indicating that the server has started and is trying to connect to Rhino.

## Step 5: Configure Claude

### For Claude Desktop

For integration with Claude Desktop, edit your `claude_desktop_config.json` file (located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
    "mcpServers": {
        "rhino": {
            "command": "/path/to/your/conda/environment/bin/python",
            "args": [
                "-m", "rhino_mcp.server"
            ]
        }
    }
}
```

**Important:** If you're using a conda environment (recommended), you need to:
1. Replace `/path/to/your/conda/environment` with the actual path to your conda environment
   - Example: `/Users/username/miniconda3/envs/rhino_mcp`
2. Make sure your conda environment is properly set up with all dependencies
3. Restart Claude Desktop after saving the configuration

**Troubleshooting:**
- If you get "No solution found when resolving tool dependencies" errors, make sure you're using the full Python path
- The `uvx` command approach might not work reliably with conda environments
- You can check your conda environment path with `conda info --envs`

### For Cursor

In Cursor Settings > MCP, add a new command:

```
rhino-mcp
```

## Step 6: Testing the Connection

In Claude, you can now use the RhinoMCP tools:

```
get_scene_info()
create_cube(size=2.0, location=[0, 0, 0], name="TestCube")
get_layers()
```

## Troubleshooting

- **Connection errors**: Make sure Rhino is running and the `rhino_script.py` has been executed
- **Missing dependencies**: Check that all required packages are installed
- **Port conflicts**: If there's a port conflict, you can change the port in both the Rhino script and the MCP server by setting environment variables:
  ```
  export RHINO_MCP_PORT=9877
  ```

## Next Steps

Once you have the basic connection working, you can extend the functionality by:

1. Adding new command handlers in the `RhinoMCPServer` class in `rhino_script.py`
2. Adding corresponding MCP tools in `server.py` 