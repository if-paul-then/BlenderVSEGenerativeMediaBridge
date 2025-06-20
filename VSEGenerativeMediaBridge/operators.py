import bpy
import uuid
from bpy.types import Operator
from bpy.props import StringProperty

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

class GMB_OT_add_generator_strip(Operator):
    """Add a new generator strip to the timeline."""
    bl_idname = "gmb.add_generator_strip"
    bl_label = "Add Generator Strip"
    bl_options = {'REGISTER', 'UNDO'}

    generator_name: StringProperty(
        name="Generator Name",
        description="The name of the generator to add."
    )

    def execute(self, context):
        scene = context.scene
        
        # Add the new strip to the timeline
        new_strip = scene.sequence_editor.sequences.new_effect(
            name=self.generator_name,
            type='ADJUSTMENT', # Use an Adjustment Layer as a controller strip
            channel=1, # TODO: Find first empty channel
            frame_start=scene.frame_current,
            frame_end=scene.frame_current + 100 # TODO: Make this configurable
        )
        
        # Create a new property group for our strip's data
        gmb_properties = scene.gmb_strip_properties.add()
        gmb_properties.id = uuid.uuid4().hex
        gmb_properties.generator_name = self.generator_name
        
        # Link the VSE strip to our property group using the generated UUID
        new_strip["gmb_id"] = gmb_properties.id
        
        return {'FINISHED'}

classes = (
    GMB_OT_add_generator,
    GMB_OT_remove_generator,
    GMB_OT_add_generator_strip,
)

def register():
    """Register the operator classes."""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    """Unregister the operator classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 