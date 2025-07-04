import bpy
import uuid
import os
import subprocess
import queue
import threading
import re
import shlex
import tempfile
import shutil
from bpy.types import Operator
from bpy.props import StringProperty
from .utils import (
    get_gmb_type_from_strip, 
    get_strip_by_uuid,
    get_stable_filepath,
    cleanup_gmb_id_version,
    get_addon_placeholder_filepath,
    resolve_strip_filepath,
    get_prefs
)
from .properties import (
    get_gmb_strip_properties_from_id, 
    get_gmb_config_from_strip_properties,
    parse_yaml_config,
    GMB_LogEntry
)

class GMB_OT_add_generator_strip(Operator):
    """Add a new generator strip to the timeline."""
    bl_idname = "gmb.add_generator_strip"
    bl_label = "Add Generator Strip"
    bl_options = {'REGISTER', 'UNDO'}

    generator_name: StringProperty(
        name="Generator Name",
        description="The name of the generator to add."
    )
    
    _temp_files = []

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
        new_strip = None
        sequences = scene.sequence_editor.sequences
        channel = 1 # TODO: Find first empty channel
        frame_start = scene.frame_current
        
        # Decide what kind of strip to create based on the number of outputs
        if gen_config and len(gen_config.outputs) == 1:
            output_prop = gen_config.outputs[0]
            gmb_type = output_prop.type
            
            # This is a single-output strip. Create a stable placeholder for it.
            if gmb_type == 'TEXT':
                new_strip = sequences.new_effect(
                    name=self.generator_name,
                    type='TEXT',
                    channel=channel,
                    frame_start=frame_start,
                    frame_end=frame_start + 100
                )
            elif gmb_type in ['IMAGE', 'SOUND', 'MOVIE']:
                try:
                    # Generate a unique ID for the strip's data first
                    gmb_id = uuid.uuid4().hex
                    
                    # Create the data block for this strip immediately
                    gmb_properties = scene.gmb_strip_properties.add()
                    gmb_properties.id = gmb_id
                    
                    # Get the final destination path for the placeholder
                    stable_path = get_stable_filepath(
                        self.generator_name,
                        gen_config.name,
                        output_prop.name,
                        gmb_id,
                        output_prop.file_ext
                    )

                    # Get the path to the addon's premade placeholder
                    source_placeholder = get_addon_placeholder_filepath(gmb_type)
                    if not source_placeholder or not os.path.exists(source_placeholder):
                        raise FileNotFoundError(f"Premade placeholder for type {gmb_type} not found.")

                    # Copy the premade placeholder to the stable location
                    shutil.copy(source_placeholder, stable_path)
                    
                    # Now create the strip pointing to the stable placeholder
                    if gmb_type == 'IMAGE':
                        new_strip = sequences.new_image(name=self.generator_name, filepath=stable_path, channel=channel, frame_start=frame_start)
                        # new_strip.frame_final_duration = 100
                    elif gmb_type == 'SOUND':
                        new_strip = sequences.new_sound(name=self.generator_name, filepath=stable_path, channel=channel, frame_start=frame_start)
                        # new_strip.frame_final_duration = 100
                    elif gmb_type == 'MOVIE':
                        new_strip = sequences.new_movie(name=self.generator_name, filepath=stable_path, channel=channel, frame_start=frame_start)
                        # new_strip.frame_final_duration = 100
                    
                    # We have to manually assign the gmb_id here since we needed it for the filename
                    new_strip["gmb_id"] = gmb_id
                        
                except (ValueError, FileNotFoundError) as e:
                    self.report({'ERROR'}, f"Failed to create stable placeholder: {e}")
                    return {'CANCELLED'}
            else:
                 self.report({'ERROR'}, f"Unknown output type for single output: {gmb_type}")
                 return {'CANCELLED'}

        # Default to an Adjustment strip if it's not a recognized single output,
        # or if there are multiple/zero outputs.
        if not new_strip:
            new_strip = sequences.new_effect(
                name=self.generator_name,
                type='ADJUSTMENT',
                channel=channel,
                frame_start=frame_start,
                frame_end=frame_start + 100
            )
        
        # --- Property & Data Linking ---
        # If the strip already has a gmb_id (from the single-output case), we just need to link the name.
        # Otherwise, create new props and link the id.
        if "gmb_id" in new_strip:
             gmb_id = new_strip.get("gmb_id")
             gmb_properties = get_gmb_strip_properties_from_id(context, gmb_id)
        else:
            gmb_properties = scene.gmb_strip_properties.add()
            gmb_properties.id = uuid.uuid4().hex
            # Link the VSE strip to our property group using the generated UUID
            new_strip["gmb_id"] = gmb_properties.id

        gmb_properties.generator_name = self.generator_name
        
        # Pre-populate the input link slots based on the generator's config
        if gen_config:
            for input_prop in gen_config.inputs:
                link = gmb_properties.linked_inputs.add()
                link.name = input_prop.name
                # If we found a match during pre-selection, set the UUID
                if input_prop.name in matched_uuids:
                    link.linked_strip_uuid = matched_uuids[input_prop.name]

        return {'FINISHED'}

