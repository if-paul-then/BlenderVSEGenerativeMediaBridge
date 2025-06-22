# Implementation Plan: VSE Generative Media Bridge

This document outlines a phased implementation plan for the VSE Generative Media Bridge addon. Each milestone delivers a deployable and testable version of the addon with an incrementally larger feature set.

## [x] Milestone 1a: Basic Addon Skeleton

- **Goal:** Create a minimal, installable Blender addon with the correct directory structure.
- **Deliverable:** An addon that can be installed and enabled/disabled in Blender. It will have no functionality but will establish the foundational file structure.
- **Key Tasks:**
    1.  **Project Setup:** Create the addon's root directory (`VSEGenerativeMediaBridge/`).
    2.  **`__init__.py`:** Create the main `__init__.py` file.
    3.  **`bl_info`:** Add the `bl_info` dictionary to `__init__.py`.
    4.  **Registration:** Add empty `register()` and `unregister()` functions.
- **Testable Outcome:**
    1.  Zip the `VSEGenerativeMediaBridge` folder.
    2.  In Blender, navigate to `Edit > Preferences > Add-ons` and click `Install...`.
    3.  Select the zipped file. The addon "VSE Generative Media Bridge" should appear in the list.
    4.  You can enable and disable the addon's checkbox without any errors appearing in the system console.

## [x] Milestone 1b: Generator Data Structure

- **Goal:** Define the data structures for storing generator configurations within Blender.
- **Deliverable:** The addon will have the internal data model for generators registered with Blender. It will still be installable, but no UI will exist yet to modify the data.
- **Key Tasks:**
    1.  **`properties.py`:** Create the `properties.py` file.
    2.  **`GMB_GeneratorConfig`:** Define a `PropertyGroup` with `name: StringProperty` and `yaml_config: StringProperty`.
    3.  **`GMB_AddonPreferences`:** Define an `AddonPreferences` class containing a `CollectionProperty` of the new generator config group.
    4.  **Registration:** Import and register these classes in `__init__.py`.
- **Testable Outcome:**
    1.  With the addon enabled, open Blender's Python Console.
    2.  Executing `bpy.context.preferences.addons['VSEGenerativeMediaBridge'].preferences.generators` should run without error and return an empty collection.

## [x] Milestone 1c: Preferences UI Panel & Generator List

- **Goal:** Create the UI in the addon preferences to display the list of generators.
- **Deliverable:** A user can go to the addon preferences and see a (currently empty) list for generators. When an item is selected, its properties (name, YAML config) will be displayed. The add/remove buttons will not be functional yet.
- **Key Tasks:**
    1.  **`ui.py`:** Create the `ui.py` file.
    2.  **`GMB_UL_Generators`:** Create a `UIList` class to display the generator items.
    3.  **`GMB_PT_addon_preferences`:** Create a `Panel` class for the preferences.
    4.  **Draw Panel:** In the panel's `draw()` method, use `template_list()` to render the `UIList` and also draw the properties of the active item from the list.
    5.  **Registration:** Import and register these UI classes in `__init__.py`.
- **Testable Outcome:**
    1.  In the addon preferences, a panel titled "Generators" is visible.
    2.  The panel contains an empty list view. Below it, "Name" and "YAML Config" fields are visible but greyed out.

## [x] Milestone 1d: Add/Remove Operators

- **Goal:** Implement the logic to add new generators to the list and remove existing ones.
- **Deliverable:** The `+` (Add) and `-` (Remove) buttons in the preferences panel will be fully functional, allowing a user to manage their list of generators.
- **Key Tasks:**
    1.  **`operators.py`:** Create the `operators.py` file.
    2.  **Add Operator:** Create an `Operator` that adds a new, blank item to the generator `CollectionProperty`.
    3.  **Remove Operator:** Create an `Operator` that removes the currently selected item from the `CollectionProperty`.
    4.  **Connect UI:** Add the operator buttons to the preferences `Panel` in `ui.py`.
    5.  **Registration:** Import and register the new operator classes in `__init__.py`.
