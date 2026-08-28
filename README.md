# ComfyUI Text Node Plugin

**English** | [简体中文](./README_CN.md)

A collection of ComfyUI custom nodes providing text file management, image processing, LoRA loading with trigger word management, Photoshop bridging, style prompt cards, and other utilities.

## Installation

### Via ComfyUI Manager (Recommended)

Search for `Comfyui-txtnode` in ComfyUI Manager and click install.

### Manual Installation

1. Clone this repository into ComfyUI's `custom_nodes` directory:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/your-username/Comfyui-txtnode.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Restart ComfyUI

## Node Overview

| Node | Category | Description |
|------|----------|-------------|
| **Save String to Text File** | `Utils` | Save text content to local file |
| **Save Image to Folder** | `Utils` | Save images to specified folder |
| **Load Text Files from Folder** | `Utils` | Load text files by index from folder |
| **Resize and Pad Image** | `txtnode` | Resize image and pad to square canvas |
| **Remove Pad from Image** | `txtnode` | Remove padding, restore original size |
| **LoRA Loader (Model Only)** | `loaders/lora` | Load LoRA to model only (no CLIP) |
| **LoRA Loader (Full)** | `loaders/lora` | Load LoRA to both model and CLIP |
| **LoRA Prompt Encoder** | `loaders/lora` | Multi-LoRA selection + prompt editing + CLIP encoding |
| **Get Image from PS** | `PS Bridge` | Get canvas and mask from Photoshop |
| **Send Image to PS** | `PS Bridge` | Send images to Photoshop |

---

## Text / File Utilities

### Save String to Text File

Save text content to file. Supports single file append and multiple file split modes.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | STRING | - | Text content to save |
| `file_name` | STRING | `output` | File name (without extension) |
| `extension` | STRING | `txt` | File extension |
| `encoding` | COMBO | `utf-8` | Encoding: utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | `single_file` | Save mode: single_file / multiple_files |
| `directory_path` | STRING | ComfyUI/output | Target directory path (optional) |

**Output**: `file_path` — Absolute path of saved file

- `single_file`: All content appended to the same file
- `multiple_files`: Split by newlines, each line saved as a separate file (designed for batch processing with for loops)

### Save Image to Folder

Save images to a specified folder.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `images` | IMAGE | - | Image tensor (supports batches) |
| `file_name` | STRING | `""` | File name (empty for auto-increment) |
| `image_format` | COMBO | `png` | Image format: png / jpg / jpeg / webp |
| `output_folder` | STRING | ComfyUI/output | Output folder path (optional) |

**Output**: `folder_path` — Absolute path of output folder

- Specified `file_name`: Later images in batch overwrite earlier ones
- Empty `file_name`: Auto-increment naming `image_1.png`, `image_2.png`...

### Load Text Files from Folder

Load `.txt` files by index, designed for batch processing with for loops.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_path` | STRING | ComfyUI/output | Directory containing .txt files |
| `max_files` | INT | `10` | Maximum file count (1-999) |
| `index` | INT | `0` | File index to load (starts from 0) |

**Output**: `text` — File content, `file_name` — File name

---

## Image Processing

### Resize and Pad Image

Resize image proportionally and center-pad to a square canvas, while recording padding metadata for downstream cropping.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_image` | IMAGE | - | Input image |
| `target_size` | INT | `1024` | Target size (64-8192, auto-snaps to resolution multiple) |
| `resolution_multiple` | INT | `32` | Resolution multiple (8-128) |
| `upscale_method` | COMBO | `lanczos` | Upscale algorithm: lanczos / bicubic / area / nearest |
| `resize_and_pad` | BOOLEAN | `true` | Enable/disable (bypass when disabled) |

**Output**: `output_image` — Resized image, `image_info` — Padding metadata

### Remove Pad from Image

