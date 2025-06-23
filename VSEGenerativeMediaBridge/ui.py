import bpy
from bpy.types import UIList, Menu, Panel
from .utils import get_strip_by_uuid


def get_prefs(context):
    """Get the addon preferences."""
    return context.preferences.addons[__package__].preferences


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
            for link in gmb_props.linked_inputs:
                # First, find the strip that is actually linked via UUID
                # linked_strip = get_strip_by_uuid(link.linked_strip_uuid)
                # if linked_strip:
                    # If found, set the temporary UI property to its name for display
                    # link.ui_strip_name = linked_strip.name

                # Now, draw the special search UI element
                inputs_box.prop_search(
                    link, 
                    "ui_strip_name", 
                    context.scene.sequence_editor, 
                    "sequences_all",
                    text=link.name
                )
                # inputs_box.prop(link, "linked_strip_uuid", text=link.name + " ID")
                # if linked_strip:
                #     inputs_box.prop(linked_strip, "name", text=link.name + " Name")

        # --- Operator Buttons ---
        op_row = layout.row(align=True)
        
        # Disable the button if the process is already running
        is_running = gmb_props.status == 'RUNNING'
        op_row.enabled = not is_running
        
        # Show different text based on the status
        if is_running:
            run_button_text = f"Running ({gmb_props.status})..."
        else:
            run_button_text = f"Generate ({gmb_props.status})"
            
        run_op = op_row.operator("gmb.run_script", text=run_button_text, icon='PLAY')
        run_op.strip_id = gmb_props.id


def draw_add_menu(self, context):
    """Draw the 'Generative Media' entry in the VSE Add menu."""
    self.layout.menu(GMB_MT_add_generator.bl_idname)


classes = (
    GMB_UL_Generators,
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