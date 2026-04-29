# ComfyUI Text Node Plugin

A ComfyUI custom node plugin providing utility nodes for text file saving, image saving, and text file batch loading.

## Nodes

### Save String to Text File
Saves string content to a local text file. Supports single file (append) mode and multiple files mode (split by lines).

### Save Image to Folder
Saves image tensors to a specified folder. Supports custom filenames and multiple image formats (PNG, JPG, JPEG, WebP).

### Load Text Files from Folder
Loads text files from a folder by index. Designed to work with for-loop nodes for batch processing.

## Installation

1. Clone or download this repository into ComfyUI's `custom_nodes` directory:
   ```
   ComfyUI/custom_nodes/Comfyui-txtnode/
   ```
2. Restart ComfyUI
3. Find the nodes under the `Utils` category

## Node Parameters

### Save String to Text File

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| text | STRING | Yes | - | Content to save (multiline supported) |
| file_name | STRING | Yes | output | Base filename |
| extension | STRING | Yes | txt | File extension |
| encoding | ENUM | Yes | utf-8 | utf-8 / gbk / utf-16 / ascii |
| save_mode | ENUM | Yes | single_file | single_file / multiple_files |
| directory_path | STRING | No | ComfyUI/output | Target directory |

**Output**: `file_path` - absolute path to the saved file

### Save Image to Folder

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| images | IMAGE | Yes | - | Image tensor batch |
| file_name | STRING | Yes | - | Filename (leave empty for auto-naming) |
| image_format | ENUM | Yes | png | png / jpg / jpeg / webp |
| output_folder | STRING | No | ComfyUI/output | Target directory |

**Output**: `folder_path` - absolute path to the output folder

### Load Text Files from Folder

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| folder_path | STRING | Yes | ComfyUI/output | Directory containing .txt files |
| max_files | INT | Yes | 10 | Maximum files to consider (1-999) |
| index | INT | Yes | 0 | File index to load (0-based) |

**Output**: `text` - file content, `file_name` - filename

## Usage Examples

### Save Prompts to Individual Files
1. Connect a multiline text input to **Save String to Text File**
2. Set `save_mode` to `multiple_files`
3. Each line will be saved as a separate file

### Batch Process Text Files
1. Use **Save String to Text File** (multiple_files mode) to create files
2. Connect **Load Text Files from Folder** with a for-loop node
3. Set `max_files` to match the number of created files
4. Each loop iteration loads one file's content

### Save Generated Images with Custom Names
1. Connect image output to **Save Image to Folder**
2. Enter a custom filename in `file_name`
3. Select desired image format
4. Images will be saved with the specified name

## File Structure

```
Comfyui-txtnode/
├── __init__.py          # Plugin entry and node registration
├── nodes.py             # Node implementation
├── README.md            # This documentation
└── TECHNICAL_DOC.md     # Technical documentation
```

## Requirements

- ComfyUI
- Python 3.10+
- PIL (Pillow)
- numpy
- torch