Crop padding area based on metadata to restore the original aspect ratio. Use with the "Resize and Pad Image" node.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_image` | IMAGE | - | Padded image |
| `image_info` | IMAGE_INFO | - | Padding metadata (from upstream node) |
| `remove_pad` | BOOLEAN | `true` | Enable/disable (bypass when disabled) |
| `latent_scale` | FLOAT | `0.0` | Latent space scale factor (optional, for precise matching) |

**Output**: `output_image` — Image restored to original dimensions

---

## LoRA Loaders

### LoRA Loader (Model Only)

Apply LoRA to model only (not CLIP), with trigger word management and multi-LoRA chaining.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | MODEL | - | Input model from upstream |
| `lora_name` | COMBO | - | LoRA model file selector |
| `strength_model` | FLOAT | `1.0` | LoRA model strength (-10.0 ~ 10.0) |
| `trigger_word` | STRING | `""` | Current LoRA trigger word |
| `upstream_trigger_word` | STRING | `""` | Upstream LoRA trigger word (optional) |

**Output**: `MODEL` — Model after LoRA, `trigger_word` — Merged trigger word

### LoRA Loader (Full)

Apply LoRA to both model and CLIP, with trigger word management and multi-LoRA chaining.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | MODEL | - | Input model from upstream |
| `clip` | CLIP | - | Input CLIP from upstream |
| `lora_name` | COMBO | - | LoRA model file selector |
| `strength_model` | FLOAT | `1.0` | LoRA model strength (-10.0 ~ 10.0) |
| `strength_clip` | FLOAT | `1.0` | LoRA CLIP strength (-10.0 ~ 10.0) |
| `trigger_word` | STRING | `""` | Current LoRA trigger word |
| `upstream_trigger_word` | STRING | `""` | Upstream LoRA trigger word (optional) |

**Output**: `MODEL`, `CLIP` — Model and CLIP after LoRA, `trigger_word` — Merged trigger word

### LoRA Prompt Encoder

Integrated multi-LoRA selection, prompt editing, and CLIP text encoding. Supports loading multiple LoRAs with independent strength control.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | MODEL | - | Input model from upstream |
| `clip` | CLIP | - | Input CLIP from upstream |
| `positive_prompt` | STRING | `""` | Positive prompt (optional input port) |
| `negative_prompt` | STRING | `""` | Negative prompt (optional input port) |

**Output**: `MODEL` — Model with all LoRAs applied, `CONDITIONING` — Positive, `NEGATIVE_CONDITIONING` — Negative

**Frontend UI Features**:
- Left panel: Positive/negative prompt editing + Selected LoRA list (with strength sliders)
- Right panel: Search box + Folder filter + Thumbnail grid + Pagination
- Left-click thumbnail: Edit trigger word
- Right-click thumbnail: Upload/modify preview image

---

## PS Bridge (Photoshop Bridging)

Requires a Photoshop UXP plugin for real-time image transfer between ComfyUI and Photoshop.

### Get Image from PS

Read canvas and mask exported by Photoshop from ComfyUI's input directory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_filename` | STRING | `""` | Canvas file name (optional, default: `xyps_canvas.png`) |
| `mask_filename` | STRING | `""` | Mask file name (optional, default: `xyps_mask.png`) |

**Output**: `image` — Canvas image, `mask` — Mask (red channel extracted as grayscale)

- Uses a checkerboard placeholder image and white mask when files don't exist
- Supports multi-user isolation on LAN via custom file names
- Auto-detects file changes to trigger re-execution

### Send Image to PS

Save images to output directory and notify the Photoshop plugin. Pure output node — does not pass image tensors.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `images` | IMAGE | - | Input image tensor |
| `client_id` | STRING | `""` | Client ID (optional, for multi-user output isolation) |

---

## Frontend Features

### Trigger Word Management

LoRA loader nodes provide complete trigger word management:

- **Auto Save**: Automatically saves trigger words to `lora_trigger_words.json` on execution
- **Auto Load**: Automatically fills in saved trigger words when switching LoRA selection
- **Multi-level Chaining**: Link multiple LoRA nodes via `upstream_trigger_word` port, trigger words auto-merge

### Trigger Word Picker

Quick buttons at the bottom-left of input fields on text and LoRA nodes:

- **Left-click** to open trigger word selection popup
- Saved trigger words: Click to apply directly
- Unsaved LoRAs: Input and save

