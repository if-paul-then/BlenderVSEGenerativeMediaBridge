# VSE Generative Media Bridge

The VSE Generative Media Bridge is a Blender addon that connects the Video Sequence Editor (VSE) with external tools, integrating them directly into your video editing workflow.

## The Problem
Often, the media you need for a project can't be created within Blender alone. But using external tools breaks your workflow, forcing you to switch contexts and manually copy-paste media.

For some external tools it's straightforward to call a command-line tool or script to generate an image, sound, or video — you provide inputs and receive media outputs.
For example, to create a watermarked video using ffmpeg you need an input video and watermark image:
```
ffmpeg -y -i "{Base Video}" -i "{Watermark Image}" -filter_complex "overlay=W-w-10:H-h-10" "{Output Video}"
```
However, to call the same command from within Blender, you need to create an addon that specifies operators, properties, UI elements, and more. This adds unnecessary complexity when all you want to do is call a command.

## The Solution
The VSE Generative Media Bridge addon takes a simple definition of the external tool command you want to call and dynamically creates the Blender UI elements and logic for calling the command.

For example, the previous ffmpeg command can be declaratively specified as:
```
name: Video Watermark
command:
  program: ffmpeg
  arguments: -y -i "{Base Video}" -i "{Watermark Image}" -filter_complex "overlay=W-w-10:H-h-10" "{Output Video}"
properties:
  input:
    - name: Base Video
      type: movie
      pass-via: file
    - name: Watermark Image
      type: image
      pass-via: file
  output:
    - name: Output Video
      type: movie
      pass-via: file
      file-ext: .mp4
```
With this definition, a **Video Watermark** option becomes available in the **Add > Generative Media** menu:
![Add Menu](https://github.com/if-paul-then/BlenderVSEGenerativeMediaBridge/raw/main/docs/images/README/AddMenu.png)

The addon also provides side panel input properties and a Generate button to run the command and capture the generated media:
![Side Panel](https://github.com/if-paul-then/BlenderVSEGenerativeMediaBridge/raw/main/docs/images/README/SidePanelUI.png)

This addon works by letting you define "Generators" using simple YAML configuration files. These generators appear in the VSE's "Add" menu, allowing you to add them as special strips to your timeline. From the VSE sidebar, you can provide inputs (by linking to other strips, selecting files, or entering text) and then execute the tool to generate media that is automatically brought back into your project.

## Features

-   **Extensible:** Integrate any command-line tool by creating a simple YAML configuration file.
-   **Dynamic UI:** The addon's side panel dynamically creates UI elements based on your YAML configuration.
-   **Flexible Inputs:** Provide inputs by linking to existing VSE strips, selecting files from your computer, or entering text directly.
-   **Non-Blocking:** External tools run in the background, keeping Blender's UI responsive. You can cancel a running process at any time.
-   **Multi-Output:** Generators can produce single or multiple outputs, which are automatically added to the VSE.

## Installation

This addon is packaged as a Blender Extension and can be obtained in two ways:

### Option 1: Download from GitHub Releases (Recommended)

1.  **Download the Addon:**
    -   Go to the [Releases page](../../releases) of this GitHub repository.
    -   Download the latest `.zip` file (e.g., `vse_generative_media_bridge-1.0.0.zip`).

2.  **Install in Blender:**
    -   Open Blender (version 4.2 or newer is recommended).
    -   Navigate to `Edit > Preferences > Add-ons`.
    -   Click the **Install...** button.
    -   Select the downloaded `.zip` file.
    -   Find "VSE Generative Media Bridge" in the add-on list and enable it by checking the box.

### Option 2: Build from Source

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
For a detailed guide on all available options, see the [YAML Configuration File Format](docs/yaml_format.md) documentation.

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