- **Testable Outcome:**
    1.  Clicking the `+` button in the preferences panel adds a new "Generator" item to the list.
    2.  When an item is selected, the "Name" and "YAML Config" fields become editable.
    3.  Clicking the `-` button removes the selected item from the list.
    4.  Changes persist after saving preferences and restarting Blender.

## [x] Milestone 1e: Vendoring Dependency

- **Goal:** Prepare the addon for using the `PyYAML` library without conflicting with other addons.
- **Deliverable:** The addon will contain the necessary folder structure to hold the `PyYAML` dependency.
- **Key Tasks:**
    1.  **`dependencies/` folder:** Create the `dependencies` sub-folder.
    2.  **Package Init:** Add an empty `__init__.py` inside `dependencies` to mark it as a Python package.
- **Testable Outcome:**
    1.  The `VSEGenerativeMediaBridge/dependencies` folder and its `__init__.py` file exist.
    2.  The addon continues to install and run without errors.

## [x] Milestone 2a: Custom Strip Properties

- **Goal:** Create the data structure that will be attached to every VSE strip to hold generator-specific information.
- **Deliverable:** Every strip in the VSE will have a new set of custom properties. This is a purely structural change with no visible UI impact yet.
- **Key Tasks:**
    1.  **`properties.py`:** Define a new `GMB_StripProperties(PropertyGroup)`. It should contain an `id` property for a UUID and a `generator_name` property.
    2.  **Scene Collection:** Create a `CollectionProperty` of `GMB_StripProperties` and attach it to `bpy.types.Scene`. This collection will hold the data for all generator strips in the scene.
- **Testable Outcome:**
    1.  Reload the addon.
    2.  In the Python Console, run `bpy.context.scene.gmb_strip_properties`.
    3.  The command should execute without error and return an empty collection.

## [x] Milestone 2b: Dynamic "Add Generator" Menu

- **Goal:** Create a submenu in the VSE `Add` menu that dynamically lists all configured generators.
- **Deliverable:** A new "Generative Media" option will appear in the VSE `Add` menu, containing a sub-menu item for each generator defined in the addon preferences. Clicking these items will not do anything yet.
- **Key Tasks:**
    1.  **`ui.py`:** Define a new menu drawing function. This function will access the addon preferences, loop through the list of generators, and use `layout.operator()` to create a menu entry for each one.
    2.  **Menu Registration:** Use `bpy.types.VSE_MT_add.append()` in the addon's `register()` function to add the new drawing function to the VSE's Add menu.
- **Testable Outcome:**
    1.  In the addon preferences, create two generators named "Text-to-Image" and "Text-to-Speech".
    2.  In the VSE, click the `Add` menu. A `Generative Media` submenu should be present.
    3.  This submenu should contain two (currently inactive) options: "Text-to-Image" and "Text-to-Speech".

## [x] Milestone 2c: Add Generator Strip Operator

- **Goal:** Implement the operator that creates a new generator strip on the timeline.
- **Deliverable:** Clicking a generator name from the `Add > Generative Media` menu will now add a new `EffectStrip` to the VSE timeline and link it to the selected generator.
- **Key Tasks:**
    1.  **`operators.py`:** Create a new `GMB_OT_add_generator_strip(Operator)`.
    2.  **Operator Property:** Give the operator a `StringProperty` to receive the `generator_name` from the menu.
    3.  **`execute()` Method:** Implement the operator's `execute` method to add a new `EffectStrip` and set its `gmb_properties.generator_name` to the value of the operator's property.
    4.  **Connect Menu:** Update the menu drawing function in `ui.py` so that the menu items correctly call this new operator with the right `generator_name`.
- **Testable Outcome:**
    1.  Clicking `Add > Generative Media > Text-to-Image` adds a new Effect Strip to the timeline.
    2.  Select the new strip. In the Python Console, verify that `bpy.context.scene.sequence_editor.active_strip.gmb_properties.generator_name` equals `"Text-to-Image"`.

## [x] Milestone 2d: VSE Sidebar Panel

