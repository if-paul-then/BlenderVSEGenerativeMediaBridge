bl_info = {
    "name": "VSE Generative Media Bridge",
    "author": "Paul Siegfried",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "VSE > Add Menu & Sidebar",
    "description": "A bridge between Blender's VSE and external generative tools",
    "warning": "",
    "doc_url": "",
    "category": "VSE",
}

import sys
import importlib
import os

# --- Path setup for vendored dependencies ---
# Ensure the 'dependencies' directory is in Python's path
addon_dir = os.path.dirname(__file__)
dependencies_dir = os.path.join(addon_dir, "dependencies")
if dependencies_dir not in sys.path:
    sys.path.append(dependencies_dir)

# --- Module reloading for development ---
# When this script is reloaded, we need to reload our sub-modules too.
# This is important for development so we can see changes without restarting Blender.
if "bpy" in locals():
    from . import dependencies
    importlib.reload(dependencies)
    from . import utils
    importlib.reload(utils)
    from . import yaml_parser
    importlib.reload(yaml_parser)
    from . import properties
    importlib.reload(properties)
    from . import operators
    importlib.reload(operators)
    from . import ui
    importlib.reload(ui)
    
    # Reload the new preferences package and its modules
    from . import preferences
    importlib.reload(preferences)
    if hasattr(preferences, "operators"):
        importlib.reload(preferences.operators)
    if hasattr(preferences, "ui"):
        importlib.reload(preferences.ui)


from . import dependencies
from . import utils
from . import yaml_parser
from . import properties
from . import operators
from . import ui
from . import preferences


def register():
    """Register all parts of the addon."""
    properties.register()
    operators.register()
    ui.register()
    preferences.register()


def unregister():
    """Unregister all parts of the addon."""
    properties.unregister()
    operators.unregister()
    ui.unregister()
    preferences.unregister()


if __name__ == "__main__":
    register() 