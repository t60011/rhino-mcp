import rhinoscriptsyntax as rs
import scriptcontext as sc
import System.Guid
import time
import datetime
import base64
import json
from System.Drawing import Bitmap
from System.Drawing.Imaging import ImageFormat
from System.IO import MemoryStream

ANNOTATION_LAYER = "MCP_Annotations"

# Add this constant at the top of the file with other constants
VALID_METADATA_FIELDS = {
    # Required fields (always returned)
    'required': ['id', 'name', 'type', 'layer'],
    
    # Optional metadata fields
    'optional': [
        'short_id',      # Short identifier (DDHHMMSS format)
        'created_at',    # Timestamp of creation
        'bbox',          # Bounding box coordinates
        'description',   # Object description
        'user_text'      # All user text key-value pairs
    ]
}

#--------------------------------------
# Main Function Implementations
#--------------------------------------

def capture_viewport(layer_name=None, show_annotations=True):
    """Capture viewport with optional annotations and layer filtering"""
    try:
        original_layer = rs.CurrentLayer()
        temp_dots = []

        if show_annotations:
            # Ensure annotation layer exists and is current
            ensure_annotation_layer()
            rs.CurrentLayer(ANNOTATION_LAYER)
            
            # Create temporary text dots for each object
            for obj in sc.doc.Objects:
                # Skip if layer filter is active and object is not on specified layer
                if layer_name and rs.ObjectLayer(obj.Id) != layer_name:
                    continue
                    
                bbox = rs.BoundingBox(obj)
                if bbox:
                    pt = bbox[1]  # Use top corner of bounding box
                    
                    # Get or create short ID
                    short_id = rs.GetUserText(obj.Id, "short_id")
                    if not short_id:
                        short_id = generate_short_id()
                        rs.SetUserText(obj.Id, "short_id", short_id)
                    
                    # Build minimal text string
                    name = rs.ObjectName(obj) or "Unnamed"
                    text = "{0}\n{1}".format(name, short_id)
                    
                    # Create smaller text dot and store its ID
                    dot_id = rs.AddTextDot(text, pt)
                    rs.TextDotHeight(dot_id, 8)
                    temp_dots.append(dot_id)
        
        try:
            # Get the active view
            view = sc.doc.Views.ActiveView
            
            # Create a memory stream to hold the image
            memory_stream = MemoryStream()
            
            # Capture the view to a bitmap
            bitmap = view.CaptureToBitmap()
            
            # Save the bitmap to our memory stream as PNG
            bitmap.Save(memory_stream, ImageFormat.Png)
            
            # Get the bytes from memory stream and convert to base64
            bytes_array = memory_stream.ToArray()
            # Convert System.Array[Byte] to Python bytes and then to base64
            image_data = base64.b64encode(bytes(bytearray(bytes_array))).decode('utf-8')
            
            # Clean up
            bitmap.Dispose()
            memory_stream.Dispose()
                
        finally:
            # Clean up - remove the temporary text dots
            if temp_dots:
                rs.DeleteObjects(temp_dots)
                print("Removed {0} temporary annotations".format(len(temp_dots)))
            
            # Restore original layer
            rs.CurrentLayer(original_layer)
        
        # Return in Claude Vision API format
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_data
            }
        }
            
    except Exception as e:
        print("Error: {0}".format(str(e)))
        # Ensure we restore the original layer even if there's an error
        if 'original_layer' in locals():
            rs.CurrentLayer(original_layer)
        return {
            "type": "text",
            "text": "Error capturing viewport: {0}".format(str(e))
        }