- **Goal:** Display context-sensitive information for the generator strips in the VSE side panel.
- **Deliverable:** A new "Generative Media" panel will appear in the VSE sidebar, but only when a generator strip is selected. It will display the name of the linked generator.
- **Key Tasks:**
    1.  **`ui.py`:** Create a new `GMB_PT_vse_sidebar(Panel)`.
    2.  **`poll()` Method:** Implement a class method `poll(cls, context)` that returns `True` only if the `active_strip` has a non-empty `gmb_properties.generator_name`.
    3.  **`draw()` Method:** Implement the panel's `draw` method to display the `generator_name` from the strip's properties.
    4.  **Registration:** Register the new panel class.
- **Testable Outcome:**
    1.  The "Generative Media" panel is not visible when a normal VSE strip is selected.
    2.  When the "Text-to-Image" generator strip is selected, the panel appears in the sidebar and displays "Generator: Text-to-Image".

## [x] Milestone 2e: Vendor PyYAML

- **Goal:** Add the `PyYAML` library to the addon's `dependencies` folder.
- **Deliverable:** The addon package will contain the necessary library code for parsing YAML in later milestones.
- **Key Tasks:**
    1.  **Download PyYAML:** Obtain the `PyYAML` library files.
    2.  **Copy `yaml` Directory:** Place the `yaml` package directory inside the `VSEGenerativeMediaBridge/dependencies/` folder.
- **Testable Outcome:**
    1.  The folder `VSEGenerativeMediaBridge/dependencies/yaml` exists and contains the library's source files.
    2.  The addon continues to load without errors. You can verify the library is accessible by adding `from .dependencies import yaml` to a file like `operators.py` and reloading the addon.

## [x] Milestone 3a: YAML Parsing & Data Model

- **Goal:** Parse the YAML config string and store the structured data.
- **Deliverable:** The addon will parse the YAML config of a selected generator and store the input/output definitions internally. This is a structural change with no immediate UI impact.
- **Key Tasks:**
    1.  **`yaml_parser.py`:** Create this new file. Implement a function that takes a YAML string and returns a structured Python object. It should use the vendored `PyYAML` and include robust error handling for malformed YAML.
    2.  **Data Model:** In `properties.py`, define new `PropertyGroup` classes for `InputProperty`, `OutputProperty`, etc.
    3.  **Extend `GMB_GeneratorConfig`:** Add `CollectionProperty`s for the parsed `inputs` and `outputs` to the `GMB_GeneratorConfig` `PropertyGroup`.
    4.  **Update Hook:** Use a property's `update` function on the raw `yaml_config` `StringProperty` to automatically trigger the parsing logic whenever the text is changed.
- **Testable Outcome:**
    1.  In the addon preferences, create a generator and paste a valid YAML config with one `input` and one `output` property into the text field.
    2.  In the Python Console, access the corresponding `GMB_GeneratorConfig` object from the preferences.
    3.  Verify that `len(the_config.inputs)` is 1 and `the_config.outputs[0].name` matches the name from your YAML.
    4.  Changing the YAML text and leaving the text field should update the parsed data automatically.

## [x] Milestone 3b: Dynamic Side Panel UI

- **Goal:** Dynamically display UI elements in the VSE side panel based on the generator's parsed `input` properties.
- **Deliverable:** The "Generative Media" side panel will now show a label for each `input` property defined in the generator's YAML.
- **Key Tasks:**
    1.  **Helper Function:** Create a helper function to get the full, parsed `GMB_GeneratorConfig` for the active generator strip.
    2.  **`ui.py`:** Update the `GMB_PT_vse_sidebar`'s `draw()` method to:
        - Call the new helper function.
        - Loop through the parsed `inputs` collection on the config object.
        - For each input, draw a `layout.label()` with its name.
- **Testable Outcome:**
    1.  Configure a generator with a YAML file defining two inputs, "Prompt" and "Style Image".
    2.  Add this generator strip to the VSE.
    3.  When selected, the "Generative Media" side panel should display the labels "Prompt" and "Style Image".

## [x] Milestone 3c: Linking Input Properties

