import bpy
from bpy.types import Operator

def get_prefs(context):
    """Get the addon preferences."""
    return context.preferences.addons[__package__].preferences

class GMB_OT_add_generator(Operator):
    """Add a new generator to the list."""
    bl_idname = "gmb.generator_add"
    bl_label = "Add Generator"

    def execute(self, context):
        prefs = get_prefs(context)
        new_generator = prefs.generators.add()
        new_generator.name = f"New Generator"
        prefs.active_generator_index = len(prefs.generators) - 1
        return {'FINISHED'}

class GMB_OT_remove_generator(Operator):
    """Remove the selected generator from the list."""
    bl_idname = "gmb.generator_remove"
    bl_label = "Remove Generator"

    @classmethod
    def poll(cls, context):
        """Disable the button if the list is empty."""
        prefs = get_prefs(context)
        return len(prefs.generators) > 0

    def execute(self, context):
        prefs = get_prefs(context)
        index = prefs.active_generator_index
        prefs.generators.remove(index)
        
        if index >= len(prefs.generators):
            prefs.active_generator_index = len(prefs.generators) - 1
            
        return {'FINISHED'}

classes = (
    GMB_OT_add_generator,
    GMB_OT_remove_generator,
)

def register():
    """Register the operator classes."""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    """Unregister the operator classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 