def add_object_metadata(obj_id, name=None, description=None):
    """Add standardized metadata to an object"""
    try:
        import json
        import time
        from datetime import datetime
        
        # Generate short ID
        short_id = datetime.now().strftime("%d%H%M%S")
        
        # Get bounding box
        bbox = rs.BoundingBox(obj_id)
        bbox_data = [[p.X, p.Y, p.Z] for p in bbox] if bbox else []
        
        # Get object type
        obj = sc.doc.Objects.Find(obj_id)
        obj_type = obj.Geometry.GetType().Name if obj else "Unknown"
        
        # Standard metadata
        metadata = {
            "short_id": short_id,
            "created_at": time.time(),
            "layer": rs.ObjectLayer(obj_id),
            "type": obj_type,
            "bbox": bbox_data
        }
        
        # User-provided metadata
        if name:
            rs.ObjectName(obj_id, name)
            metadata["name"] = name
        else:
            # Auto-generate name if none provided
            auto_name = "{0}_{1}".format(obj_type, short_id)
            rs.ObjectName(obj_id, auto_name)
            metadata["name"] = auto_name
            
        if description:
            metadata["description"] = description
            
        # Store metadata as user text (convert bbox to string for storage)
        user_text_data = metadata.copy()
        user_text_data["bbox"] = json.dumps(bbox_data)
        
        # Add all metadata as user text
        for key, value in user_text_data.items():
            rs.SetUserText(obj_id, key, str(value))
            
        return {
            "status": "success", 
            "id": str(obj_id),
            "metadata": metadata
        }
    except Exception as e:
        print("Error adding metadata: " + str(e))
        return {"status": "error", "message": str(e)}

def get_objects_with_metadata(filters=None, metadata_fields=None):
    """Get objects with their metadata, with optional filtering and field selection"""
    try:
        import re
        import json
        
        filters = filters or {}
        layer_filter = filters.get("layer")
        name_filter = filters.get("name")
        id_filter = filters.get("short_id")
        
        # Validate metadata fields
        all_fields = VALID_METADATA_FIELDS['required'] + VALID_METADATA_FIELDS['optional']
        if metadata_fields:
            invalid_fields = [f for f in metadata_fields if f not in all_fields]
            if invalid_fields:
                return {
                    "status": "error",
                    "message": "Invalid metadata fields: " + ", ".join(invalid_fields),
                    "available_fields": all_fields
                }
        
        objects = []
        
        for obj in sc.doc.Objects:
            obj_id = obj.Id
            
            # Apply layer filter with wildcard support
            if layer_filter:
                layer = rs.ObjectLayer(obj_id)
                pattern = "^" + layer_filter.replace("*", ".*") + "$"
                if not re.match(pattern, layer, re.IGNORECASE):
                    continue
                
            # Apply name filter with wildcard support
            if name_filter:
                name = obj.Name or ""
                pattern = "^" + name_filter.replace("*", ".*") + "$"
                if not re.match(pattern, name, re.IGNORECASE):
                    continue
                
            # Apply ID filter
            if id_filter:
                short_id = rs.GetUserText(obj_id, "short_id") or ""
                if short_id != id_filter:
                    continue
                
            # Build base object data with required fields
            obj_data = {
                "id": str(obj_id),
                "name": obj.Name or "Unnamed",
                "type": obj.Geometry.GetType().Name,
                "layer": rs.ObjectLayer(obj_id)
            }
            
            # Get user text data and parse stored values
            stored_data = {}
            for key in rs.GetUserText(obj_id):
                value = rs.GetUserText(obj_id, key)
                if key == "bbox":
                    try:
                        value = json.loads(value)
                    except:
                        value = []
                elif key == "created_at":
                    try:
                        value = float(value)
                    except:
                        value = 0
                stored_data[key] = value
            
            # Build metadata based on requested fields
            if metadata_fields:
                metadata = {k: stored_data[k] for k in metadata_fields if k in stored_data}
            else:
                # When no fields specified, include all non-required fields
                metadata = {k: v for k, v in stored_data.items() 
                          if k not in VALID_METADATA_FIELDS['required']}
            
            # Only include user_text if specifically requested
            if not metadata_fields or 'user_text' in metadata_fields:
                # Filter out fields that are already in metadata
                user_text = {k: v for k, v in stored_data.items() 
                           if k not in metadata}
                if user_text:
                    obj_data["user_text"] = user_text
            
            # Add metadata if we have any
            if metadata:
                obj_data["metadata"] = metadata
                
            objects.append(obj_data)
        
        return {
            "status": "success",
            "count": len(objects),
            "objects": objects,
            "available_fields": all_fields
        }
        
    except Exception as e:
        print("Error filtering objects: " + str(e))
        return {
            "status": "error",
            "message": str(e),
            "available_fields": all_fields
        }

