# VSE Generative Media Bridge
# Copyright (C) 2024 Paul Siegfried
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import bpy
import os
import shutil

def get_prefs(context):
    """Get the addon preferences."""
    return context.preferences.addons[__package__].preferences

def get_strip_by_uuid(uuid_to_find: str):
    """Find a VSE strip by its 'gmb_id' custom property."""
    if not uuid_to_find:
        return None
    # Use sequences_all to include meta strips
    for strip in bpy.context.scene.sequence_editor.sequences_all:
        if strip.get("gmb_id") == uuid_to_find:
            return strip
    return None

def get_gmb_type_from_strip(strip):
    """
    Determines the GMB media type ('IMAGE', 'VIDEO', 'AUDIO', 'TEXT') from a VSE strip.
    """
    if not strip:
        return None

    strip_type = strip.type
    if strip_type == 'IMAGE':
        return 'IMAGE'
    elif strip_type == 'MOVIE':
        return 'MOVIE'
    elif strip_type == 'SOUND':
        return 'SOUND'
    elif strip_type == 'TEXT':
        return 'TEXT'
    # EffectStrips and others don't have a direct media type
    return None

def get_stable_filepath(strip_name, generator_name, output_name, gmb_id, file_ext):
    """
    Constructs a stable, unique filepath for a generated media file next to the .blend file.
    Example: //MyProject_vse_gmb/MyStrip_MyGenerator_OutputName_gmb_id.png
    """
    # This check is crucial. We can't form a relative path without a saved .blend file.
    if not bpy.data.is_saved:
        raise ValueError("Project must be saved to generate media to a stable location.")

    blend_filepath = bpy.data.filepath
    blend_dir = os.path.dirname(blend_filepath)
    
    # Create a unique directory name based on the .blend file's name
    blend_filename = os.path.basename(blend_filepath)
    blend_name, _ = os.path.splitext(blend_filename)
    output_dir_name = f"{blend_name}_vse_gmb"
    output_dir = os.path.join(blend_dir, output_dir_name)
    
    # Create the directory if it doesn't exist.
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a name for the output file based on all available info, ensuring uniqueness.
    output_strip_name = f"{strip_name}_{generator_name}_{output_name}_{gmb_id}"
    safe_filename = bpy.path.clean_name(output_strip_name) + file_ext
    
    # Return the full, absolute path for file operations.
    return os.path.join(output_dir, safe_filename)

def cleanup_gmb_id_version(directory, gmb_id_to_remove):
    """
    Removes any file from the target directory that contains the gmb_id as a substring.
    This is used to clean up old versions of generated media before creating a new one.
    """
    if not os.path.isdir(directory):
        return

    for filename in os.listdir(directory):
        if gmb_id_to_remove in filename:
            try:
                os.remove(os.path.join(directory, filename))
                print(f"GMB Cleanup: Removed old version '{filename}'")
            except OSError as e:
                print(f"GMB Cleanup Error: Could not remove file '{filename}': {e}")
                
                
def get_addon_placeholder_filepath(gmb_type):
    """
    Gets the absolute path to the premade placeholder file for a given media type.
    """
    addon_dir = os.path.dirname(__file__)
    placeholder_dir = os.path.join(addon_dir, "placeholders")

    if gmb_type == 'IMAGE':
        return os.path.join(placeholder_dir, "placeholder.png")
    elif gmb_type == 'SOUND':
        return os.path.join(placeholder_dir, "placeholder.wav")
    elif gmb_type == 'MOVIE':
        return os.path.join(placeholder_dir, "placeholder.mp4")
    else:
        return None

def resolve_strip_filepath(filepath):
    """
    Resolves a filepath from a strip, handling Blender's relative paths ('//')
    and paths relative to the blend file directory.
    """
    if not filepath:
        return ""

    # First, let Blender try to resolve it. This handles '//' paths correctly.
    abs_path = bpy.path.abspath(filepath)

    # If it's still not absolute, it might be a filename relative to the .blend file.
    if not os.path.isabs(abs_path):
        if bpy.data.is_saved:
            blend_dir = os.path.dirname(bpy.data.filepath)
            abs_path = os.path.join(blend_dir, abs_path)
        else:
            # We cannot resolve it without a saved blend file.
            # The calling code should handle this error.
            raise ValueError(f"Cannot resolve relative path '{filepath}' for an unsaved project.")
    
    return abs_path 