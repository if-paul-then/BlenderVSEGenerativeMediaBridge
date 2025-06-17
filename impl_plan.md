# Implementation Plan: VSE Generative Media Bridge

This document outlines a phased implementation plan for the VSE Generative Media Bridge addon. Each milestone delivers a deployable and testable version of the addon with an incrementally larger feature set.

## [ ] Milestone 1a: Basic Addon Skeleton

- **Goal:** Create a minimal, installable Blender addon with the correct directory structure.
- **Deliverable:** An addon that can be installed and enabled/disabled in Blender. It will have no functionality but will establish the foundational file structure.
- **Key Tasks:**
    1.  **Project Setup:** Create the addon's root directory (`VSEGenerativeMediaBridge/`).
    2.  **`__init__.py`:** Create the main `__init__.py` file.
    3.  **`bl_info`:** Add the `bl_info` dictionary to `__init__.py`.
    4.  **Registration:** Add empty `register()` and `unregister()` functions.

## [ ] Milestone 1b: Generator Data Structure

- **Goal:** Define the data structures for storing generator configurations within Blender.
- **Deliverable:** The addon will have the internal data model for generators registered with Blender. It will still be installable, but no UI will exist yet to modify the data.
- **Key Tasks:**
    1.  **`properties.py`:** Create the `properties.py` file.
    2.  **`GMB_GeneratorConfig`:** Define a `PropertyGroup` with `name: StringProperty` and `yaml_config: StringProperty`.
    3.  **`GMB_AddonPreferences`:** Define an `AddonPreferences` class containing a `CollectionProperty` of the new generator config group.
    4.  **Registration:** Import and register these classes in `__init__.py`.

## [ ] Milestone 1c: Preferences UI Panel & Generator List

- **Goal:** Create the UI in the addon preferences to display the list of generators.
- **Deliverable:** A user can go to the addon preferences and see a (currently empty) list for generators. When an item is selected, its properties (name, YAML config) will be displayed. The add/remove buttons will not be functional yet.
- **Key Tasks:**
    1.  **`ui.py`:** Create the `ui.py` file.
    2.  **`GMB_UL_Generators`:** Create a `UIList` class to display the generator items.
    3.  **`GMB_PT_addon_preferences`:** Create a `Panel` class for the preferences.
    4.  **Draw Panel:** In the panel's `draw()` method, use `template_list()` to render the `UIList` and also draw the properties of the active item from the list.
    5.  **Registration:** Import and register these UI classes in `__init__.py`.

## [ ] Milestone 1d: Add/Remove Operators

- **Goal:** Implement the logic to add new generators to the list and remove existing ones.
- **Deliverable:** The `+` (Add) and `-` (Remove) buttons in the preferences panel will be fully functional, allowing a user to manage their list of generators.
- **Key Tasks:**
    1.  **`operators.py`:** Create the `operators.py` file.
    2.  **Add Operator:** Create an `Operator` that adds a new, blank item to the generator `CollectionProperty`.
    3.  **Remove Operator:** Create an `Operator` that removes the currently selected item from the `CollectionProperty`.
    4.  **Connect UI:** Add the operator buttons to the preferences `Panel` in `ui.py`.
    5.  **Registration:** Import and register the new operator classes in `__init__.py`.

## [ ] Milestone 1e: Vendoring Dependency

- **Goal:** Prepare the addon for using the `PyYAML` library without conflicting with other addons.
- **Deliverable:** The addon will contain the necessary folder structure to hold the `PyYAML` dependency.
- **Key Tasks:**
    1.  **`dependencies/` folder:** Create the `dependencies` sub-folder.
    2.  **Package Init:** Add an empty `__init__.py` inside `dependencies` to mark it as a Python package.

## [ ] Milestone 2: Basic VSE Integration & YAML Parsing