- **Goal:** Allow users to link other VSE strips to the input properties on the side panel using a robust, name-change-proof method.
- **Deliverable:** The side panel will show a strip selector for each `input` property. The link will persist even if the linked strip is renamed.
- **Key Tasks:**
    1.  **UUID-based Linking:** Implement a linking system based on custom UUIDs stored on each strip, as `PointerProperty` cannot be used with `bpy.types.Sequence`.
    2.  **`properties.py`:** Define `GMB_InputLink(PropertyGroup)` with:
        - `linked_strip_uuid`: A `StringProperty` to store the permanent ID of the linked strip.
        - `ui_strip_name`: A "virtual" `StringProperty` for the UI. It will have an `update` function to find a strip by its name and store its UUID, and a `get` function to find a strip by its stored UUID and return its current name.
    3.  **Extend `GMB_StripProperties`:** Add a `CollectionProperty` of `GMB_InputLink` to hold the linked input strips for each generator strip.
    4.  **`ui.py`:** Modify the `GMB_PT_vse_sidebar`'s `draw()` method to use `layout.prop_search()` on the `ui_strip_name` property, creating a searchable dropdown of all sequences in the timeline.
- **Testable Outcome:**
    1.  Using a generator with defined inputs, add its strip to the VSE.
    2.  Add a `Text` strip and an `Image` strip to the timeline.
    3.  The "Generative Media" panel shows two strip selector fields. You can assign the `Text` strip and `Image` strip to their respective inputs.
    4.  Rename the `Text` strip in the VSE.
    5.  The link in the side panel remains intact and now displays the new name of the strip.

## [x] Milestone 3d: Pre-selecting Strips on Add

- **Goal:** Automatically link pre-selected strips when a new generator strip is added.
- **Deliverable:** If a user selects compatible strips on the timeline *before* adding a generator strip, the addon will automatically populate the input properties.
- **Key Tasks:**
    1.  **Type Checking:** Create a utility function (`get_gmb_type_from_strip`) to check if a strip's type matches an input property's defined `type` (e.g., text, image).
    2.  **`operators.py`:** Update the `GMB_OT_add_generator_strip` operator's `execute` method to:
        - Before creating the strip, iterate through `context.selected_sequences`.
        - Match the selected strips to the generator's `input` properties based on type and order.
        - After creating the strip and its data properties, populate the input `linked_strip_uuid` properties with the matched strips' UUIDs.
- **Testable Outcome:**
    1.  Create a generator that takes a `text` and an `image` input.
    2.  In the VSE, add a Text strip and an Image strip. Select them both.
    3.  With them selected, use `Add > Generative Media` to add the generator strip.
    4.  Select the new generator strip. The "Prompt" and "Style Image" input fields in the side panel should already be populated with the strips you selected.

## [ ] Milestone 4: Asynchronous Generation Operator

- **Goal:** Implement the core media generation logic using a non-blocking modal operator.
- **Deliverable:** The "Generate" button in the side panel will be functional. Clicking it will execute the configured command-line program in the background. The Blender UI will remain responsive, and the user will see a status indicator (e.g., in the header) and be able to cancel the operation by pressing `ESC`.
- **Key Tasks:**
    1.  **Utilities:** Create `utils.py` for helper functions, especially for managing temporary file paths for media passed by file.
    2.  **Modal Operator:** In `operators.py`, implement `GMB_OT_generate_media(Operator)` as a modal operator.
        - `invoke()`: Prepare the command-line arguments, replacing placeholders with actual values, and launch the external process using `subprocess.Popen`.
        - `modal()`: Periodically check the status of the subprocess. Handle timer events for updates and keyboard events for cancellation. Update the UI to show the "busy" state.
    3.  **Error Handling:** If the subprocess returns a non-zero exit code, capture `stderr` and report a clear, concise error to the user via the Blender UI.
- **Testable Outcome:**
    1.  Configure a generator with a command that sleeps for 5 seconds.
    2.  Clicking "Generate" does not freeze the Blender UI.
    3.  A status message appears in the Blender header (e.g., "Generating...").
    4.  Pressing `ESC` cancels the operation.
    5.  If the command is invalid (e.g., program not found), a user-friendly error is displayed.

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
- **Testable Outcome:**
    1.  Define a generator that creates an output text file. Adding this strip creates a Text strip in the VSE.
    2.  After clicking "Generate", the content of the VSE Text strip is updated with the content of the generated file.
    3.  Define a generator with a required input. The "Generate" button is disabled until that input is assigned a strip. 