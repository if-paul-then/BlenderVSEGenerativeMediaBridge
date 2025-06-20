import bpy
import uuid
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty
from bpy.types import PropertyGroup, AddonPreferences, Scene
from .ui import GMB_UL_Generators
from .yaml_parser import parse_yaml_config


def update_config_filepath(self, context):
    """
    This function is called by Blender whenever the config_filepath is updated.
    It reads the file, parses the YAML, and populates the structured properties.
    """
    # Clear any previously parsed data
    self.inputs.clear()
    self.outputs.clear()

    if not self.config_filepath:
        return

    try:
        with open(self.config_filepath, 'r') as f:
            yaml_string = f.read()
        parsed_data = parse_yaml_config(yaml_string)
    except FileNotFoundError:
        print(f"Error: File not found at {self.config_filepath}")
        return
    except Exception as e:
        print(f"Error reading or parsing file: {e}")
        return

    if not parsed_data:
        return

    # Populate the 'input' properties
    if 'properties' in parsed_data and 'input' in parsed_data['properties']:
        for prop_data in parsed_data['properties']['input']:
            if isinstance(prop_data, dict) and 'name' in prop_data:
                item = self.inputs.add()
                item.name = prop_data.get('name', '')
                item.type = prop_data.get('type', 'TEXT')
                item.pass_via = prop_data.get('pass-via', 'TEXT')
                item.required = prop_data.get('required', True)

    # Populate the 'output' properties
    if 'properties' in parsed_data and 'output' in parsed_data['properties']:
        for prop_data in parsed_data['properties']['output']:
            if isinstance(prop_data, dict) and 'name' in prop_data:
                item = self.outputs.add()
                item.name = prop_data.get('name', '')
                item.type = prop_data.get('type', 'IMAGE')
                item.pass_via = prop_data.get('pass-via', 'FILE')
                item.file_ext = prop_data.get('file-ext', '.png')
                item.required = prop_data.get('required', True)


class GMB_InputProperty(PropertyGroup):
    """A parsed 'input' property from the YAML config."""
    name: StringProperty(name="Name")
    type: EnumProperty(
        name="Type",
        items=[
            ('TEXT', "Text", "Text data"),
            ('IMAGE', "Image", "Image media"),
            ('AUDIO', "Audio", "Audio media"),
            ('VIDEO', "Video", "Video media"),
        ]
    )
    pass_via: EnumProperty(
        name="Pass Via",
        items=[
            ('FILE', "File", "Pass the data via a temporary file"),
            ('TEXT', "Text", "Pass the data directly as a string"),
            ('STREAM', "Stream", "Pass the data via stdin/stdout stream"),
        ]
    )
    required: BoolProperty(name="Required", default=True)


class GMB_OutputProperty(PropertyGroup):
    """A parsed 'output' property from the YAML config."""
    name: StringProperty(name="Name")
    type: EnumProperty(
        name="Type",
        items=[
            ('TEXT', "Text", "Text data"),
            ('IMAGE', "Image", "Image media"),
            ('AUDIO', "Audio", "Audio media"),
            ('VIDEO', "Video", "Video media"),
        ]
    )
    pass_via: EnumProperty(
        name="Pass Via",
        items=[
            ('FILE', "File", "Receive the data from a temporary file"),
            ('STREAM', "Stream", "Receive the data via stdin/stdout stream"),
        ]
    )
    file_ext: StringProperty(name="File Extension")
    required: BoolProperty(name="Required", default=True)


class GMB_StripProperties(PropertyGroup):
    """Properties for a generator strip, stored in a scene-level collection."""
    # This UUID will be used to link this property group to a specific VSE strip.
    id: StringProperty(
        name="UUID",
        description="A unique identifier to link this data to a VSE strip."
    )
    generator_name: StringProperty(
        name="Generator Name",
        description="The name of the generator used by this strip."
    )


class GMB_GeneratorConfig(PropertyGroup):
    """A generator configuration."""
    name: StringProperty(
        name="Name",
        description="A unique name for the generator.",
        default="New Generator"
    )
    config_filepath: StringProperty(
        name="Config File",
        description="Path to the YAML configuration file for the generator.",
        subtype='FILE_PATH',
        update=update_config_filepath
    )
    # Collections to store the parsed YAML data
    inputs: CollectionProperty(type=GMB_InputProperty)
    outputs: CollectionProperty(type=GMB_OutputProperty)


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
            box.prop(active_generator, "config_filepath")
        else:
            # Provide feedback when the list is empty
            layout.box().label(text="Add a generator to get started.")

classes = (
    GMB_InputProperty,
    GMB_OutputProperty,
    GMB_StripProperties,
    GMB_GeneratorConfig,
    GMB_AddonPreferences,
)

def register():
    """Register the property classes."""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    Scene.gmb_strip_properties = CollectionProperty(type=GMB_StripProperties)

def unregister():
    """Unregister the property classes."""
    del Scene.gmb_strip_properties

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 