class GMB_OT_cancel_generation(Operator):
    """Request cancellation of the running generative script."""
    bl_idname = "gmb.cancel_generation"
    bl_label = "Cancel Generation"
    bl_options = {'REGISTER', 'UNDO'}

    strip_id: StringProperty(
        name="Strip ID",
        description="The GMB ID of the strip to cancel."
    )

    def execute(self, context):
        gmb_props = get_gmb_strip_properties_from_id(context, self.strip_id)
        if not gmb_props:
            self.report({'ERROR'}, f"Could not find GMB properties for strip ID: {self.strip_id}")
            return {'CANCELLED'}
        
        if gmb_props.status != 'RUNNING':
            self.report({'WARNING'}, "Process is not running.")
            return {'CANCELLED'}
            
        gmb_props.cancel_requested = True
        self.report({'INFO'}, "Cancellation requested.")
        return {'FINISHED'}

class GMB_OT_generate_media(Operator):
    """Run the generative script for the active GMB strip."""
    bl_idname = "gmb.generate_media"
    bl_label = "Run Generative Script"
    bl_options = {'REGISTER'}

    TIMER_INTERVAL = 0.1
    LOG_HISTORY_LENGTH = 3

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
    _output_temp_files = None
    _parsed_gen_config = None

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
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError as e:
                    print(f"Error removing temporary file {temp_file}: {e}")
            self._temp_files = None
        
        self._output_temp_files = None
        self._parsed_gen_config = None
        
        # The threads are daemons, so they should die automatically.
        self._stdout_thread = None
        self._queue = None
        self._stderr_thread = None
        self._stderr_queue = None
        
        if self._strip_props:
            if self._strip_props.status == 'RUNNING':
                self._strip_props.status = 'ERROR' # Assume error if cleaned up while running
            self._strip_props.runtime_seconds = 0.0 # Reset timer
            self._strip_props.cancel_requested = False # Reset flag
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
            self._parsed_gen_config = parse_yaml_config(yaml_string)
            if not self._parsed_gen_config:
                raise ValueError("Parsed YAML is empty or invalid.")
        except (FileNotFoundError, Exception) as e:
            self.report({'ERROR'}, f"Could not read or parse config file: {e}")
            self._strip_props.status = 'ERROR'
            self._cleanup(context)
            return {'CANCELLED'}

        # --- Build Command ---
        self._temp_files = []
        self._output_temp_files = {}
        try:
            command_list = self._build_command(self._parsed_gen_config)
        except ValueError as e:
            self.report({'ERROR'}, f"Failed to build command: {e}")
            print(f"Failed to build command: {e}")
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
        self._strip_props.runtime_seconds = 0.0 # Reset timer
        self._strip_props.log_history.clear() # Clear log on new run
        self._strip_props.cancel_requested = False # Ensure flag is reset
        
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
        self._timer = context.window_manager.event_timer_add(self.TIMER_INTERVAL, window=context.window)
        context.window_manager.modal_handler_add(self)
        
        context.area.tag_redraw()
        print(f"Started generative script for strip '{self._strip_props.generator_name}'")
        return {'RUNNING_MODAL'}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        """The modal loop for checking the process."""
        if event.type in {'RIGHTMOUSE', 'ESC'} or (self._strip_props and self._strip_props.cancel_requested):
            self.report({'INFO'}, "Cancelled script execution.")
            self._cleanup(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            # --- Update runtime and check for timeout ---
            if self._strip_props.status == 'RUNNING':
                self._strip_props.runtime_seconds += self.TIMER_INTERVAL
                context.area.tag_redraw() # Force UI update for timer text

                # Get timeout value. Priority: YAML > Addon Prefs. 0 means no timeout.
                prefs = get_prefs(context)
                timeout_val = self._parsed_gen_config.command.timeout
                if timeout_val is None:
                    timeout_val = prefs.global_timeout
                
                if timeout_val and timeout_val > 0 and self._strip_props.runtime_seconds > timeout_val:
                    self.report({'ERROR'}, f"Process timed out after {timeout_val} seconds.")
                    self._cleanup(context)
                    return {'FINISHED'}

            def add_to_log(log_line):
                if not log_line:
                    return
                new_entry = self._strip_props.log_history.add()
                new_entry.line = log_line
                # Trim the log history
                while len(self._strip_props.log_history) > self.LOG_HISTORY_LENGTH:
                    self._strip_props.log_history.remove(0)

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
                        add_to_log(stripped_line)

            # --- Check for real-time output from the stderr queue ---
            while True:
                try:
                    line = self._stderr_queue.get_nowait()
                except queue.Empty:
                    break # No more lines in the queue.
                else:
                    # We got a line from stderr. Many tools use this for progress/info.
                    # We will log it without treating it as a Blender error unless the process fails.
                    stripped_line = line.strip()
                    if stripped_line:
                        print(f"GMB-STDERR: {stripped_line}") # More accurate for console
                        add_to_log(stripped_line)
            
            # --- Check if the process has finished ---
            if self._process.poll() is not None:
                return_code = self._process.wait()
                if return_code == 0:
                    self.report({'INFO'}, f"Script finished successfully.")
                    self._strip_props.status = 'FINISHED'
                    self._populate_outputs(context)
                else:
                    error_summary = f"Script failed with exit code {return_code}. See log for details."
                    self.report({'ERROR'}, error_summary)
                    self._strip_props.status = 'ERROR'
                
                self._cleanup(context)
                return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def _build_command(self, gen_config):
        """Builds the command list from the generator config and linked strips."""
        program = gen_config.command.program
        arguments = gen_config.command.arguments
        argument_list = gen_config.command.argument_list

        arg_item_list = []
        if arguments is not None:
            # The dataclass validation ensures 'arguments' and 'argument_list' are mutually exclusive.
            # An empty string for arguments is valid, so we check for None.
            arg_item_list = [{'argument': arg, 'if_property_set': None} for arg in shlex.split(arguments)]
        elif argument_list:
            arg_item_list = [{'argument': arg.argument, 'if_property_set': arg.if_property_set} for arg in argument_list]
        
        # Create maps for faster lookup
        output_defs = {odef.name: odef for odef in gen_config.properties.output}
        input_defs = {idef.name: idef for idef in gen_config.properties.input}

        resolved_args = []

        for arg_item in arg_item_list:
            # Handle conditional arguments based on 'if_property_set'
            if_prop_set_name = arg_item.get('if_property_set')
            if if_prop_set_name:
                # This argument is conditional. Check if the corresponding input property is linked to a strip.
                input_link = next((link for link in self._strip_props.linked_inputs if link.name == if_prop_set_name), None)
                
                # An input is considered "set" if a strip has been linked to it.
                is_set = input_link and input_link.linked_strip_uuid
                
                if not is_set:
                    # The property is not set, so we skip this argument entirely.
                    continue

            current_arg = arg_item['argument']
            # Find all placeholders like {PlaceholderName} in the current argument
            placeholders = re.findall(r'\{(.*?)\}', current_arg)

            for placeholder in placeholders:
                value = None
                
                # Is it an output placeholder?
                if placeholder in output_defs:
                    output_def = output_defs[placeholder]
                    if output_def.pass_via.lower() == 'file':
                        # Generate a unique path in the system's temp directory
                        # without creating the file itself.
                        temp_dir = tempfile.gettempdir()
                        unique_filename = f"{uuid.uuid4()}{output_def.file_ext or '.tmp'}"
                        value = os.path.join(temp_dir, unique_filename)
                        
                        self._output_temp_files[placeholder] = value
                        self._temp_files.append(value) # for global cleanup
                    else:
                        # For now, we only support 'file' for outputs.
                        raise ValueError(f"Output '{placeholder}' has unsupported 'pass-via' method: {output_def.pass_via}")

                # Is it an input placeholder?
                elif placeholder in input_defs:
                    input_def = input_defs[placeholder]
                    input_link = next((link for link in self._strip_props.linked_inputs if link.name == placeholder), None)
                    
                    if not input_link or not input_link.linked_strip_uuid:
                        # If not linked, check for a default value.
                        if input_def.default_value is not None:
                            value = input_def.default_value
                        elif input_def.required:
                            # This should have been caught by the UI poll function, but as a safeguard:
                            raise ValueError(f"Required input '{placeholder}' is not linked and has no default value.")
                        else:
                            # Optional, not linked, no default value. Replace with empty string.
                            value = ""
                    else:
                        # It's linked, so get the value from the strip.
                        linked_strip = get_strip_by_uuid(input_link.linked_strip_uuid)
                        if not linked_strip:
                            raise ValueError(f"Could not find strip for input '{placeholder}' (UUID: {input_link.linked_strip_uuid}).")
                        
                        value = self._get_input_value(linked_strip, input_def, input_link)
                else:
                    raise ValueError(f"Placeholder '{{{placeholder}}}' does not match any defined input or output property.")

                if value is not None:
                    # Replace the placeholder with the actual value.
                    current_arg = current_arg.replace(f'{{{placeholder}}}', str(value))
            
            resolved_args.append(current_arg)

        final_command_list = [program] + resolved_args
        print(f"Executing command: {final_command_list}")
        return final_command_list

    def _get_input_value(self, linked_strip, input_def, input_link):
        """
        Extracts the required value for an input property based on its configured mode.
        (e.g., from a strip, a file, or direct text).
        """
        value = None
        mode = input_link.input_mode

        # --- Get value based on the selected mode ---
        if mode == 'STRIP':
            if not linked_strip:
                raise ValueError(f"Input '{input_def.name}' is set to 'STRIP' mode but no strip is linked.")
            
            strip_type = linked_strip.type
            if strip_type == 'TEXT':
                value = linked_strip.text
            elif strip_type == 'IMAGE' and linked_strip.elements:
                value = resolve_strip_filepath(linked_strip.elements[0].filename)
            elif strip_type == 'SOUND':
                value = resolve_strip_filepath(linked_strip.sound.filepath)
            elif strip_type == 'MOVIE':
                value = resolve_strip_filepath(linked_strip.filepath)
            else:
                raise ValueError(f"Unsupported strip type '{strip_type}' for input '{input_def.name}'.")

        elif mode == 'FILE':
            if not input_link.filepath:
                raise ValueError(f"Input '{input_def.name}' is set to 'FILE' mode but no file is selected.")
            value = resolve_strip_filepath(input_link.filepath)

        elif mode == 'TEXT':
            if input_def.type.upper() != 'TEXT':
                raise ValueError(f"Input '{input_def.name}' has type '{input_def.type}' which is incompatible with 'TEXT' mode.")
            value = input_link.text_value
        
        # --- Handle pass-via mechanism for the retrieved value ---
        # This is mostly for creating temp files for text values when needed.
        if input_def.pass_via.lower() == 'file' and (mode == 'TEXT' or (mode == 'STRIP' and linked_strip.type == 'TEXT')):
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as temp_f:
                temp_f.write(value)
                value = temp_f.name
                self._temp_files.append(value)
        elif input_def.pass_via.lower() == 'text' and mode != 'TEXT' and (mode != 'STRIP' or linked_strip.type != 'TEXT'):
             raise ValueError(f"'pass-via: text' is only valid for Text inputs, not for file paths or non-text strips.")

        if value is None:
            raise ValueError(f"Could not get value for input '{input_def.name}'.")
            
        return value

    def _populate_outputs(self, context):
        """
        After a successful generation, create or populate the output strips
        with the generated media.
        """
        if not self._parsed_gen_config or not self._output_temp_files:
            self.report({'ERROR'}, "Missing config or temp files for output population.")
            return

        outputs = self._parsed_gen_config.properties.output
        
        # --- SINGLE OUTPUT CASE ---
        if len(outputs) == 1:
            controller_strip = get_strip_by_uuid(self.strip_id)
            if not controller_strip:
                self.report({'ERROR'}, f"Could not find controller strip with ID {self.strip_id}")
                return
            
            output_def = outputs[0]
            temp_filepath = self._output_temp_files.get(output_def.name)
            if not temp_filepath:
                self.report({'ERROR'}, f"Could not find temp file for output '{output_def.name}'")
                return

            self._populate_strip_from_file(controller_strip, output_def, temp_filepath)

        # --- MULTI-OUTPUT CASE ---
        elif len(outputs) > 1:
            controller_strip = get_strip_by_uuid(self.strip_id)
            if not controller_strip:
                self.report({'ERROR'}, f"Could not find controller strip with ID {self.strip_id}")
                return

            for output_def in outputs:
                temp_filepath = self._output_temp_files.get(output_def.name)
                if not temp_filepath:
                    self.report({'WARNING'}, f"Could not find temp file for output '{output_def.name}'")
                    continue

                # Create and populate a new strip
                new_strip = self._create_and_populate_output_strip(context, controller_strip, output_def, temp_filepath)
                if not new_strip:
                    self.report({'ERROR'}, f"Failed to create strip for output '{output_def.name}'")
                    continue
                    
                # Link it to the controller strip's properties
                link = self._strip_props.linked_outputs.add()
                link.name = output_def.name
                link.linked_strip_uuid = new_strip["gmb_id"]

    def _create_and_populate_output_strip(self, context, controller_strip, output_def, temp_filepath):
        """Creates and populates a new strip from a file."""
        sequences = context.scene.sequence_editor.sequences
        gmb_type = output_def.type.upper()
        strip_name = output_def.name
        channel = controller_strip.channel + 1  # Place above the controller
        frame_start = int(controller_strip.frame_start)
        new_strip = None
        strip_gmb_id = uuid.uuid4().hex
                
        if gmb_type == 'TEXT':
            new_strip = sequences.new_effect(name=strip_name, type='TEXT', channel=channel, frame_start=frame_start, frame_end=frame_start + 100)
            try:
                # For text, we don't need a stable file, just read the temp file content.
                with open(temp_filepath, 'r', encoding='utf-8') as f:
                    new_strip.text = f.read()
            except Exception as e:
                self.report({'ERROR'}, f"Failed to read text output file: {e}")
                return None
        elif gmb_type in ['IMAGE', 'SOUND', 'MOVIE']:
            try:
                stable_filepath = get_stable_filepath(
                    strip_name,
                    self._parsed_gen_config.name,
                    output_def.name,
                    strip_gmb_id,
                    output_def.file_ext
                )
                shutil.move(temp_filepath, stable_filepath)
            except (ValueError, FileNotFoundError, OSError) as e:
                self.report({'ERROR'}, f"Could not move generated file to stable location: {e}")
                return None

            if gmb_type == 'IMAGE':
                new_strip = sequences.new_image(name=strip_name, filepath=stable_filepath, channel=channel, frame_start=frame_start)
                # new_strip.frame_final_duration = 100
            elif gmb_type == 'SOUND':
                new_strip = sequences.new_sound(name=strip_name, filepath=stable_filepath, channel=channel, frame_start=frame_start)
                # new_strip.frame_final_duration = 100
            elif gmb_type == 'MOVIE':
                new_strip = sequences.new_movie(name=strip_name, filepath=stable_filepath, channel=channel, frame_start=frame_start)
                # new_strip.frame_final_duration = 100

        new_strip["gmb_id"] = strip_gmb_id
        return new_strip

    def _populate_strip_from_file(self, strip, output_def, temp_filepath):
        """Updates a strip's content from a generated file."""
        gmb_type = output_def.type.upper()
        strip_name = strip.name
        strip_gmb_id = strip["gmb_id"]

        if gmb_type == 'TEXT':
            try:
                # Text is just updated in place, no file moves needed.
                with open(temp_filepath, 'r', encoding='utf-8') as f:
                    strip.text = f.read()
            except Exception as e:
                self.report({'ERROR'}, f"Failed to read text output file: {e}")
        elif gmb_type in ['IMAGE', 'SOUND', 'MOVIE']:
            try:
                # Get the directory where the stable file should be.
                stable_filepath = get_stable_filepath(
                    strip_name,
                    self._parsed_gen_config.name,
                    output_def.name,
                    strip_gmb_id,
                    output_def.file_ext
                )
                stable_dir = os.path.dirname(stable_filepath)

                # Clean up any previous versions of this file (e.g., the placeholder)
                cleanup_gmb_id_version(stable_dir, strip_gmb_id)
                
                # Move the new temp file to the stable location
                shutil.move(temp_filepath, stable_filepath)

                # Update the strip to point to the new file
                if gmb_type == 'IMAGE':
                    strip.filepath = stable_filepath
                elif gmb_type == 'SOUND':
                    strip.sound.filepath = stable_filepath
                elif gmb_type == 'MOVIE':
                    strip.filepath = stable_filepath
            except (ValueError, FileNotFoundError, OSError) as e:
                self.report({'ERROR'}, f"Could not populate strip with stable file: {e}")

def register():
    bpy.utils.register_class(GMB_OT_add_generator_strip)
    bpy.utils.register_class(GMB_OT_cancel_generation)
    bpy.utils.register_class(GMB_OT_generate_media)


def unregister():
    bpy.utils.unregister_class(GMB_OT_add_generator_strip)
    bpy.utils.unregister_class(GMB_OT_cancel_generation)
    bpy.utils.unregister_class(GMB_OT_generate_media) 