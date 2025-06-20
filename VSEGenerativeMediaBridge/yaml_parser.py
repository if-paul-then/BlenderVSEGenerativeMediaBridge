from .dependencies import yaml

def parse_yaml_config(yaml_string: str):
    """
    Safely parse a YAML string.

    Args:
        yaml_string: The string containing the YAML configuration.

    Returns:
        A dictionary representing the parsed YAML, or None if parsing fails.
    """
    if not yaml_string:
        return None
        
    try:
        data = yaml.safe_load(yaml_string)
        if isinstance(data, dict):
            return data
        else:
            # The YAML is valid but not a dictionary (e.g., just a string or list)
            return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return None 