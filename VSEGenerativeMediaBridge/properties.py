import bpy
from bpy.props import StringProperty, CollectionProperty
from bpy.types import PropertyGroup, AddonPreferences


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

    def draw(self, context):
        """Draw the preferences panel."""
        layout = self.layout
        layout.label(text="This is a placeholder for the generator list UI.")

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