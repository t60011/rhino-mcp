# RhinoMCP Quick Start Guide

This quick start guide will help you get up and running with RhinoMCP as quickly as possible.

## Step 1: Run the Rhino-side Script

1. Open Rhino
2. Open the Python script editor (Tools > PythonScript > Edit...)
3. Open the `rhino_script.py` file
4. Run the script

You should see output similar to:
```
RhinoMCP server started on localhost:9876
RhinoMCP script loaded. Server started automatically.
```

## Step 2: Run the MCP Server

Open a command prompt or terminal and run:
```
rhino-mcp
```

You should see output similar to:
```
INFO: Starting Rhino MCP server on localhost:8080
INFO: Connect to Rhino at localhost:9876
```

## Step 3: Try the Available MCP Tools in Claude

Once connected, you can use the following tools in Claude:

### Get Scene Information
```
get_scene_info()
```
This returns detailed information about the current Rhino scene, including objects and layers.

### Create a Cube
```
create_cube(size=2.0, location=[1, 1, 0], name="MyCube")
```
This creates a cube with the specified size, location, and name.

### Get Layer Information
```
get_layers()
```
This returns information about all layers in the Rhino document.

### Execute Custom Rhino Code
```
execute_rhino_code("""
import rhinoscriptsyntax as rs
# Create a sphere
center = [0, 0, 0]
radius = 5
sphere_id = rs.AddSphere(center, radius)
rs.ObjectName(sphere_id, "MySphere")
result = "Sphere created with ID: " + str(sphere_id)
""")
```
This executes custom Python code in the Rhino environment and returns the result.

## Example Session

Here's an example of a conversation with Claude:

**User:** Create a cube in Rhino and get all layer names.

**Claude:**
```
I'll help you create a cube in Rhino and get all layer names.

First, let me create a cube:
create_cube(size=2.0, location=[0, 0, 0], name="ClaudeCube")

Now, let me get all the layer names:
get_layers()
```

## Next Steps

Once you're comfortable with the basic operations, you can:

1. Extend the Rhino-side script with more functions
2. Add more MCP tools to the server
3. Create more complex workflows combining multiple tools 