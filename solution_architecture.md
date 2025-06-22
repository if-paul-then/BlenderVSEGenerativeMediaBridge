# Solution Architecture: VSE Generative Media Bridge

This document outlines the proposed software architecture for the VSE Generative Media Bridge addon for Blender 4.x.

## 1. Overview

The addon will be structured around Blender's standard Python API components: `AddonPreferences`, `PropertyGroup`, `Operator`, and `Panel`. The core idea is to manage a list of "Generator" configurations in the addon's preferences. When a user adds a "Generator Strip" to the VSE, this strip is linked to one of these configurations. A dedicated panel in the VSE sidebar will display the properties of the selected generator strip, allowing the user to link other strips as inputs and trigger the generation process.

The generation itself will be handled by a modal operator to avoid locking up Blender's UI, providing a non-blocking user experience with the ability to cancel the operation.

## 2. Core Components

The addon will be organized into the following key components:

### 2.1. Data Model & Properties (`properties.py`)

- **`GMB_GeneratorConfig(bpy.types.PropertyGroup)`**: Represents a single generator configuration. It will contain properties to store the parsed YAML data, such as `name`, `program`, `arguments`, and collections for input/output properties. A `StringProperty` will hold the raw YAML text for editing.
- **`GMB_AddonPreferences(bpy.types.AddonPreferences)`**: The main preferences class for the addon. It will feature a `CollectionProperty` of `GMB_GeneratorConfig` to manage the list of all available generators.
- **`GMB_StripProperties(bpy.types.PropertyGroup)`**: Represents the custom data for a single generator strip. To avoid modifying Blender's protected `Sequence` type directly, a collection of these `PropertyGroup` instances will be stored at the scene level (`bpy.types.Scene.gmb_strip_properties`). Each VSE strip created by the addon will be linked to an entry in this collection via a unique ID. It will store:
    - A `StringProperty` for the `id`, a unique UUID to stably link this data block to a VSE strip.
    - A `StringProperty` to link to the `name` of the `GMB_GeneratorConfig` it was created from.
    - A `CollectionProperty` of `GMB_InputLink` to hold the links to VSE strips used as inputs.
- **`GMB_InputLink(bpy.types.PropertyGroup)`**: A helper data block to manage the relationship between a generator strip and one of its input strips. Since `PointerProperty` cannot be used with `bpy.types.Sequence`, this provides a robust, name-change-proof alternative. It contains:
    - `name`: The name of the input property from the generator's config.
    - `linked_strip_uuid`: A `StringProperty` that stores the unique ID of the linked input strip. This is the persistent link.
    - `ui_strip_name`: A "virtual" `StringProperty` used only for the UI. It uses `get` and `set` functions to translate between the strip's name (shown to the user) and its underlying UUID (used for storage).

### 2.2. Operators (`operators.py`)

- **`GMB_OT_add_generator_strip(bpy.types.Operator)`**:
    - This operator will be responsible for adding a new generator strip to the VSE timeline.
    - It will be invoked from the `VSE > Add` menu.
    - Based on the selected generator's output properties (as defined in `requirements.md`), it will create the appropriate strip type (e.g., `Image`, 
    `Sound`, `Text`, or an `EffectStrip` as a controller) and then:
        1.  Generate a new unique ID (`uuid.uuid4()`).
        2.  Store this UUID in a custom property on the VSE strip itself (e.g., `the_strip["gmb_uuid"] = ...`).
        3.  Create a new entry in the scene's `gmb_strip_properties` collection.
        4.  Set the `id` and `generator_name` on this new property group entry, establishing the link.
- **`GMB_OT_generate_media(bpy.types.Operator)`**:
    - This will be a modal operator (`'RUNNING_MODAL'`) to handle the media generation process asynchronously.
    - When invoked by the "Generate" button, it will:
        1. Find the active strip's UUID from its custom property.
        2. Use the UUID to find the corresponding `GMB_StripProperties` entry in the scene collection.
        3. Read the generator configuration from that property group.
        4. Construct the full command-line arguments.
        5. Launch the external program using Python's `subprocess.Popen`.

### 2.3. User Interface (`ui.py`)

- **`GMB_PT_addon_preferences(bpy.types.Panel)`**: A panel within the Addon Preferences window to manage generators. It will use a `UIList` to display the list of `GMB_GeneratorConfig` instances, with buttons to add, remove, and edit them.
- **`GMB_PT_vse_sidebar(bpy.types.Panel)`**: A panel in the VSE's sidebar (`UI` region).
    - It will only be visible when the active strip is a generator strip (i.e., its `gmb_id` custom property is set).
    - It will display the generator's name and dynamically draw properties for each defined input.
    - For input properties, it will use a `prop_search` UI element, pointing to the virtual `ui_strip_name` property, which gives the user a searchable dropdown of all strips in the sequence.
    - It will display the "Generate" button, which will be disabled until all required properties are set.

### 2.4. Utilities (`utils.py` and `yaml_parser.py`)

- **YAML Parsing**: A dedicated module (`yaml_parser.py`) will handle parsing the YAML configuration string into a structured Python object that maps to the `GMB_GeneratorConfig` `PropertyGroup`. We will need to bundle the `PyYAML` library with the addon.
- **Helper Functions (`utils.py`)**: Utility functions for tasks like finding a VSE strip by its custom UUID, managing temporary files for generation, and identifying strip types.

## 3. Workflow Diagram

```mermaid
graph TD
    subgraph "Addon Preferences"
        A[User defines Generator A<br/>(e.g., Text-to-Speech)] --> B{Addon stores config};
    end

    subgraph "VSE"
        C[User selects 'Generator A'<br/>from Add menu] --> D[GMB_OT_add_generator_strip];
        D --> E[New Sound Strip created];
        E --> F[Strip properties linked<br/>to Generator A config];
    end

    subgraph "VSE Side Panel"
        G[User selects the new Sound Strip] --> H[GMB_PT_vse_sidebar appears];
        H --> I{User sets 'Prompt' text};
        I --> J[User clicks 'Generate'];
    end

    subgraph "Background Process"
        J --> K[GMB_OT_generate_media starts];
        K --> L["subprocess.Popen('tts.exe --text \"Hello\"...')"];
        L -- ".wav file" --> M[Operator updates Sound Strip's filepath];
    end

    M --> N[User sees generated audio in VSE];

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#f9f,stroke:#333,stroke-width:2px
    style L fill:#ccf,stroke:#333,stroke-width:2px
    style M fill:#ccf,stroke:#333,stroke-width:2px
```

## 4. Key Decisions & Considerations

- **Targeting Blender 4**: The architecture relies on standard, stable APIs that are fully supported in Blender 4.0 and later.
- **Dependency Management**: To avoid conflicts with other addons, the `PyYAML` library will be "vendored". It will be placed into a `dependencies` sub-folder within the addon package. All imports of the library from within our addon's code will use relative imports (e.g., `from .dependencies import yaml`). This makes the library private to our addon and prevents any clashes with other versions of PyYAML that may be present in Blender's Python environment.
- **State Management**: Storing generator configurations in `AddonPreferences` makes them available globally across all `.blend` files. Strip-specific data is stored directly on the strips themselves, ensuring it's saved with the project.
- **Modularity**: The separation of concerns (data, operators, UI) into different files will make the codebase easier to maintain and extend. 