### Model Preview Manager

- Find the icon button at the bottom-left of input fields
- **Right-click** to open the model preview manager
- Auto-scans workflow for model loader nodes
- Click `[Add]` or `[Edit]` to upload preview images

### Context Menu Hover Preview

- Right-click on a model loader node to open the model selection menu
- Hover over a model name to auto-display its preview image
- Click the menu or any mouse button to hide the preview

### Style Prompt Cards

Pre-built art style prompt cards for use with the LoRA Prompt Encoder:

- 9 built-in styles: Anime CG, Cel-shaded Anime, Isometric 3D, Pixel Art, Cartoon Block, Cute Chibi, Hand-drawn Brush, Watercolor, Simple Anime
- Support for custom add/edit/delete of style cards
- User card data stored separately — plugin updates won't lose your data

---

## Usage Examples

### Batch Save Prompts to Separate Files
1. Connect multiline text to **Save String to Text File**'s `text` input
2. Set `save_mode` to `multiple_files`
3. Each line saves as a separate file

### Batch Process Text Files
1. Use **Save String to Text File** (multiple_files mode) to generate files
2. Use **Load Text Files from Folder** with a for loop
3. Set `max_files` to match the total file count
4. Each iteration loads one file's content

### Save Images with Custom Names
1. Connect image output to **Save Image to Folder**
2. Enter custom filename in `file_name`
3. Select image format, images are saved to the specified directory

### Proportional Resize and Restore
1. Use **Resize and Pad Image** to proportionally scale to a square canvas
2. Connect `image_info` output to **Remove Pad from Image**'s `image_info` input
3. After processing, **Remove Pad from Image** automatically crops back to original aspect ratio

### Using LoRA Trigger Words (Single LoRA)
1. Add a LoRA loader node, select a LoRA model
2. Fill in the trigger word in the `trigger_word` input
3. Connect output to CLIP Text Encode's text input
4. Trigger word auto-saves after workflow execution

### Multi-LoRA Trigger Word Chaining
1. Chain two LoRA loader nodes
2. Connect the first node's output to the second node's `upstream_trigger_word`
3. Trigger words auto-merge as `"TriggerA, TriggerB"` format

### Using Trigger Word Picker
1. Find the icon button at the bottom-left of input fields
2. **Left-click** to open the trigger word selection popup
3. Saved trigger words: Click to apply directly
4. Unsaved LoRAs: Input and save

### Using Model Preview Manager
1. Find the icon button at the bottom-left of input fields
2. **Right-click** to open the model preview manager
3. Auto-scans workflow for model loader nodes
4. Click `[Add]` or `[Edit]` to upload preview images

### Using Context Menu Hover Preview
1. Right-click on a model loader node to open the model selection menu
2. Hover over a model name to auto-display its preview image
3. Click the menu or any mouse button to hide the preview

### Photoshop Real-time Collaboration
1. Edit canvas and mask in Photoshop
2. Use **Get Image from PS** node to import canvas and mask
3. Connect your processing pipeline
4. Use **Send Image to PS** node to send results back to Photoshop

---

## Compatible Plugins

This plugin works well with the following ComfyUI plugins:

| Plugin | Relationship | Description |
|--------|-------------|-------------|
| [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) | Installation | Supports installing and managing this plugin via Manager |
| [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) | Integration | LoRA loaders work with Impact-Pack's Detailer nodes |
| [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use) | Integration | Text/image utility nodes pair well with Easy-Use batch processing |
| [comfyui-photoshop](https://github.com/NimaNzrii/comfyui-photoshop) | PS Bridge | Alternative Photoshop bridging solution; this plugin's PS Bridge nodes provide an independent file-transfer approach |
| [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) | Integration | Image processing nodes complement KJNodes image tools |
| [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | Integration | Batch text file processing pairs well with video frame workflows |

---

## Dependencies

- ComfyUI (V3 API compatible version)
- Python 3.10+
- Pillow (image processing)
- numpy (array operations)
- aiohttp (HTTP routing)
- typing_extensions (type support)

> These dependencies are typically included with ComfyUI and usually don't require separate installation.
