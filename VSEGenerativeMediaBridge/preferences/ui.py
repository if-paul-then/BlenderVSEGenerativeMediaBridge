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

import bpy
from bpy.types import UIList


class GMB_UL_Generators(UIList):
    """UIList for displaying generator configurations."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Custom drawing for each row - shows the 'name' property
        layout.prop(item, "name", text="", emboss=False, icon_value=icon)


classes = (
    GMB_UL_Generators,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 