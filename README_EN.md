# ComfyUI Text Node Plugin

> [中文](./README.md) | **English**

A custom node plugin built on **ComfyUI V3 API**, providing text file operations, image processing, batch file loading, LoRA trigger word management, and model preview image management.

---

## Features

- **Text Nodes**: Save strings to files, load text files from folders
- **Image Nodes**: Save images to folders, resize and pad images, remove padding
- **LoRA Loaders**: Two versions of LoRA loaders with trigger word management
- **Trigger Word Picker**: Quick trigger word selection buttons on text and LoRA nodes
- **Model Preview Manager**: Right-click button to open manager dialog, add/modify model previews
- **Hover Preview**: Automatically display preview images when hovering over model names in context menus

---

## Node List

| Node | Category | Description |
|------|----------|-------------|
| **Save String to Text File** | `Utils` | Save text content to local file |
| **Save Image to Folder** | `Utils` | Save image tensor to specified folder |
| **Load Text Files from Folder** | `Utils` | Load text files by index (for loops) |
| **Resize and Pad Image** | `image/transform` | Resize image and pad to target size |
| **Remove Pad from Image** | `image/transform` | Remove padding, restore original size |
| **LoRA Loader (Model Only)** | `loaders/lora` | Load LoRA to model only, with trigger word management |
| **LoRA Loader (Full)** | `loaders/lora` | Load LoRA to both model and CLIP, with trigger word management |

---

## Installation

1. Clone or download this repository to ComfyUI's `custom_nodes` directory:
   ```
   ComfyUI/custom_nodes/Comfyui-txtnode/
   ```
2. Restart ComfyUI
3. Nodes will appear under `Utils`, `image/transform`, and `loaders/lora` categories

---

## Node Parameters

### Save String to Text File

Save text content to file. Supports single file append and multiple file split modes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | STRING | Yes | - | Text content to save (supports multiline) |
| `file_name` | STRING | Yes | `output` | File name (without extension) |
| `extension` | STRING | Yes | `txt` | File extension |
| `encoding` | COMBO | Yes | `utf-8` | Encoding: utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | Yes | `single_file` | Save mode: single_file / multiple_files |
| `directory_path` | STRING | No | ComfyUI/output | Target directory path |

**Output**: `file_path` - Absolute path of saved file

**Mode Description**:
- `single_file`: All output appended to same file (each iteration appends a line in loops)
- `multiple_files`: Split text by newlines, each line saved as separate file (`filename_index.ext`)

---

### Save Image to Folder

Save image tensor to specified folder.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `images` | IMAGE | Yes | - | Image tensor (supports batches) |
| `file_name` | STRING | Yes | `""` | File name (empty for auto-increment) |
| `image_format` | COMBO | Yes | `png` | Image format: png / jpg / jpeg / webp |
| `output_folder` | STRING | No | ComfyUI/output | Output folder path |

**Output**: `folder_path` - Absolute path of output folder

**File Name Rules**:
- Specified `file_name`: All images saved with this name (later images overwrite earlier ones)
- Empty `file_name`: Auto-increment naming `image_1.png`, `image_2.png`...

---

### Load Text Files from Folder

Load `.txt` files by index, designed for batch processing with for loops.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `folder_path` | STRING | Yes | ComfyUI/output | Directory containing .txt files |
| `max_files` | INT | Yes | `10` | Maximum file count (1-999) |
| `index` | INT | Yes | `0` | File index to load (starts from 0) |

**Output**: `text` - File content, `file_name` - File name

**Usage**:
1. Set `max_files` to total file count
2. Connect for loop's index to node's `index` input
3. Each iteration loads file 0, 1, 2...N sequentially

---

### Resize and Pad Image

Resize image and pad to target size, supports multiple padding modes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image` | IMAGE | Yes | - | Input image |
| `target_width` | INT | Yes | `512` | Target width |
| `target_height` | INT | Yes | `512` | Target height |
| `mode` | COMBO | Yes | `fit` | Padding mode: fit / fill / stretch |
| `background_color` | STRING | No | `#000000` | Background color (hex) |

