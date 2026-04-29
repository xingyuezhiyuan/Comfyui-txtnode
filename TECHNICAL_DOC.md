# Comfyui-txtnode Technical Documentation

## Project Overview

Comfyui-txtnode is a ComfyUI custom node plugin that provides utility nodes for text and image file operations. It includes three core nodes: text saving, image saving, and text file loading.

## Project Structure

```
Comfyui-txtnode/
├── __init__.py              # Plugin entry point and node registration
├── nodes.py                 # Core node implementation
├── README.md                # User-facing documentation
└── TECHNICAL_DOC.md         # Technical documentation (this file)
```

## Core Architecture

### Utility Functions

#### `get_default_output_dir()`

Automatically detects the ComfyUI root directory by traversing up three levels from the current file path, then returns the `output` subdirectory.

```
__file__ → custom_nodes/Comfyui-txtnode/
  └─ 1 level up → custom_nodes/
    └─ 2 levels up → ComfyUI/
      └─ + "output" → ComfyUI/output/
```

#### `ensure_absolute_path(path_str, default_to_cwd)`

Converts relative paths to absolute paths. If the input is empty, defaults to the current working directory when `default_to_cwd=True`.

#### `ensure_parent_directory(file_path)`

Creates parent directories recursively using `mkdir(parents=True, exist_ok=True)`.

---

## Node Specifications

### 1. SaveStringToTextNode

**Display Name**: Save String to Text File  
**Category**: Utils  
**Type**: Output Node

#### Input Ports

| Port | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| text | STRING | Yes | N/A | Text content to save. Supports multiline and forceInput |
| file_name | STRING | Yes | "output" | Base filename without extension |
| extension | STRING | Yes | "txt" | File extension |
| encoding | ENUM | Yes | "utf-8" | Options: utf-8, gbk, utf-16, ascii |
| save_mode | ENUM | Yes | "single_file" | Options: single_file, multiple_files |
| directory_path | STRING | No | ComfyUI/output | Target directory path |

#### Output Ports

| Port | Type | Description |
|------|------|-------------|
| file_path | STRING | Absolute path to the saved file |

#### Save Mode Logic

**single_file mode:**
- All content is written to one file
- Uses append mode (`"a"`) if the file already exists and is non-empty
- Adds a newline separator before appending
- First write uses write mode (`"w"`)

**multiple_files mode:**
- Splits input text by newline characters
- Each non-empty line becomes a separate file
- Files are named `{file_name}_{index}.{extension}` (1-based indexing)
- Returns the path of the first created file

#### Error Handling

Wraps all operations in try-except, raising formatted exceptions on failure.

---

### 2. SaveImageToFolderNode

**Display Name**: Save Image to Folder  
**Category**: Utils  
**Type**: Output Node

#### Input Ports

| Port | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| images | IMAGE | Yes | N/A | ComfyUI IMAGE tensor batch |
| file_name | STRING | Yes | "" | Filename for saving (empty = auto-naming) |
| image_format | ENUM | Yes | "png" | Options: png, jpg, jpeg, webp |
| output_folder | STRING | No | ComfyUI/output | Target directory path |

#### Output Ports

| Port | Type | Description |
|------|------|-------------|
| folder_path | STRING | Absolute path to the output folder |

#### Image Processing Pipeline

1. Convert IMAGE tensor from GPU to CPU
2. Scale values from [0,1] to [0,255] range
3. Convert to numpy array with uint8 type
4. Create PIL Image from array
5. Save using PIL with format-specific encoding

#### Naming Logic

**When file_name is provided:**
- Uses exact filename: `{file_name}.{image_format}`

**When file_name is empty:**
- Auto-generates sequential names: `image_1.png`, `image_2.png`, etc.
- Checks for existing files to avoid overwriting

---

### 3. LoadTextFilesNode

**Display Name**: Load Text Files from Folder  
**Category**: Utils  
**Type**: Output Node

#### Input Ports

| Port | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| folder_path | STRING | Yes | ComfyUI/output | Directory containing txt files |
| max_files | INT | Yes | 10 | Maximum number of files to load (1-999) |
| index | INT | Yes | 0 | File index to load (0 to max_files-1) |

#### Output Ports

| Port | Type | Description |
|------|------|-------------|
| text | STRING | Content of the loaded file |
| file_name | STRING | Name of the loaded file |

#### File Loading Logic

1. Validates folder existence and type
2. Collects all `.txt` files (case-insensitive extension check)
3. Sorts files alphabetically by name
4. Applies max_files limit
5. Selects file by index
6. Reads content with UTF-8 encoding

#### Loop Integration Pattern

Designed to work with ComfyUI for-loop nodes:
- Set max_files to total file count
- Connect loop index to the index input
- Each iteration loads the next file sequentially

#### Console Output

Prints loading information during execution:
```
[LoadTextFilesNode] 加载文件 (1/10): file1.txt
[LoadTextFilesNode] 文件路径：F:\path\to\file1.txt
[LoadTextFilesNode] 内容长度：1234 字符
```

---

## Dependencies

| Library | Usage |
|---------|-------|
| torch | GPU tensor to CPU conversion |
| PIL (Pillow) | Image format conversion and saving |
| numpy | Array manipulation for image data |
| os | Path operations and environment detection |
| pathlib | Modern path handling (Path class) |

## Node Registration Pattern

Nodes are registered via `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` dictionaries in `__init__.py`. The `__all__` export list exposes these mappings to the ComfyUI plugin loader.

## ComfyUI Integration Points

- **Custom Node Detection**: ComfyUI scans `custom_nodes/` for `__init__.py` files
- **Node Category**: All nodes use "Utils" category for grouping
- **Output Node Flag**: All nodes set `OUTPUT_NODE = True` to indicate terminal operations
- **Force Input**: The text input uses `forceInput: True` to require connected values
