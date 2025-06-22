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
        return 'VIDEO'
    elif strip_type == 'SOUND':
        return 'AUDIO'
    elif strip_type == 'TEXT':
        return 'TEXT'
    # EffectStrips and others don't have a direct media type
    return None 