- **Goal:** Bridge the gap between the preferences and the VSE by adding a "Generator Strip" to the timeline that is linked to a configuration.
- **Deliverable:** From the `VSE > Add` menu, a user can select a generator defined in Milestone 1. This action will add a new `EffectStrip` to the timeline. A basic side panel will appear when this strip is selected, confirming the name of the generator it's linked to.
- **Key Tasks:**
    1.  **YAML Parser:** Create `yaml_parser.py`. Implement a function that takes the YAML string and safely parses it using the vendored `PyYAML` library (e.g., `from .dependencies import yaml`). It should handle syntax errors gracefully.
    2.  **Strip Properties:** In `properties.py`, define `GMB_StripProperties(PropertyGroup)`. Add a `StringProperty` to store the name of the linked generator config. Register this property group with `bpy.types.Sequence`.
    3.  **Add Operator:** Create `operators.py`. Implement `GMB_OT_add_generator_strip(Operator)`. This operator will be responsible for creating a new strip and setting its `GMB_StripProperties`.
    4.  **Menu Integration:** Update `ui.py` to dynamically create a sub-menu in the `VSE_MT_add` menu, populating it with the available generators.
    5.  **Side Panel:** In `ui.py`, create `GMB_PT_vse_sidebar(Panel)`. Its `draw()` method will check if the active strip is a generator strip and display the generator's name.

## [ ] Milestone 3: Dynamic Side Panel & Input Linking

- **Goal:** Make the VSE side panel fully dynamic, displaying properties based on the parsed YAML and allowing users to link other strips as inputs.
- **Deliverable:** The side panel will now show a UI element for each `input` property defined in the generator's YAML. Users will be able to use these properties to select other strips in the timeline (e.g., a `Text` strip for a `{Prompt}` input).
- **Key Tasks:**
    1.  **Data Model Expansion:**
        - Enhance `GMB_GeneratorConfig` to store the *parsed* configuration (lists of input and output properties).
        - Enhance `GMB_StripProperties` with a `CollectionProperty` containing `PointerProperty(type=bpy.types.Sequence)` to hold references to the input strips.
    2.  **Dynamic UI:** The `GMB_PT_vse_sidebar` `draw()` method will be rewritten to:
        - Look up the full, parsed config for the active strip's generator.
        - Loop through the parsed `input` properties and draw a corresponding `PointerProperty` from the strip's collection for each one.
    3.  **Pre-selection:** Implement the logic in `GMB_OT_add_generator_strip` to automatically populate input properties from pre-selected strips, as per the requirements.

## [ ] Milestone 4: Asynchronous Generation Operator

- **Goal:** Implement the core media generation logic using a non-blocking modal operator.
- **Deliverable:** The "Generate" button in the side panel will be functional. Clicking it will execute the configured command-line program in the background. The Blender UI will remain responsive, and the user will see a status indicator (e.g., in the header) and be able to cancel the operation by pressing `ESC`.
- **Key Tasks:**
    1.  **Utilities:** Create `utils.py` for helper functions, especially for managing temporary file paths for media passed by file.
    2.  **Modal Operator:** In `operators.py`, implement `GMB_OT_generate_media(Operator)` as a modal operator.
        - `invoke()`: Prepare the command-line arguments, replacing placeholders with actual values, and launch the external process using `subprocess.Popen`.
        - `modal()`: Periodically check the status of the subprocess. Handle timer events for updates and keyboard events for cancellation. Update the UI to show the "busy" state.
    3.  **Error Handling:** If the subprocess returns a non-zero exit code, capture `stderr` and report a clear, concise error to the user via the Blender UI.

## [ ] Milestone 5: Output Handling & Final Polish

- **Goal:** Process the media created by the external tool and correctly update or create the necessary VSE strips.
- **Deliverable:** A feature-complete addon. After a successful generation, the addon will replace placeholder strips or update output strips with the new media. For example, a generated `.png` will appear in an `ImageStrip`, and a `.wav` in a `SoundStrip`.
- **Key Tasks:**
    1.  **Strip Creation Logic:** Enhance `GMB_OT_add_generator_strip` to create the correct final strip type (or a placeholder if necessary) based on the YAML `output` definitions.
    2.  **Output Processing:** In `GMB_OT_generate_media`, upon successful completion of the subprocess, implement the logic to:
        - Locate the generated file(s).
        - Update the `filepath`, `text` content, or other relevant properties of the output VSE strip(s).
    3.  **UI Polish:**
        - Implement the "required" property logic to enable/disable the "Generate" button.
        - Add visual cues in the UI to indicate which properties are required.
    4.  **Testing & Documentation:** Conduct thorough end-to-end testing of various generator configurations. Create a `README.md` with installation and usage instructions. 