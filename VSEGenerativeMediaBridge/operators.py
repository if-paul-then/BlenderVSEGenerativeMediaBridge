import bpy
import uuid
from bpy.types import Operator
from bpy.props import StringProperty
from .ui import get_generator_config
from .utils import get_gmb_type_from_strip

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
        
        # --- Pre-selection Logic ---
        # Find the generator config first to know what inputs are needed
        gen_config = get_generator_config(context, self.generator_name)
        if not gen_config:
            self.report({'ERROR'}, f"Generator '{self.generator_name}' not found.")
            return {'CANCELLED'}
        
        available_strips = list(context.selected_sequences)
        active_strip = context.active_strip
        if active_strip:
            # Move the active strip to the front of the list
            available_strips.remove(active_strip)
            available_strips.insert(0, active_strip)
        matched_uuids = {} # Dict to store {input_name: strip_uuid}

        # Try to match selected strips to the generator's input properties
        for input_prop in gen_config.inputs:
            # Find an unused, selected strip of the correct type
            for strip in available_strips:
                strip_gmb_type = get_gmb_type_from_strip(strip)
                if strip_gmb_type == input_prop.type:
                    # Match found. Ensure the strip has a GMB ID.
                    if "gmb_id" not in strip:
                        strip["gmb_id"] = uuid.uuid4().hex
                    matched_uuids[input_prop.name] = strip["gmb_id"]
                    # Remove the strip from the available pool so it can't be matched again
                    available_strips.remove(strip)
                    break # Move to the next input_prop

        # --- Strip Creation ---
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
        
        # Pre-populate the input link slots based on the generator's config
        if gen_config:
            for input_prop in gen_config.inputs:
                link = gmb_properties.linked_inputs.add()
                link.name = input_prop.name
                # If we found a match during pre-selection, set the UUID
                if input_prop.name in matched_uuids:
                    link.linked_strip_uuid = matched_uuids[input_prop.name]

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