**Output**: `IMAGE` - Resized image, `pad_info` - Padding info (for restoration)

---

### Remove Pad from Image

Remove image padding, restore original size. Use with "Resize and Pad Image" node.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image` | IMAGE | Yes | - | Padded image |
| `pad_info` | STRING | Yes | - | Padding info (from upstream node) |

**Output**: `IMAGE` - Image restored to original size

---

### LoRA Loader (Model Only)

Apply LoRA to model only (not CLIP), supports trigger word management and multi-LoRA trigger word chaining.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | MODEL | Yes | - | Input model from upstream |
| `lora_name` | COMBO | Yes | - | LoRA model file selector |
| `strength_model` | FLOAT | Yes | `1.0` | LoRA model strength (-10.0 ~ 10.0) |
| `trigger_word` | STRING | Yes | `""` | Current LoRA trigger word (multiline) |
| `upstream_trigger_word` | STRING | No | `""` | Upstream LoRA trigger word (port input) |

**Output**: `MODEL` - Model after LoRA, `trigger_word` - Merged trigger word

---

### LoRA Loader (Full)

Apply LoRA to both model and CLIP, supports trigger word management and multi-LoRA trigger word chaining.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | MODEL | Yes | - | Input model from upstream |
| `clip` | CLIP | Yes | - | Input CLIP from upstream |
| `lora_name` | COMBO | Yes | - | LoRA model file selector |
| `strength_model` | FLOAT | Yes | `1.0` | LoRA model strength (-10.0 ~ 10.0) |
| `strength_clip` | FLOAT | Yes | `1.0` | LoRA CLIP strength (-10.0 ~ 10.0) |
| `trigger_word` | STRING | Yes | `""` | Current LoRA trigger word (multiline) |
| `upstream_trigger_word` | STRING | No | `""` | Upstream LoRA trigger word (port input) |

**Output**: `MODEL` - Model after LoRA, `CLIP` - CLIP after LoRA, `trigger_word` - Merged trigger word

---

## Trigger Word Management Features

LoRA loader nodes provide complete trigger word management:

- **Auto Save**: Automatically save `trigger_word` to `lora_trigger_words.json` on execution
- **Auto Load**: Automatically fill in saved trigger word when switching LoRA selection
- **Multi-level Chaining**: Link multiple LoRA nodes via `upstream_trigger_word` port, trigger words auto-merge
- **Trigger Word Picker**: Quick buttons at bottom-left of input fields on text and LoRA nodes

---

## Usage Examples

### Batch Save Prompts to Separate Files
1. Connect multiline text to **Save String to Text File**'s `text` input
2. Set `save_mode` to `multiple_files`
3. Each line saved as separate file

### Batch Process Text Files
1. Use **Save String to Text File** (multiple_files mode) to generate files
2. Use **Load Text Files from Folder** with for loop
3. Set `max_files` to total file count
4. Each iteration loads one file's content

### Save Images with Custom Names
1. Connect image output to **Save Image to Folder**
2. Enter custom filename in `file_name`
3. Select image format
4. Images saved to specified directory

### Using LoRA Trigger Words (Single LoRA)
1. Add **LoRA Loader (Model Only)** or **LoRA Loader (Full)** node
2. Select a LoRA model
3. Fill in trigger word in `trigger_word` input
4. Connect `trigger_word` output to CLIP Text Encode or CR Text
5. Trigger word auto-saved after workflow execution

### Multi-LoRA Trigger Word Chaining
1. Chain two LoRA loader nodes
2. Connect first node's `trigger_word` output to second node's `upstream_trigger_word` input
3. Trigger words auto-merge as `"TriggerA, TriggerB"` format

### Using Trigger Word Picker
1. Find icon button at bottom-left of input field on **CLIP Text Encode**, **CR Text**, or **LoRA Loader** nodes
2. **Left-click** button to open trigger word selection popup
3. Popup shows saved trigger words and unsaved LoRAs
   - **Saved trigger words**: Click to apply directly (LoRA nodes check if LoRA name matches)
   - **Unsaved LoRAs**: Input field and save button, auto-writes to node input after saving
   - **Edit function**: Click "Edit" button to edit or delete saved trigger words

### Using Model Preview Manager
1. Find icon button at bottom-left of input field on text or LoRA nodes
2. **Right-click** button to open model preview manager
3. Window auto-scans workflow for model loader nodes:
   - CheckpointLoaderSimple (Checkpoint models)
   - LoraLoader / LoraLoaderModelOnly / LoRALoaderModelOnly / LoRALoaderFull (LoRA models)
   - UNETLoader / UnetLoader (UNet/Diffusion models)
4. List shows all detected models with type labels
   - **Has preview**: Shows thumbnail + `[Edit]` button
   - **No preview**: Shows `[Add]` button
5. Click `[Add]` or `[Edit]` button:
   - File picker dialog opens, select image file (png/jpg/webp)
   - Image preview confirmation dialog
   - Image auto-renamed to match model name, saved to model directory
6. List auto-refreshes after successful upload

### Using Context Menu Preview (Hover Preview)
1. Right-click on model loader node (Checkpoint/LoRA/UNet) to open model selection menu
2. Hover over model name, preview image auto-appears
3. Preview shows on right side of menu, auto-flips to left if out of screen
4. Click menu or any mouse button to hide preview

---

## File Structure

```
Comfyui-txtnode/
├── __init__.py                    # Plugin entry, V3 extension registration
├── nodes/                         # File operation nodes package
│   ├── __init__.py                # Node re-exports
│   ├── utils.py                   # Shared path utility functions
│   ├── save_string.py             # Save string to text node
│   ├── save_image.py              # Save image to folder node
│   ├── load_text.py               # Batch load text files node
│   └── resize_pad.py              # Resize and pad image node
├── lora_loader_node.py            # LoRA loader node (model only)
├── lora_loader_full_node.py       # LoRA loader node (full version)
├── trigger_word_manager.py        # Trigger word config manager
├── server.py                      # API routes (trigger words + model previews)
├── lora_trigger_words.json        # Trigger word config file (auto-generated)
├── requirements.txt               # Project dependencies
├── web/
│   ├── icon.png                   # Trigger word picker icon
│   ├── lora_loader.js             # LoRA node frontend extension
│   ├── trigger_word_picker.js     # Trigger word picker (text + LoRA nodes)
│   ├── model_preview.js           # Context menu hover preview
│   ├── model_preview_manager.js   # Model preview manager dialog
│   └── utils/
│       └── trigger-word-api.js    # Trigger word API wrapper
├── CLAUDE.md                      # Project development guidelines
├── README.md                      # Chinese documentation
└── README_EN.md                   # This file (English)
```

---

## Technical Architecture

- **V3 API**: All nodes inherit from `io.ComfyNode`, using `define_schema()` + `execute()` pattern
- **Extension Registration**: Via `ComfyExtension` + `comfy_entrypoint()` (ComfyUI new entry point)
- **Frontend Extensions**: `WEB_DIRECTORY = "./web"` loads frontend JS files
  - `lora_loader.js`: LoRA node trigger word management (save button, auto-load, context menu)
  - `trigger_word_picker.js`: Trigger word picker (supports text and LoRA nodes)
  - `model_preview.js`: Context menu hover preview (Monkey Patch LiteGraph.ContextMenu)
  - `model_preview_manager.js`: Model preview manager dialog (right-click TW button)
- **API Service**: `server.py` registers HTTP routes
  - `POST /comfyui-txtnode/save_trigger_word` - Save trigger word
  - `GET /comfyui-txtnode/get_trigger_word` - Get single trigger word
  - `GET /comfyui-txtnode/get_all_trigger_words` - Get all trigger words
  - `GET /model_preview/get_image_by_name` - Get model preview image by name
  - `POST /model_preview/upload_preview_image` - Upload model preview (JSON + base64)

---

## Dependencies

- ComfyUI (V3 API compatible version)
- Python 3.10+
- Pillow (image processing)
- numpy (array operations)
- torch (tensor processing)
- aiohttp (HTTP routing)
- typing_extensions (type support)
