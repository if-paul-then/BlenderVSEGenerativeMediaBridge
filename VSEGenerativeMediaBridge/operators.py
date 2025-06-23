import bpy
import uuid
import os
import subprocess
import queue
import threading
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
        for props in context.scene.gmb_strip_properties:
            if props.id == self.strip_id:
                return props
        return None

    def _cleanup(self, context: bpy.types.Context):
        """Remove the timer and kill the process."""
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if self._process:
            if self._process.poll() is None: # If the process is still running
                self._process.kill()
            self._process = None
        
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

        # The 'timeout' command is a standard Windows utility to wait for a few seconds.
        command = "timeout /t 5 /nobreak"
        
        try:
            # We create separate pipes for stdout and stderr to handle them independently.
            self._process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        except (OSError, subprocess.SubprocessError) as err:
            self.report({'ERROR'}, f"Failed to start script: {err}")
            print(f"Failed to start script: {err}")
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
                        print(f"GMB-OUTPUT: {stripped_line}")
                        self.report({'INFO'}, f"Output: {stripped_line}")

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
            if self._process and self._process.poll() is not None:
                # Process has finished, the thread will die on its own.
                if self._process.returncode == 0:
                    print("Script finished successfully.")
                    self._strip_props.status = 'FINISHED'
                else:
                    print(f"Script finished with error (code {self._process.returncode}).")
                    self._strip_props.status = 'ERROR'
                
                self._cleanup(context)
                return {'FINISHED'}

        return {'PASS_THROUGH'}

classes = (
    GMB_OT_add_generator,
    GMB_OT_remove_generator,
    GMB_OT_add_generator_strip,
    GMB_OT_generate_media,
)

def register():
    """Register the operator classes."""
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    """Unregister the operator classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls) 