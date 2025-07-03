import bpy
from bpy.types import UIList


class GMB_UL_Generators(UIList):
    """UIList for displaying generator configurations."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # We could override this to custom-draw each row
        # For now, the default drawing is fine, which just shows the 'name' property
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


classes = (
    GMB_UL_Generators,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 