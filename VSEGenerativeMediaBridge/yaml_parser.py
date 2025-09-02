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

from dataclasses import dataclass, field, is_dataclass, fields
from typing import List, Optional, Dict, Any


@dataclass
class Argument:
    """Represents a single command line argument."""
    argument: str
    if_property_set: Optional[str] = field(default=None, metadata={'key': 'if-property-set'})

@dataclass
class CommandConfig:
    """Configuration for the external command to be executed."""
    program: str
    arguments: Optional[str] = None
    argument_list: List[Argument] = field(default_factory=list, metadata={'key': 'argument-list'})
    timeout: Optional[int] = None

    def __post_init__(self):
        if self.arguments and self.argument_list:
            raise ValueError("'arguments' and 'argument_list' are mutually exclusive.")

@dataclass
class InputProperty:
    """Represents an input property for the generator."""
    name: str
    type: str
    pass_via: Optional[str] = field(default=None, metadata={'key': 'pass-via'})
    required: Optional[bool] = None
    default_value: Optional[str] = field(default=None, metadata={'key': 'default-value'})

    def __post_init__(self):
        VALID_TYPES = ["text", "image", "sound", "movie"]
        if self.type.lower() not in VALID_TYPES:
            raise ValueError(f"For property '{self.name}', invalid type '{self.type}'. Must be one of {VALID_TYPES}")

        if self.required is None:
            self.required = self.default_value is None

        if self.pass_via is None:
            self.pass_via = "text" if self.type == "text" else "file"
        
        if self.type in ["image", "sound", "movie"] and self.pass_via not in ["file", "stream"]:
            raise ValueError(f"For input '{self.name}', invalid 'pass-via' for type '{self.type}': {self.pass_via}")
        if self.type == "text" and self.pass_via not in ["file", "stream", "text"]:
            raise ValueError(f"For input '{self.name}', invalid 'pass-via' for type 'text': {self.pass_via}")

@dataclass
class OutputProperty:
    """Represents an output property for the generator."""
    name: str
    type: str
    pass_via: str = field(default="file", metadata={'key': 'pass-via'})
    file_ext: Optional[str] = field(default=None, metadata={'key': 'file-ext'})
    required: bool = True
    
    def __post_init__(self):
        VALID_TYPES = ["text", "image", "sound", "movie"]
        if self.type.lower() not in VALID_TYPES:
            raise ValueError(f"For property '{self.name}', invalid type '{self.type}'. Must be one of {VALID_TYPES}")
            
        if self.pass_via not in ["file", "stream"]:
            raise ValueError(f"For output '{self.name}', invalid 'pass-via': {self.pass_via}")

@dataclass
class PropertiesConfig:
    """Container for input and output properties."""
    input: List[InputProperty] = field(default_factory=list)
    output: List[OutputProperty] = field(default_factory=list)

@dataclass
class GeneratorConfig:
    """Root configuration for a generator."""
    name: str
    command: CommandConfig
    properties: PropertiesConfig
    description: Optional[str] = None

def _from_dict(cls, data: Dict[str, Any]):
    """Recursively constructs a dataclass instance from a dictionary."""
    if not isinstance(data, dict):
        return data

    kwargs = {}
    for f in fields(cls):
        # Map kebab-case from YAML to snake_case in dataclass
        field_key = f.metadata.get('key', f.name)
        
        if field_key in data:
            field_value = data[field_key]
            # Recursively call _from_dict for nested dataclasses
            if is_dataclass(f.type):
                kwargs[f.name] = _from_dict(f.type, field_value)
            # Handle lists of dataclasses
            elif hasattr(f.type, '__origin__') and f.type.__origin__ == list and is_dataclass(f.type.__args__[0]):
                item_cls = f.type.__args__[0]
                kwargs[f.name] = [_from_dict(item_cls, item) for item in field_value]
            else:
                kwargs[f.name] = field_value
    
    return cls(**kwargs)

# Alias fields for use in the helper function
field_iter = fields

def parse_yaml_config(yaml_string: str) -> Optional[GeneratorConfig]:
    """
    Safely parse a YAML string and return a GeneratorConfig object.

    Args:
        yaml_string: The string containing the YAML configuration.

    Returns:
        A GeneratorConfig object, or None if parsing or validation fails.
    """
    if not yaml_string:
        return None
        
    try:
        # Import dynamically to avoid static import linter errors in environments
        # where StrictYAML isn't installed at analysis time.
        from importlib import import_module
        yaml_mod = import_module('strictyaml')

        # Define a schema to ensure correct typing (e.g., Bool/Int) rather than strings
        Map = yaml_mod.Map
        Seq = yaml_mod.Seq
        Str = yaml_mod.Str
        Int = yaml_mod.Int
        Bool = yaml_mod.Bool
        OptionalKey = yaml_mod.Optional

        schema = Map({
            "name": Str(),
            OptionalKey("description"): Str(),
            "command": Map({
                "program": Str(),
                OptionalKey("arguments"): Str(),
                OptionalKey("argument-list"): Seq(Map({
                    "argument": Str(),
                    OptionalKey("if-property-set"): Str(),
                })),
                OptionalKey("timeout"): Int(),
            }),
            "properties": Map({
                "input": Seq(Map({
                    "name": Str(),
                    "type": Str(),
                    OptionalKey("pass-via"): Str(),
                    OptionalKey("required"): Bool(),
                    OptionalKey("default-value"): Str(),
                })),
                "output": Seq(Map({
                    "name": Str(),
                    "type": Str(),
                    OptionalKey("pass-via"): Str(),
                    OptionalKey("file-ext"): Str(),
                    OptionalKey("required"): Bool(),
                })),
            }),
        })

        data = yaml_mod.load(yaml_string, schema).data
        if not isinstance(data, dict):
            print(f"Error: YAML root must be a dictionary, but got {type(data)}")
            return None

        return _from_dict(GeneratorConfig, data)

    except Exception as e:
        # Catches YAML errors, dataclass constructor errors, and validation errors from __post_init__
        print(f"Error parsing or validating YAML config: {e}")
        return None 