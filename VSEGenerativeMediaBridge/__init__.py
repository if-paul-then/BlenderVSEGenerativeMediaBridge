bl_info = {
    "name": "VSE Generative Media Bridge",
    "author": "Paul & Joshua",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "VSE > Add > Generative Media",
    "description": "Bridge between the VSE and external generative tools",
    "warning": "",
    "doc_url": "",
    "category": "VSE",
}

# Support for multi-file addon reloading
if "bpy" in locals():
    import importlib
    if "yaml_parser" in locals():
        importlib.reload(yaml_parser)
    if "properties" in locals():
        importlib.reload(properties)
    if "ui" in locals():
        importlib.reload(ui)
    if "operators" in locals():
        importlib.reload(operators)

from . import properties, ui, operators, yaml_parser
import bpy

def register():
    """Register the addon classes."""
    print("Registering addon")
    properties.register()
    ui.register()
    operators.register()
    print("Registered addon")

def unregister():
    """Unregister the addon classes."""
    print("Unregistering addon")
    properties.unregister()
    ui.unregister()
    operators.unregister()
    print("Unregistered addon")

if __name__ == "__main__":
    register() 