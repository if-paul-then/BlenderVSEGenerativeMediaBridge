import bpy
from bpy.types import Menu, Panel
from .utils import get_strip_by_uuid, get_prefs


def get_generator_config(context, generator_name):
    """Find a generator configuration by name from the addon preferences."""
    prefs = get_prefs(context)
    for config in prefs.generators:
        if config.name == generator_name:
            return config
    return None


def get_gmb_properties(context):
    """Get the GMB properties for the active VSE strip."""
    strip = context.active_sequence_strip
    if not strip or "gmb_id" not in strip:
        return None
    
    gmb_id = strip["gmb_id"]
    for props in context.scene.gmb_strip_properties:
        if props.id == gmb_id:
            return props
    return None


class GMB_MT_add_generator(Menu):
    """Dynamic menu for adding a generator strip."""
    bl_idname = "GMB_MT_add_generator"
    bl_label = "Generative Media"

    def draw(self, context):
        layout = self.layout
        prefs = get_prefs(context)
        
        if not prefs.generators:
            layout.label(text="No generators defined.", icon='INFO')
            return

        for gen in prefs.generators:
            # This will call the 'add_generator_strip' operator in a later milestone
            # For now, it won't do anything, but the menu item will appear.
            op = layout.operator("gmb.add_generator_strip", text=gen.name)
            op.generator_name = gen.name


class GMB_PT_vse_sidebar(Panel):
    """Sidebar panel for Generative Media strips."""
    bl_label = "Generative Media"
    bl_idname = "GMB_PT_vse_sidebar"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Strip"

    @classmethod
    def poll(cls, context):
        """Only show the panel if the active strip is a GMB strip."""
        strip = context.active_sequence_strip
        return strip and "gmb_id" in strip

    def draw(self, context):
        layout = self.layout
        gmb_props = get_gmb_properties(context)

        if not gmb_props:
            layout.label(text="Data link is broken.", icon='ERROR')
            return

        box = layout.box()
        box.label(text=f"Generator: {gmb_props.generator_name}")

        # Get the full generator configuration
        gen_config = get_generator_config(context, gmb_props.generator_name)

        if not gen_config:
            box.label(text="Generator config not found!", icon='ERROR')
            return
        
        # Draw the dynamic properties based on the parsed YAML
        if not gen_config.inputs:
            box.label(text="No inputs defined for this generator.")
        else:
            inputs_box = box.box()
            inputs_box.label(text="Inputs:")

            # Create a mapping of input names to their definitions for efficient lookup
            input_defs_map = {idef.name: idef for idef in gen_config.inputs}

            for link in gmb_props.linked_inputs:
                input_def = input_defs_map.get(link.name)
                if not input_def:
                    raise ValueError(f"Input definition not found for {link.name}")
                
                # Visual cue in the label text
                label_text = link.name
                if input_def.required:
                    label_text = f"{link.name} *"

                inputs_box.prop_search(
                    link, 
                    "ui_strip_name", 
                    context.scene.sequence_editor, 
                    "sequences_all",
                    text=label_text
                )

        # --- Draw the outputs section for multi-output controllers ---
        if gmb_props.linked_outputs:
            outputs_box = box.box()
            outputs_box.label(text="Outputs:")
            for link in gmb_props.linked_outputs:
                # We show the name of the output property and the name of the strip it's linked to.
                strip = get_strip_by_uuid(link.linked_strip_uuid)
                strip_name = f"'{strip.name}'" if strip else "[Not Found]"
                outputs_box.label(text=f"{link.name}: {strip_name}")

        # --- Operator Buttons ---
        is_running = gmb_props.status == 'RUNNING'

        if is_running:
            # Show Cancel button and status box
            op_row = layout.row(align=True)
            cancel_op = op_row.operator("gmb.cancel_generation", text="Cancel Generation", icon='CANCEL')
            cancel_op.strip_id = gmb_props.id
            
            status_box = layout.box()
            status_box.label(text=f"Running... {gmb_props.runtime_seconds:.1f}s")
            
            if gmb_props.log_history:
                log_box = status_box.box()
                for log_entry in gmb_props.log_history:
                    log_box.label(text=log_entry.line)

        else:
            op_row = layout.row(align=True)
            
            # Logic to check if all required inputs are linked
            all_required_set = True
            if gen_config:
                # Create a mapping of input names to their linked UUIDs for efficient lookup
                linked_input_uuids = {link.name: link.linked_strip_uuid for link in gmb_props.linked_inputs}

                for input_def in gen_config.inputs:
                    if input_def.required:
                        # Check if the required input is not linked (either not in the dict or UUID is empty)
                        if not linked_input_uuids.get(input_def.name):
                            all_required_set = False
                            break # No need to check further

            # Disable the button if required inputs are missing
            op_row.enabled = all_required_set
            
            run_op = op_row.operator("gmb.generate_media", text="Generate", icon='PLAY')
            run_op.strip_id = gmb_props.id


def draw_add_menu(self, context):
    """Draw the 'Generative Media' entry in the VSE Add menu."""
    self.layout.menu(GMB_MT_add_generator.bl_idname)


classes = (
    GMB_MT_add_generator,
    GMB_PT_vse_sidebar,
)


def register():
    """Register the UI classes."""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.SEQUENCER_MT_add.append(draw_add_menu)


def unregister():
    """Unregister the UI classes."""
    bpy.types.SEQUENCER_MT_add.remove(draw_add_menu)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 