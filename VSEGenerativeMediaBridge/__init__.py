# VSE Generative Media Bridge
# Copyright (C) 2024 Paul Siegfried
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.



import sys
import importlib
import os

# --- Module reloading for development ---
# When this script is reloaded, we need to reload our sub-modules too.
# This is important for development so we can see changes without restarting Blender.
if "bpy" in locals():
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
