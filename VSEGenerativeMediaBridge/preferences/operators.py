import bpy
import os
from bpy.types import Operator
from bpy.props import StringProperty
from ..utils import get_prefs


class GMB_OT_add_generator(Operator):
    """Add a new generator from a YAML file."""
    bl_idname = "gmb.generator_add"
    bl_label = "Add Generator from File"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(
        name="File Path",
        description="Path to the YAML configuration file",
        subtype='FILE_PATH'
    )
    filter_glob: StringProperty(
        default="*.yaml;*.yml",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if not self.filepath:
            self.report({'WARNING'}, "No file selected.")
            return {'CANCELLED'}
        
        prefs = get_prefs(context)

        # Check for duplicates
        if any(g.config_filepath == self.filepath for g in prefs.generators):
            self.report({'WARNING'}, f"Generator with this config file already exists.")
            return {'CANCELLED'}

        new_generator = prefs.generators.add()
        # This assignment will trigger the 'update_config_filepath' function
        new_generator.config_filepath = self.filepath 
        
        # The update function should have populated the name. 
        # If not, it means parsing failed. The update function is responsible for reporting errors.
        if not new_generator.name:
            # The update function will set the name to "Invalid/Unparsed YAML" on failure.
            # We can remove the failed entry.
            prefs.generators.remove(len(prefs.generators) - 1)
            # The error would have been printed to the console from the update function.
            self.report({'ERROR'}, f"Failed to parse '{os.path.basename(self.filepath)}'. See console for details.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Added generator '{new_generator.name}'")
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
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 