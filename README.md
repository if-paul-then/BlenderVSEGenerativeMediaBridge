# VSE Generative Media Bridge

The VSE Generative Media Bridge is a Blender addon that connects the Video Sequence Editor (VSE) with external, command-line generative tools. It allows you to integrate any CLI-based tool (like AI image generators, text-to-speech engines, etc.) directly into your video editing workflow.

This addon works by letting you define "Generators" using simple YAML configuration files. These generators appear in the VSE's "Add" menu, allowing you to add them as special strips to your timeline. From the VSE sidebar, you can provide inputs (by linking to other strips, selecting files, or entering text) and then execute the tool to generate media that is automatically brought back into your project.

## Features

-   **Extensible:** Integrate any command-line tool by creating a simple YAML configuration file.
-   **Dynamic UI:** The addon's side panel dynamically creates UI elements based on your YAML configuration.
-   **Flexible Inputs:** Provide inputs by linking to existing VSE strips, selecting files from your computer, or entering text directly.
-   **Non-Blocking:** External tools run in the background, keeping Blender's UI responsive. You can cancel a running process at any time.
-   **Multi-Output:** Generators can produce single or multiple outputs, which are automatically added to the VSE.

## Installation

This addon is packaged as a Blender Extension.

1.  **Build the Addon:**
    -   Ensure you have Blender installed (version 4.2 or newer is recommended).
    -   Open the `package_addon.sh` script in a text editor and update the `BLENDER_EXE` variable to point to your Blender executable.
    -   Run the script from your terminal: `./package_addon.sh`.
    -   This will validate the addon and, if successful, create a zip file (e.g., `vse_generative_media_bridge-1.0.0.zip`) in your project directory.

2.  **Install in Blender:**
    -   Open Blender.
    -   Navigate to `Edit > Preferences > Add-ons`.
    -   Click the **Install...** button.
    -   Select the `.zip` file you created in the previous step.
    -   Find "VSE Generative Media Bridge" in the add-on list and enable it by checking the box.

## Usage

Using the addon involves three main steps: configuring a generator, creating a YAML file for it, and using it in the VSE.

### 1. Configure a Generator

First, you need to tell the addon about your generator.

1.  Go to `Edit > Preferences > Add-ons` and find the "VSE Generative Media Bridge" addon.
2.  Expand the preferences panel for the addon.
3.  Click the **`+`** button to add a new generator slot.
4.  Click the folder icon next to the "Config File" field and select the YAML configuration file for your generator (see next section for how to create one).
5.  The "Name" and "Description" fields will be automatically populated from the YAML file.

### 2. Create a Generator YAML File

The YAML file is the core of a generator. It defines the command to run, its inputs, and its outputs.

Here is an example YAML file for a mock text-to-image generator:

**`text-to-image.yaml`**
```yaml
name: "Text to Image"
description: "Generates an image from a text prompt using a mock script."
program: "python"
arguments: "test/dalle_mini_mock.py --text \"{text}\" --image-file \"{image}\""
timeout: 30
inputs:
  - name: "text"
    type: "text"
    pass-via: "text"
    required: true
outputs:
  - name: "image"
    type: "image"
    pass-via: "file"
    file-ext: ".png"
    required: true
```

**Key Fields:**
-   `name` & `description`: Displayed in the UI.
-   `program`: The main program to execute (e.g., `python`, `ffmpeg`, `C:\my_tool.exe`).
-   `arguments`: A string of command-line arguments. Placeholders like `{text}` and `{image}` will be replaced with actual values at runtime.
-   `timeout`: Maximum time in seconds to wait for the command to finish.
-   `inputs`: A list of inputs the tool needs.
    -   `name`: The name of the input, used for placeholders.
    -   `type`: The type of data (`text`, `image`, `sound`, `movie`).
    -   `pass-via`: How the data is passed. `text` passes the content directly on the command line, while `file` passes a path to a temporary file.
    -   `required`: If `true`, the "Generate" button will be disabled until this input is provided.
-   `outputs`: A list of outputs the tool will generate.
    -   The addon will provide a temporary file path for each output placeholder. Your script should write its result to that path.

### 3. Use the Generator in the VSE

1.  Open the **Video Sequence Editor**.
2.  Go to `Add > Generative Media` and select the generator you configured (e.g., "Text to Image").
3.  A new strip will be added to the timeline. If the generator has a single output, the strip will be of that type (e.g., an Image strip). Otherwise, a generic "Controller" strip is created.
4.  Select the new strip and open the sidebar (press the `N` key).
5.  Go to the "Generative Media" tab. Here you will see the UI for the inputs you defined in your YAML.
6.  Provide the inputs. For each input, you can choose a mode:
    -   **STRIP:** Link to another VSE strip.
    -   **FILE:** Select a file from your computer.
    -   **TEXT:** (Only for `text` type inputs) Enter the text directly.
7.  Once all required inputs are provided, the **Generate** button will become active. Click it to run the external tool.
8.  The UI will show a "Cancel" button while the process is running.
9.  When the tool finishes, the output strip(s) will be automatically populated with the generated media. 