import bpy
from bpy.props import StringProperty, CollectionProperty, IntProperty
from bpy.types import PropertyGroup, AddonPreferences
from .ui import GMB_UL_Generators


class GMB_GeneratorConfig(PropertyGroup):
    """A generator configuration."""
    name: StringProperty(
        name="Name",
        description="A unique name for the generator.",
        default="New Generator"
    )
    yaml_config: StringProperty(
        name="YAML Config",
        description="The YAML configuration for the generator."
    )


class GMB_AddonPreferences(AddonPreferences):
    """Addon preferences for VSE Generative Media Bridge."""
    bl_idname = __package__

    generators: CollectionProperty(
        name="Generators",
        description="The list of available generators.",
        type=GMB_GeneratorConfig
    )

    active_generator_index: IntProperty(
        name="Active Generator Index",
        default=0
    )

    def draw(self, context):
        """Draw the preferences panel."""
        layout = self.layout
        
        # --- Row for the list and its side-buttons ---
        list_row = layout.row()
        list_row.template_list(
            "GMB_UL_Generators",
            "",
            self,
            "generators",
            self,
            "active_generator_index"
        )
        
        button_col = list_row.column(align=True)
        button_col.operator("gmb.generator_add", icon='ADD', text="")
        button_col.operator("gmb.generator_remove", icon='REMOVE', text="")
        
        # --- Properties drawn below the list ---
        if self.generators and self.active_generator_index < len(self.generators):
            active_generator = self.generators[self.active_generator_index]
            
            box = layout.box()
            box.prop(active_generator, "name")
            
            # Draw the yaml_config property to look like a multiline editor
            box.label(text="YAML Config:")
            inner_box = box.box()
            # The prop call inside a box without a label makes it look like a multi-line text editor
            inner_box.prop(active_generator, "yaml_config", text="")
        else:
            # Provide feedback when the list is empty
            layout.box().label(text="Add a generator to get started.")

classes = (
    GMB_GeneratorConfig,
    GMB_AddonPreferences,
)

def register():
    """Register the property classes."""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    """Unregister the property classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 