def execute_test_code(code):
    """Execute arbitrary Python code in Rhino for testing"""
    try:
        # Create a local dictionary for code execution
        local_dict = {}
        # Make sure add_object_metadata is available to the executed code
        local_dict["add_object_metadata"] = add_object_metadata
        
        exec(code, globals(), local_dict)
        
        return {
            "status": "success",
            "result": str(local_dict.get("result", "Code executed successfully"))
        }
    except Exception as e:
        import traceback
        print("Error executing code:")
        print(traceback.format_exc())
        return {"status": "error", "message": str(e)}

#--------------------------------------
# Helper Functions
#--------------------------------------

def ensure_annotation_layer():
    """Create annotation layer if it doesn't exist"""
    if not rs.IsLayer(ANNOTATION_LAYER):
        rs.AddLayer(ANNOTATION_LAYER, color=(255, 0, 0))  # Red color for visibility
    return ANNOTATION_LAYER

def generate_short_id():
    """Generate a short ID based on current time: DDHHMMSS"""
    now = datetime.datetime.now()
    return now.strftime("%d%H%M%S")  # e.g., "13142359" for 13th day, 14:23:59

def find_by_short_id(short_id):
    """Utility function to find object by short ID"""
    all_objects = sc.doc.Objects
    for obj in all_objects:
        if rs.GetUserText(obj.Id, "short_id") == short_id:
            return obj.Id
    return None

def clear_annotations():
    """Clear all annotations from the MCP_Annotations layer"""
    if rs.IsLayer(ANNOTATION_LAYER):
        objects = rs.ObjectsByLayer(ANNOTATION_LAYER)
        if objects:
            rs.DeleteObjects(objects)
            print("Cleared all annotations")
        else:
            print("No annotations to clear")

def print_json(data):
    """Pretty print JSON data"""
    if isinstance(data, dict):
        print(json.dumps(data, indent=2))
    else:
        print(data)

def cleanup_test_objects(object_ids):
    """Clean up test objects created during tests"""
    print("\n===== CLEANING UP TEST OBJECTS =====")
    
    try:
        # Clean up specific objects
        if object_ids:
            deleted_count = 0
            for obj_id in object_ids:
                if rs.IsObject(obj_id):
                    if rs.DeleteObject(obj_id):
                        deleted_count += 1
            if deleted_count > 0:
                print("Deleted {0} specific test objects".format(deleted_count))
        
        # Clean up any remaining test objects by name pattern
        test_patterns = ["Test*", "MCP Test*", "Building_*", "Tower_*"]
        pattern_counts = {}
        for pattern in test_patterns:
            objects = rs.ObjectsByName(pattern, select=False)
            if objects:
                count = len(objects)
                if rs.DeleteObjects(objects):
                    pattern_counts[pattern] = count
        
        if pattern_counts:
            print("Deleted objects matching patterns:")
            for pattern, count in pattern_counts.items():
                print("  - {0}: {1} objects".format(pattern, count))
        
        # Clean up annotations
        clear_annotations()
        
    except Exception as e:
        print("Error during cleanup: " + str(e))

#--------------------------------------
# Test Functions
#--------------------------------------

def test_metadata_creation():
    """Test creating objects and adding metadata"""
    print("\n===== TESTING METADATA CREATION =====")
    
    try:
        # Create a test cube - using basic box creation
        print("Creating test cube...")
        # Create box using basic coordinates
        points = [
            [0,0,0],
            [5,0,0],
            [5,5,0],
            [0,5,0],
            [0,0,5],
            [5,0,5],
            [5,5,5],
            [0,5,5]
        ]
        cube_id = rs.AddBox(points)
        
        if not cube_id:
            print("Failed to create test cube")
            return None
            
        # Add metadata
        print("Adding metadata...")
        result = add_object_metadata(cube_id, "Test Cube", "A test cube for metadata")
        
        # Display result
        print("\nMetadata added:")
        print_json(result)
        
        if result["status"] == "success":
            print("\nRetrieving object metadata:")
            short_id = result.get("metadata", {}).get("short_id", "")
            objects = get_objects_with_metadata({"short_id": short_id})
            print("Found {0} objects with short_id '{1}'".format(
                len(objects.get("objects", [])), short_id))
            return cube_id
        else:
            print("Failed to add metadata")
            return None
            
    except Exception as e:
        print("Error in test_metadata_creation: {0}".format(str(e)))
        return None

