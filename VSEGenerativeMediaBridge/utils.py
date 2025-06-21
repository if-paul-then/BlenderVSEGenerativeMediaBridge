import bpy

def get_strip_by_uuid(uuid_to_find: str):
    """Find a VSE strip by its 'gmb_id' custom property."""
    if not uuid_to_find:
        return None
    # Use sequences_all to include meta strips
    for strip in bpy.context.scene.sequence_editor.sequences_all:
        if strip.get("gmb_id") == uuid_to_find:
            return strip
    return None 