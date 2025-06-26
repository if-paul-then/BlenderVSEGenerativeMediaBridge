import bpy
import uuid
import os
import subprocess
import queue
import threading
import re
import shlex
import tempfile
from bpy.types import Operator
from bpy.props import StringProperty
from .utils import get_gmb_type_from_strip, get_strip_by_uuid
from .properties import (
    get_gmb_strip_properties_from_id, 
    get_gmb_config_from_strip_properties,
    parse_yaml_config
)

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
        prefs = get_prefs(context)
        gen_config = next((g for g in prefs.generators if g.name == self.generator_name), None)
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

class GMB_OT_generate_media(Operator):
    """Run the generative script for the active GMB strip."""
    bl_idname = "gmb.generate_media"
    bl_label = "Run Generative Script"
    bl_options = {'REGISTER'}

    strip_id: StringProperty(
        name="Strip ID",
        description="The GMB ID of the strip to run the script for."
    )

    _timer = None
    _process = None
    _strip_props = None
    _queue = None
    _stdout_thread = None
    _stderr_queue = None
    _stderr_thread = None
    _temp_files = None

    def _enqueue_output(self, stream, q):
        """Read lines from a stream and put them in a queue."""
        try:
            for line in iter(stream.readline, ''):
                q.put(line)
        finally:
            stream.close()

    @classmethod
    def poll(cls, context):
        # For now, always allow running. We can add checks later.
        return context.area.type == 'SEQUENCE_EDITOR'

    def _get_strip_properties(self, context: bpy.types.Context):
        """Find the GMB_StripProperties for the given strip_id."""
        return get_gmb_strip_properties_from_id(context, self.strip_id)

    def _cleanup(self, context: bpy.types.Context):
        """Remove the timer and kill the process."""
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if self._process:
            if self._process.poll() is None: # If the process is still running
                self._process.kill()
            self._process = None
        
        # Clean up temporary files
        if self._temp_files:
            for temp_file in self._temp_files:
                try:
                    os.remove(temp_file)
                    print(f"Removed temporary file: {temp_file}")
                except OSError as e:
                    print(f"Error removing temporary file {temp_file}: {e}")
            self._temp_files = None
        
        # The threads are daemons, so they should die automatically.
        self._stdout_thread = None
        self._queue = None
        self._stderr_thread = None
        self._stderr_queue = None
        
        if self._strip_props:
            if self._strip_props.status == 'RUNNING':
                self._strip_props.status = 'ERROR' # Assume error if cleaned up while running
            self._strip_props = None
        context.area.tag_redraw()

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        """Start the script and enter the modal loop."""
        self._strip_props = self._get_strip_properties(context)
        if not self._strip_props:
            self.report({'ERROR'}, f"Could not find GMB properties for strip ID: {self.strip_id}")
            return {'CANCELLED'}
        
        if self._strip_props.status == 'RUNNING':
            self.report({'WARNING'}, "Script is already running for this strip.")
            return {'CANCELLED'}

        gmb_generator_config = get_gmb_config_from_strip_properties(context, self._strip_props)
        if not gmb_generator_config:
            self.report({'ERROR'}, f"Could not find generator config '{self._strip_props.generator_name}'")
            self._strip_props.status = 'ERROR'
            return {'CANCELLED'}

        if not gmb_generator_config.config_filepath:
            self.report({'ERROR'}, f"Generator '{gmb_generator_config.name}' has no config file set.")
            self._strip_props.status = 'ERROR'
            return {'CANCELLED'}

        try:
            with open(gmb_generator_config.config_filepath, 'r') as f:
                yaml_string = f.read()
            parsed_gen_config = parse_yaml_config(yaml_string)
            if not parsed_gen_config:
                raise ValueError("Parsed YAML is empty or invalid.")
        except (FileNotFoundError, Exception) as e:
            self.report({'ERROR'}, f"Could not read or parse config file: {e}")
            self._strip_props.status = 'ERROR'
            return {'CANCELLED'}

        # --- Build Command ---
        self._temp_files = []
        try:
            command_list = self._build_command(parsed_gen_config)
        except ValueError as e:
            self.report({'ERROR'}, f"Failed to build command: {e}")
            self._strip_props.status = 'ERROR'
            self._cleanup(context)
            return {'CANCELLED'}
        
        try:
            # We create separate pipes for stdout and stderr to handle them independently.
            self._process = subprocess.Popen(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
        except (OSError, subprocess.SubprocessError) as err:
            self.report({'ERROR'}, f"Failed to start script: {err}")
            print(f"Failed to start script: {command_list}, Error: {err}")
            self._strip_props.status = 'ERROR'
            return {'CANCELLED'}

        self._strip_props.status = 'RUNNING'
        self._strip_props.process_uuid = uuid.uuid4().hex
        
        # Create queues and threads to read stdout and stderr in a non-blocking way.
        self._queue = queue.Queue()
        self._stdout_thread = threading.Thread(
            target=self._enqueue_output,
            args=(self._process.stdout, self._queue)
        )
        self._stdout_thread.daemon = True # Thread dies with the main program.
        self._stdout_thread.start()
        
        self._stderr_queue = queue.Queue()
        self._stderr_thread = threading.Thread(
            target=self._enqueue_output,
            args=(self._process.stderr, self._stderr_queue)
        )
        self._stderr_thread.daemon = True
        self._stderr_thread.start()
        
        # Add a timer to check the process status periodically
        self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
        context.window_manager.modal_handler_add(self)
        
        context.area.tag_redraw()
        print(f"Started generative script for strip '{self._strip_props.generator_name}'")
        return {'RUNNING_MODAL'}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        """The modal loop for checking the process."""
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.report({'INFO'}, "Cancelled script execution.")
            self._cleanup(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            # --- Check for real-time output from the stdout queue ---
            while True:
                try:
                    line = self._queue.get_nowait()
                except queue.Empty:
                    break # No more lines in the queue.
                else:
                    # We got a line, print it and report it.
                    stripped_line = line.strip()
                    if stripped_line:
                        print(f"GMB Log: {stripped_line}")
                        self.report({'INFO'}, stripped_line)

            # --- Check for real-time output from the stderr queue ---
            while True:
                try:
                    line = self._stderr_queue.get_nowait()
                except queue.Empty:
                    break # No more lines in the queue.
                else:
                    # We got an error line, print it and report it as an error.
                    stripped_line = line.strip()
                    if stripped_line:
                        print(f"GMB-ERROR: {stripped_line}")
                        self.report({'ERROR'}, f"Error: {stripped_line}")
            
            # --- Check if the process has finished ---
            if self._process.poll() is not None:
                return_code = self._process.wait()
                if return_code == 0:
                    self.report({'INFO'}, f"Script finished successfully.")
                    self._strip_props.status = 'DONE'
                else:
                    self.report({'ERROR'}, f"Script failed with exit code {return_code}.")
                    self._strip_props.status = 'ERROR'
                
                self._cleanup(context)
                return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _build_command(self, gen_config):
        """Builds the command list from the generator config and linked strips."""
        program = gen_config.command.program
        arguments_template = gen_config.command.arguments or ""
        
        # Find all placeholders like {PlaceholderName}
        placeholders = re.findall(r'\{(.*?)\}', arguments_template)
        
        resolved_args = arguments_template
        
        for placeholder in placeholders:
            # Find the linked strip for this placeholder
            input_link = next((link for link in self._strip_props.linked_inputs if link.name == placeholder), None)
            if not input_link or not input_link.linked_strip_uuid:
                raise ValueError(f"Input '{placeholder}' is not linked.")

            linked_strip = get_strip_by_uuid(input_link.linked_strip_uuid)
            if not linked_strip:
                raise ValueError(f"Could not find strip for input '{placeholder}' (UUID: {input_link.linked_strip_uuid}).")

            # Find the input definition in the generator's config to know how to handle it
            input_def = next((idef for idef in gen_config.properties.input if idef.name == placeholder), None)
            if not input_def:
                raise ValueError(f"Could not find input definition for '{placeholder}' in generator config.")

            # Get the value from the strip based on its type and pass-via method
            value = self._get_strip_value(linked_strip, input_def)
            
            # Replace the placeholder with the actual value
            resolved_args = resolved_args.replace(f'{{{placeholder}}}', str(value))
            
        final_command_list = [program] + shlex.split(resolved_args)
        print(f"Executing command: {final_command_list}")
        return final_command_list

    def _get_strip_value(self, strip, input_def):
        """Extracts the required value from a strip based on the input definition."""
        value = None
        strip_type = strip.type
        
        # Get the raw value first
        if strip_type == 'TEXT':
            value = strip.text
        elif strip_type == 'IMAGE' and strip.elements:
            value = bpy.path.abspath(strip.elements[0].filename)
        elif strip_type == 'SOUND':
            value = bpy.path.abspath(strip.sound.filepath)
        elif strip_type == 'MOVIE':
            value = bpy.path.abspath(strip.filepath)
        else:
            raise ValueError(f"Unsupported strip type '{strip_type}' for input '{input_def.name}'.")

        # Handle pass-via mechanism
        if input_def.pass_via.lower() == 'file' and strip_type == 'TEXT':
            # Write the text content to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as temp_f:
                temp_f.write(value)
                value = temp_f.name
                self._temp_files.append(value)
        elif input_def.pass_via.lower() == 'text' and strip_type != 'TEXT':
            raise ValueError(f"'pass-via: text' is only valid for Text strips, not '{strip_type}'.")

        if value is None:
            raise ValueError(f"Could not get value for input '{input_def.name}' from strip '{strip.name}'.")
            
        return value

def register():
    bpy.utils.register_class(GMB_OT_add_generator)
    bpy.utils.register_class(GMB_OT_remove_generator)
    bpy.utils.register_class(GMB_OT_add_generator_strip)
    bpy.utils.register_class(GMB_OT_generate_media)


def unregister():
    bpy.utils.unregister_class(GMB_OT_add_generator)
    bpy.utils.unregister_class(GMB_OT_remove_generator)
    bpy.utils.unregister_class(GMB_OT_add_generator_strip)
    bpy.utils.unregister_class(GMB_OT_generate_media) 