def test_filters():
    """Test object filtering with various criteria"""
    print("\n===== TESTING OBJECT FILTERING =====")
    
    try:
        # Create several test objects in different layers
        print("Creating test objects...")
        
        # Ensure test layers exist
        test_layer1 = "Test_Layer_1"
        test_layer2 = "Test_Layer_2"
        if not rs.IsLayer(test_layer1):
            rs.AddLayer(test_layer1)
        if not rs.IsLayer(test_layer2):
            rs.AddLayer(test_layer2)
        
        # Store original layer to restore later
        original_layer = rs.CurrentLayer()
        created_objects = []
        
        try:
            # Create objects on first layer
            rs.CurrentLayer(test_layer1)
            
            # Create box using basic coordinates
            points1 = [
                [0,0,0], [3,0,0], [3,3,0], [0,3,0],
                [0,0,3], [3,0,3], [3,3,3], [0,3,3]
            ]
            cube1_id = rs.AddBox(points1)
            add_object_metadata(cube1_id, "Building_A", "Test building A")
            created_objects.append(cube1_id)
            
            sphere1_id = rs.AddSphere([5, 5, 0], 2)
            add_object_metadata(sphere1_id, "Building_B", "Test building B")
            created_objects.append(sphere1_id)
            
            # Create objects on second layer
            rs.CurrentLayer(test_layer2)
            points2 = [
                [10,0,0], [15,0,0], [15,5,0], [10,5,0],
                [10,0,5], [15,0,5], [15,5,5], [10,5,5]
            ]
            cube2_id = rs.AddBox(points2)
            add_object_metadata(cube2_id, "Tower_1", "Test tower 1")
            created_objects.append(cube2_id)
            
            sphere2_id = rs.AddSphere([15, 10, 0], 2)
            add_object_metadata(sphere2_id, "Tower_2", "Test tower 2")
            created_objects.append(sphere2_id)
            
            # Test various filters
            print("\nTesting layer filter:")
            result = get_objects_with_metadata({"layer": test_layer1})
            print("Found {0} objects in layer '{1}'".format(
                len(result.get("objects", [])), test_layer1))
            
            print("\nTesting name filter with wildcard:")
            result = get_objects_with_metadata({"name": "Building_*"})
            print("Found {0} objects with name pattern 'Building_*'".format(
                len(result.get("objects", []))))
            
            print("\nTesting combined filters:")
            result = get_objects_with_metadata({
                "layer": test_layer2,
                "name": "Tower_*"
            })
            print("Found {0} objects with layer '{1}' and name pattern 'Tower_*'".format(
                len(result.get("objects", [])), test_layer2))
            
            return created_objects
            
        finally:
            # Restore original layer
            rs.CurrentLayer(original_layer)
            
    except Exception as e:
        print("Error in test_filters: {0}".format(str(e)))
        return []

def test_viewport_capture():
    """Test viewport capture with and without annotations"""
    print("\n===== TESTING VIEWPORT CAPTURE =====")
    
    try:
        # Ensure we have some objects with metadata
        print("Creating test objects if none exist...")
        existing_objects = rs.AllObjects()
        test_objects = []
        
        if not existing_objects:
            # Create a test box
            points = [
                [0,0,0], [5,0,0], [5,5,0], [0,5,0],
                [0,0,5], [5,0,5], [5,5,5], [0,5,5]
            ]
            cube_id = rs.AddBox(points)
            add_object_metadata(cube_id, "Test Cube", "A test cube")
            test_objects.append(cube_id)
            
            sphere_id = rs.AddSphere([10, 0, 0], 3)
            add_object_metadata(sphere_id, "Test Sphere", "A test sphere")
            test_objects.append(sphere_id)
        
        # Capture with annotations
        print("\nCapturing viewport with annotations...")
        result = capture_viewport(show_annotations=True)
        if result.get("type") == "image":
            print("Successfully captured viewport with annotations")
            print("Image data length: {0} characters".format(
                len(result.get("source", {}).get("data", ""))))
        else:
            print("Failed to capture viewport with annotations")
            print_json(result)
        
        # Capture without annotations
        print("\nCapturing viewport without annotations...")
        result = capture_viewport(show_annotations=False)
        if result.get("type") == "image":
            print("Successfully captured viewport without annotations")
            print("Image data length: {0} characters".format(
                len(result.get("source", {}).get("data", ""))))
        else:
            print("Failed to capture viewport without annotations")
            print_json(result)
        
        return test_objects
        
    except Exception as e:
        print("Error in test_viewport_capture: {0}".format(str(e)))
        return []

