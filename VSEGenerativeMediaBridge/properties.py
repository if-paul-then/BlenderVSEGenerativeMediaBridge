import bpy
import uuid
from bpy.props import StringProperty, CollectionProperty, IntProperty, BoolProperty, EnumProperty
from bpy.types import PropertyGroup, AddonPreferences, Scene
from .yaml_parser import parse_yaml_config
from .utils import get_strip_by_uuid


def set_ui_strip_name(self, strip_name):
    """
    This function is called by Blender whenever the ui_strip_name property is set.
    It sets the name of the strip that is linked to this input link.
    """
    # Find the strip the user selected by its name
    target_strip = bpy.context.scene.sequence_editor.sequences.get(strip_name)
    if target_strip:
        # If the selected strip doesn't have our ID, assign one.
        if "gmb_id" not in target_strip:
            target_strip["gmb_id"] = uuid.uuid4().hex
        # Store the stable UUID in our actual data property
        self.linked_strip_uuid = target_strip["gmb_id"]
    else:
        # The strip name was not found (e.g. user cleared the field)
        self.linked_strip_uuid = ""


def get_ui_strip_name(self):
    """
    This function is called by Blender whenever the ui_strip_name property is accessed.
    It returns the name of the strip that is linked to this input link.
    """
    if self.linked_strip_uuid:
        strip = get_strip_by_uuid(self.linked_strip_uuid)
        if strip:
            return strip.name
    return ""


def get_gmb_strip_properties_from_id(context, gmb_id):
    """Finds a GMB_StripProperties instance by its unique ID."""
    if not gmb_id:
        return None
    for props in context.scene.gmb_strip_properties:
        if props.id == gmb_id:
            return props
    return None


def get_gmb_config_from_strip_properties(context, strip_props):
    """Finds the full GMB_GeneratorConfig based on the name stored in a strip's properties."""
    if not strip_props or not strip_props.generator_name:
        return None
    
    prefs = context.preferences.addons[__package__].preferences
    for config in prefs.generators:
        if config.name == strip_props.generator_name:
            return config
    return None


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

    # Populate the 'input' properties from the GeneratorConfig object
    if parsed_data.properties and parsed_data.properties.input:
        for prop_data in parsed_data.properties.input:
            item = self.inputs.add()
            item.name = prop_data.name
            item.type = prop_data.type.upper()
            item.pass_via = prop_data.pass_via.upper()
            item.required = prop_data.required

    # Populate the 'output' properties from the GeneratorConfig object
    if parsed_data.properties and parsed_data.properties.output:
        for prop_data in parsed_data.properties.output:
            item = self.outputs.add()
            item.name = prop_data.name
            item.type = prop_data.type.upper()
            item.pass_via = prop_data.pass_via.upper()
            item.file_ext = prop_data.file_ext or ""
            item.required = prop_data.required


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


class GMB_InputLink(PropertyGroup):
    """A property group to link an input property to a VSE strip."""
    name: StringProperty(name="Name")
    linked_strip_uuid: StringProperty(name="Linked Strip UUID")
    
    # This property is for the UI only (to display the search_prop UI element) and does not store the persistent link.
    ui_strip_name: StringProperty(
        name="Strip",
        description="Select the strip to link as an input",
        get=get_ui_strip_name, # The the latest name of the target strip in case it's name changed
        set=set_ui_strip_name, # Set the ui_strip_name when the user selects a strip
    )


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
    # A collection of links to the strips used as inputs
    linked_inputs: CollectionProperty(type=GMB_InputLink)

    # --- Runtime Properties ---
    process_uuid: StringProperty(
        name="Process UUID",
        description="A unique identifier for the running generative process."
    )
    
    status: EnumProperty(
        name="Status",
        items=[
            ('READY', "Ready", "Ready to start the process."),
            ('RUNNING', "Running", "The generative process is running."),
            ('FINISHED', "Finished", "The generative process has finished successfully."),
            ('ERROR', "Error", "An error occurred during the process."),
        ],
        default='READY'
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
    GMB_InputLink,
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