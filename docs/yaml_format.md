# YAML Configuration File Format

The VSE Generative Media Bridge uses YAML files to define "Generators." Each YAML file describes a command-line tool, its inputs, and its outputs, allowing Blender to dynamically create a user interface for it.

Here is a comprehensive guide to the format.

## Example

```yaml
name: "Text to Image"
description: "Generates an image from a text prompt using a mock script."
command:
  program: "python"
  arguments: "test/dalle_mini_mock.py --text \"{text}\" --image-file \"{image}\""
  timeout: 30
properties:
  input:
    - name: "text"
      type: "text"
      pass-via: "text"
      required: true
    - name: "another_input"
      type: "image"
      pass-via: "file"
      required: false
      default-value: "path/to/default.png"
  output:
    - name: "image"
      type: "image"
      pass-via: "file"
      file-ext: ".png"
      required: true
```

## Top-Level Fields

These are the main keys in the YAML file.

| Field         | Type   | Required | Description                                                                                             |
|---------------|--------|----------|---------------------------------------------------------------------------------------------------------|
| `name`        | string | Yes      | The name of the generator, displayed in the Blender UI (e.g., in the Add > Generative Media menu).      |
| `description` | string | No       | A short description of what the generator does. This appears as a tooltip in the addon preferences.     |
| `command`     | object | Yes      | An object containing the details of the command-line tool to execute. See [Command Object](#command-object). |
| `properties`  | object | Yes      | An object defining the inputs and outputs for the command. See [Properties Object](#properties-object). |

---

## `command` Object

This object specifies the external program to run and how to run it.

| Field           | Type          | Required | Description                                                                                                                                                                                                     |
|-----------------|---------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `program`       | string        | Yes      | The executable to run (e.g., `python`, `ffmpeg`, `C:\path\to\my_tool.exe`).                                                                                                                                        |
| `arguments`     | string        | Yes*     | A single string of arguments to pass to the program. Placeholders like `{my_input}` will be replaced with values from the `properties` section.                                                                    |
| `argument-list` | list of objects | Yes*     | An alternative to `arguments` for more complex scenarios. It allows sending arguments conditionally. See [Argument List](#argument-list). You must use either `arguments` or `argument-list`, but not both. |
| `timeout`       | integer       | No       | The maximum time in seconds to wait for the command to finish. If the process runs longer, it will be terminated. If not set, a global default from the addon preferences is used.                             |

*\*You must provide either `arguments` or `argument-list`.*

### Tip: Handling Special Characters in Arguments

If your `arguments` string contains special characters that YAML might interpret (like `#` for comments, or extensive quotes), you can use a **literal block scalar** (`|-`) to ensure the string is passed to the command exactly as you've written it.

This is especially useful for complex command-line arguments.

**Example:**
```yaml
command:
  program: curl
  arguments: |-
    -L -o "{output_path}" --data-urlencode "text={text}" --data-urlencode "voice=Adult Male #1, American English"
```

In this example, the `|-` tells YAML to treat the following indented block as a raw string, so the `#` in `Adult Male #1` is not treated as a comment.

### `argument-list`
This provides a more flexible way to define arguments. It is a list of objects, where each object has the following keys:

| Field             | Type   | Required | Description                                                                                             |
|-------------------|--------|----------|---------------------------------------------------------------------------------------------------------|
| `argument`        | string | Yes      | The argument string to pass (e.g., `"--text"` or `"input.jpg"`).                                          |
| `if-property-set` | string | No       | The name of an input property. This argument will only be included if that property has been given a value by the user. |

---

## `properties` Object

This object describes the inputs the tool requires and the outputs it will generate. It contains two keys: `input` and `output`.

### `input`
A list of input properties. Each input is an object with the following keys:

| Field           | Type    | Required | Description                                                                                                                                                           |
|-----------------|---------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name`          | string  | Yes      | The name of the input, used for placeholders in the `arguments` string (e.g., `name: "prompt"` corresponds to `{prompt}`).                                              |
| `type`          | string  | Yes      | The type of data. Valid values are `text`, `image`, `sound`, or `movie`. This determines the kind of UI element shown in Blender.                                        |
| `pass-via`      | string  | No       | How the data is passed to the tool. Valid values depend on the `type`: <ul><li>For `text`: `text` (default, passes content directly), `file` (writes to a temp file and passes the path).</li><li>For `image`, `sound`, `movie`: `file` (default, passes the file path).</li></ul> |
| `required`      | boolean | No       | If `true`, the user must provide this input before the "Generate" button is enabled. Defaults to `true`.                                                              |
| `default-value` | string  | No       | A default value to use if the user does not provide one. For file-based types, this should be a path.                                                                 |

### `output`
A list of output properties. Each output is an object with the following keys:

| Field      | Type    | Required | Description                                                                                                                   |
|------------|---------|----------|-------------------------------------------------------------------------------------------------------------------------------|
| `name`     | string  | Yes      | The name of the output, used for placeholders in the `arguments` string. The addon provides a temporary file path for this placeholder. |
| `type`     | string  | Yes      | The type of media that will be generated. Valid values are `text`, `image`, `sound`, or `movie`.                                 |
| `pass-via` | string  | No       | How the generated media is received. Currently, only `file` (the default) is supported. The tool should write its output to the file path provided by the placeholder. |
| `file-ext` | string  | No       | The file extension for the generated file (e.g., `.png`, `.mp4`). This is important for Blender to correctly interpret the file. |
| `required` | boolean | No       | If `true`, the tool is expected to produce this output. Defaults to `true`.                                                  | 