def test_code_execution():
    """Test code execution that creates objects with metadata"""
    print("\n===== TESTING CODE EXECUTION =====")
    
    # Create simpler test code using basic box creation
    test_code = """
import rhinoscriptsyntax as rs
import scriptcontext as sc

# Create a simple box using corner points
points = [
    [0,0,0], [4,0,0], [4,4,0], [0,4,0],
    [0,0,4], [4,0,4], [4,4,4], [0,4,4]
]
cube_id = rs.AddBox(points)

# Add metadata
metadata_result = add_object_metadata(cube_id, "MCP Test Cube", "Created through code execution")

# Store the result for reference
result = "Created cube with ID: " + str(cube_id)
"""
    
    try:
        # Execute the test code
        print("Executing test code...")
        result = execute_test_code(test_code)
        
        # Display result
        print("\nCode execution result:")
        print_json(result)
        
        if result["status"] == "success":
            print("\nVerifying created object exists:")
            objects = get_objects_with_metadata({"name": "MCP Test Cube"})
            print("Found {0} objects with name 'MCP Test Cube'".format(
                len(objects.get("objects", []))))
            if objects.get("objects"):
                print("Object metadata:")
                print_json(objects["objects"][0])
        else:
            print("\nFailed to create test object")
            
    except Exception as e:
        print("Error in test_code_execution: {0}".format(str(e)))

def test_metadata_field_selection():
    """Test metadata field selection in object filtering"""
    print("\n===== TESTING METADATA FIELD SELECTION =====")
    
    try:
        # Create a test object with full metadata
        points = [
            [0,0,0], [4,0,0], [4,4,0], [0,4,0],
            [0,0,4], [4,0,4], [4,4,4], [0,4,4]
        ]
        cube_id = rs.AddBox(points)
        add_object_metadata(cube_id, "Test Field Selection", "Testing metadata fields")
        
        # Test different field combinations
        print("\nTesting with specific fields:")
        result = get_objects_with_metadata(
            filters={"name": "Test Field Selection"},
            metadata_fields=['short_id', 'description']
        )
        print_json(result)
        
        print("\nTesting with invalid field:")
        result = get_objects_with_metadata(
            filters={"name": "Test Field Selection"},
            metadata_fields=['invalid_field']
        )
        print_json(result)
        
        print("\nTesting with no field selection (all fields):")
        result = get_objects_with_metadata(
            filters={"name": "Test Field Selection"}
        )
        print_json(result)
        
        return cube_id
        
    except Exception as e:
        print("Error in test_metadata_field_selection: " + str(e))
        return None

def run_all_tests():
    """Run all tests automatically"""
    from datetime import datetime
    
    print("\n============================================")
    print("Starting RhinoMCP Function Testing")
    print("Timestamp: {0}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("============================================\n")
    
    # Ensure we're in a clean state
    clear_annotations()
    
    # Store created objects for cleanup
    created_objects = []
    
    # Run all tests sequentially
    try:
        # Test 1: Metadata Creation
        obj_id = test_metadata_creation()
        if obj_id:
            created_objects.append(obj_id)
        
        # Test 2: Object Filtering
        filter_objects = test_filters()
        created_objects.extend(filter_objects)
        
        # Test 3: Viewport Capture
        capture_objects = test_viewport_capture()
        created_objects.extend(capture_objects)
        
        # Test 4: Code Execution
        test_code_execution()
        
        # Test 5: Metadata Field Selection
        field_test_obj = test_metadata_field_selection()
        if field_test_obj:
            created_objects.append(field_test_obj)
        
    finally:
        # Clean up all created objects
        cleanup_test_objects(created_objects)
        
        print("\n============================================")
        print("Testing completed at: {0}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        print("============================================")

# Remove the menu system and just run all tests
if __name__ == "__main__":
    run_all_tests() 