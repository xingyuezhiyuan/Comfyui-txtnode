# ComfyUI Text Node Plugin

**English** | [简体中文](./README_CN.md)

A collection of ComfyUI custom nodes — 12 nodes in total — covering batch text file processing, image padding and restoration, LoRA loading with trigger word management, conditional route control, and real-time Photoshop bridging. This guide is organized by node usage; each node covers **what it does → how to wire it → parameters → steps**.

## Installation

### Via ComfyUI Manager (Recommended)

Search for `Comfyui-txtnode` in ComfyUI Manager, click install, then restart ComfyUI.

### Manual Installation

1. Clone this repository into ComfyUI's `custom_nodes` directory:
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/your-username/Comfyui-txtnode.git
   ```
2. Install dependencies: `pip install -r requirements.txt`
3. Restart ComfyUI

## Node Overview

Double-click the canvas or right-click → Add Node, then search by node name (the table below shows the name displayed in the ComfyUI UI):

| Node | Category | Purpose |
|------|----------|---------|
| Save String to Text File | `Utils` | Save text to a local file (single-file append / multi-file split) |
| Save Image to Folder | `Utils` | Save images to a specified folder |
| Load Text Files from Folder | `Utils` | Load .txt files by index for batch processing with a for loop |
| Resize and Pad Image (调整图像尺寸填充) | `txtnode` | Proportionally resize and center-pad to a square canvas |
| Remove Pad from Image (移除图像填充) | `txtnode` | Crop padding via metadata, restore original size |
| LoRA Loader Model Only (LoRA加载器(仅模型)) | `loaders/lora` | Apply LoRA to model only, with trigger word management |
| LoRA Loader Full (LoRA加载器(完整)) | `loaders/lora` | Apply LoRA to both model and CLIP |
| LoRA Prompt Encoder (LoRA提示词编码器) | `loaders/lora` | Multi-LoRA selection + prompt editing + CLIP encoding in one node |
| Route Blocker (是否阻断) | `txtnode` | Manually pass through / empty / silently interrupt a route |
| Any Exists (是否存在) | `txtnode` | Detect whether a route carries data; output placeholder + boolean |
| Get Image from PS (从PS获取图像) | `PS Bridge` | Read canvas and mask exported by Photoshop |
| Send Image to PS (发送图像到PS) | `PS Bridge` | Send images back to Photoshop |

---

## Text / File Utilities

### Save String to Text File

**What it does**: Writes text to a local file. `single_file` mode appends all content to one file (accumulating across repeated for-loop executions); `multiple_files` mode splits by newline and saves each line as its own file.

**Wiring**: Connect any upstream text source (prompt node, text concatenate node, etc.) to the `text` input. The `file_path` output is the absolute path of the saved file and usually needs no downstream connection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | STRING | - | Text to save (multiline input) |
| `file_name` | STRING | `output` | File name (without extension) |
| `extension` | STRING | `txt` | File extension |
| `encoding` | COMBO | `utf-8` | Encoding: utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | `single_file` | Save mode: single_file / multiple_files |
| `directory_path` | STRING | ComfyUI/output | Target directory (optional; empty uses the default output dir) |

**Output**: `file_path` — absolute file path (in multiple_files mode, the path of the first file)

**Steps**:
1. Batch save prompts to separate files: feed multiline text into `text` → set `save_mode` to `multiple_files` → each line becomes `{file_name}_1.txt`, `{file_name}_2.txt`… (blank lines are skipped)
2. Accumulate into one file across a for loop: keep `save_mode` as `single_file`; each execution appends (a newline is inserted automatically between writes)

### Save Image to Folder

**What it does**: Saves images to a specified folder, with batch support and custom naming.

**Wiring**: Connect the upstream image output (VAE Decode, post-KSampler, etc.) to `images`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `images` | IMAGE | - | Image tensor (supports batches) |
| `file_name` | STRING | `""` | File name; leave empty for auto-increment |
| `image_format` | COMBO | `png` | Format: png / jpg / jpeg / webp |
| `output_folder` | STRING | ComfyUI/output | Output folder (optional) |

**Output**: `folder_path` — absolute path of the output folder

**Steps**:
1. Connect the image output to `images`
2. With `file_name` set, later images in the batch overwrite earlier ones; with it empty, files are auto-named `image_1.png`, `image_2.png`… (existing numbers are skipped)
3. Pick the format; images are saved to the target directory on execution

### Load Text Files from Folder

**What it does**: Loads a `.txt` file by index from a folder — designed for batch processing with a for loop, loading exactly one file per execution.

**Wiring**: Connect the for-loop node's `index` output to this node's `index` input; connect the `text` output to the downstream prompt input (e.g. CLIP Text Encode).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_path` | STRING | ComfyUI/output | Directory containing .txt files |
| `max_files` | INT | `10` | Max file count (1-999; takes the first N by name order) |
| `index` | INT | `0` | File index to load (starts from 0) |

**Output**: `text` — file content, `file_name` — file name

**Steps**:
1. Generate the files first with **Save String to Text File** (multiple_files mode)
2. Add a for loop whose iteration count matches the total file count
3. Set `max_files` to the file count and wire the loop's index into this node's `index`
4. Each iteration loads file 0, 1, 2… in turn (sorted by file name, read as UTF-8)

---

## Image Processing

### Resize and Pad Image (调整图像尺寸填充)

**What it does**: Proportionally resizes the image and center-pads it onto a square canvas (black fill), while emitting `image_info` padding metadata so a downstream "Remove Pad from Image" node can crop it back precisely. Useful for feeding arbitrary aspect ratios into models that require square inputs.

**Wiring**: Connect the upstream image to `input_image`; route `output_image` to your processing chain; `image_info` **must** be connected to the `image_info` input of "Remove Pad from Image" for restoration to work.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_image` | IMAGE | - | Input image |
| `target_size` | INT | `1024` | Target size (64-8192, auto-snapped to the resolution multiple) |
| `resolution_multiple` | INT | `8` | Multiple to snap to (0-128, step 8; 0 disables snapping) |
| `upscale_method` | COMBO | `lanczos` | Resampling: lanczos / bicubic / area / nearest |
| `resize_and_pad` | BOOLEAN | `true` | When disabled, bypasses and passes the image through unchanged |

**Output**: `output_image` — padded square image, `image_info` — padding metadata (IMAGE_INFO type)

**Steps**:
1. Feed the image into `input_image` and set `target_size` (e.g. 1024)
2. Scaling rule: resize by the smaller of the width/height ratios so the image fits entirely, center it on the square canvas, fill the borders with black
3. Connect the `image_info` output across nodes to the downstream "Remove Pad from Image"

### Remove Pad from Image (移除图像填充)

**What it does**: Crops the padded area using `image_info` metadata, restoring the original aspect ratio. Use it as a pair with "Resize and Pad Image".

**Wiring**: Connect the processed image to `input_image`; connect the upstream "Resize and Pad Image" node's `image_info` output to this node's `image_info`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input_image` | IMAGE | - | Image to crop |
| `image_info` | IMAGE_INFO | - | Padding metadata (from the upstream node) |
| `remove_pad` | BOOLEAN | `true` | When disabled, bypasses and passes the image through |
| `latent_scale` | FLOAT | `0.0` | Latent-space scale factor (optional, for precise matching) |

**Output**: `output_image` — image restored to original dimensions

**Steps**:
1. Latent-space processing (e.g. KSampler) may change the image size; this node rescales the crop coordinates by the ratio of the current size to `original_size` automatically
2. If the latent-derived scale is off, set `latent_scale` manually: when it matches the computed value within a 10% tolerance, the manual value takes precedence
3. With invalid metadata or zero padding, the image passes through untouched instead of raising an error

---

## LoRA Loaders

All three LoRA nodes support **trigger word management**: trigger words are auto-saved to `lora_trigger_words.json` on execution; saved trigger words are auto-filled when you switch LoRA selection; chaining via the `upstream_trigger_word` port merges trigger words across multiple levels.

### LoRA Loader (Model Only) — LoRA加载器(仅模型)

**What it does**: Applies the LoRA to the model only (not CLIP). Suitable for LoRAs that shouldn't alter text-encoding style.

**Wiring**: Connect the upstream MODEL to `model`; route `MODEL` to the KSampler; connect the `trigger_word` output to CLIP Text Encode's text input (optionally concatenated with your prompt).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | MODEL | - | Input model from upstream |
| `lora_name` | COMBO | - | LoRA file selector (scans the loras directory) |
| `strength_model` | FLOAT | `1.0` | Model strength (-10.0 ~ 10.0, step 0.01) |
| `trigger_word` | STRING | `""` | Current LoRA's trigger word (multiline) |
| `upstream_trigger_word` | STRING | `""` | Upstream LoRA's trigger word (optional input port) |

**Output**: `MODEL` — model after LoRA, `trigger_word` — merged trigger words (formatted as `"upstream, current"`; empty values are omitted)

**Steps**:
1. Insert between the model loader and the KSampler, pick a LoRA and adjust strength
2. Fill in `trigger_word`; it auto-saves after execution
3. Multi-LoRA chaining: connect the first loader's `trigger_word` output to the second's `upstream_trigger_word` — trigger words merge automatically
4. **Trigger Word Picker**: the icon button at the bottom-left of the input field — **left-click** opens the picker popup. Saved trigger words apply on click; unsaved LoRAs let you enter and save one

### LoRA Loader (Full) — LoRA加载器(完整)

**What it does**: Applies the LoRA to both model and CLIP. For LoRAs that ship a text-encoder part (styles, concepts).

**Wiring**: Connect upstream MODEL to `model` and CLIP to `clip`; keep passing `MODEL`/`CLIP` downstream; connect `trigger_word` to CLIP Text Encode.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | MODEL | - | Input model from upstream |
| `clip` | CLIP | - | Input CLIP from upstream |
| `lora_name` | COMBO | - | LoRA file selector |
| `strength_model` | FLOAT | `1.0` | Model strength (-10.0 ~ 10.0) |
| `strength_clip` | FLOAT | `1.0` | CLIP strength (-10.0 ~ 10.0) |
| `trigger_word` | STRING | `""` | Current LoRA's trigger word |
| `upstream_trigger_word` | STRING | `""` | Upstream LoRA's trigger word (optional input port) |

**Output**: `MODEL`, `CLIP` — model and CLIP after LoRA, `trigger_word` — merged trigger words

**Steps**: Same as the Model Only variant, plus you must carry the CLIP chain through.

### Model Preview Manager (LoRA loaders and other model loader nodes)

- **Right-click** the icon button at the bottom-left of a node's input field to open the model preview manager
- It auto-scans the workflow for model loader nodes; click `[Add]` or `[Edit]` to upload a preview image
- **Right-click a model loader node** to open the model selection menu; hovering a model name auto-shows its preview; click the menu or press any mouse button to hide it

### LoRA Prompt Encoder — LoRA提示词编码器

**What it does**: An all-in-one node combining multi-LoRA selection, prompt editing, and CLIP text encoding. One node replaces the traditional chain of several LoRA loaders plus two CLIP Text Encode nodes.

**Wiring**: Connect upstream MODEL to `model` and CLIP to `clip`; route `MODEL` to the KSampler; connect `CONDITIONING` / `NEGATIVE_CONDITIONING` to the KSampler's positive/negative conditioning. `positive_prompt` / `negative_prompt` are optional input ports that override the panel prompts when an external text node is connected.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | MODEL | - | Input model from upstream |
| `clip` | CLIP | - | Input CLIP from upstream |
| `positive_prompt` | STRING | `""` | Positive prompt (optional input port) |
| `negative_prompt` | STRING | `""` | Negative prompt (optional input port) |

**Output**: `MODEL` — model with all selected LoRAs applied, `CONDITIONING` — positive, `NEGATIVE_CONDITIONING` — negative

**Panel layout**:
- Left: positive/negative prompt editors + the selected LoRA list (each entry has a strength slider, a disable toggle, and an ✕ remove button)
- Right: search box + folder filter + LoRA thumbnail grid + pagination

**Steps**:
1. Click a thumbnail in the right-hand grid to add that LoRA to the selected list — its trigger word is appended to the end of the positive prompt automatically
2. Adjust each LoRA's strength on the left and write your positive/negative prompts
3. Understand the two distinct states:
   - **Disable** (toggle switch): temporarily suspends the LoRA — model loading is skipped and its trigger word leaves the prompt, but the entry and its strength are kept; toggling back restores everything
   - **Remove** (✕ button / clicking an enabled card): permanently deletes the entry and its trigger word
4. Left-click a thumbnail: edit that LoRA's trigger word. Right-click a thumbnail: upload/replace its preview image
5. **Style Prompt Cards**: the panel ships 9 preset art-style cards (Anime CG, Cel-shaded Anime, Isometric 3D, Pixel Art, Cartoon Block, Cute Chibi, Hand-drawn Brush, Watercolor, Simple Anime); clicking one injects that style into the prompt. Custom cards can be added/edited/deleted, and user card data is stored separately so plugin updates won't lose it

---

## Conditional Routing

Controls whether data flows through a route in your workflow. Both nodes operate on a **universal route** — a socket that accepts any data type.

### Route Blocker (是否阻断)

**What it does**: A manual on/off switch for a route. Disabled, it passes data straight through; enabled, the **block mode** decides whether downstream receives an empty value or the whole branch is silently skipped.

**Wiring**: Connect any data type to the `any` input and route the `any` output downstream, inserting the node in the middle of the line you want to switch.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `block_switch` | BOOLEAN | `false` | Block switch: on = block, off = pass through |
| `block_mode` | COMBO | `仅输出空值` | Block mode: output empty value only / interrupt downstream branch |
| `any` | AnyType | - | Universal route input (optional) |

**Output**: `any` — the route after pass-through / emptying / blocking

**Two block modes**:
- **Output empty value only**: emits None; downstream nodes still run and must tolerate it
- **Interrupt downstream branch**: the entire branch is silently skipped — no error, saves compute (equivalent to Ctrl+M on a branch)

**Steps**:
1. Insert the node into the route (e.g. between the KSampler and the decoder)
2. Keep the switch off for normal output; turn it on and pick a mode to cut the branch temporarily without deleting connections

### Any Exists (是否存在)

**What it does**: Detects whether a universal route carries valid data. With data it passes it through and outputs boolean `true`; when empty it outputs a type-specific **placeholder** and `false`, so downstream type validation never breaks. Commonly paired with Route Blocker or switch nodes to build "process if present, skip if absent" branching.

**Wiring**: Connect the route to be tested to `any`; feed the `any` output (pass-through value or placeholder) into the downstream data flow; use the boolean output to drive nodes that need a true/false signal.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `any` | AnyType | - | Universal route input (optional) |

**Output**: `any` — original data or placeholder, boolean — whether valid data exists

**Placeholder rules** (generated by type when the route is empty):

| Type | Placeholder |
|------|-------------|
| IMAGE | 64×64 black image |
| MASK | 64×64 all-black mask |
| LATENT | 1×4×1×1 empty latent |
| CONDITIONING | empty list |
| STRING / INT / FLOAT / BOOLEAN | `""` / `0` / `0.0` / `False` |
| MODEL / CLIP / VAE | None (no valid object can be fabricated) |

**Emptiness details**:
- A pure-black mask, and a mask whose residuals are barely visible (below 2% visibility), count as empty
- `0` and `False` are valid content and are not treated as empty
- The frontend detects the universal route's type automatically and the node label changes to match the source type

**Steps**:
1. Feed a possibly-empty route (e.g. a Route Blocker's output) into `any`
2. Consume the `any` output directly downstream — when empty you get a placeholder instead of a type error
3. Drive conditional branches with the boolean output (together with other switch/loop nodes)

---

## PS Bridge (Photoshop Bridging)

Requires a companion Photoshop UXP plugin; image transfer happens through file exchange for real-time collaboration.

### Get Image from PS (从PS获取图像)

**What it does**: Reads the canvas and mask exported by Photoshop from ComfyUI's input directory.

**Wiring**: Connect `image` to an image input (VAE Encode, IPAdapter, etc.) and `mask` to a mask input (inpaint workflows).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_filename` | STRING | `""` | Canvas file name (optional, default `xyps_canvas.png`) |
| `mask_filename` | STRING | `""` | Mask file name (optional, default `xyps_mask.png`) |

**Output**: `image` — canvas image, `mask` — mask (red channel extracted as grayscale)

**Steps**:
1. Edit the canvas and mask in Photoshop; the UXP plugin exports them into ComfyUI's input directory
2. The node auto-detects file changes and triggers re-execution — no manual refresh needed
3. When files don't exist, a gray checkerboard placeholder and an all-white mask are used so the workflow won't error
4. For multi-user LAN setups, assign different file names per user to isolate them

### Send Image to PS (发送图像到PS)

**What it does**: Saves the image to the output directory and notifies the Photoshop plugin to load it. A pure output node — it does not pass the image tensor further.

**Wiring**: Connect your result (e.g. VAE Decode output) to `images` as the workflow's terminal node.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `images` | IMAGE | - | Input image tensor |
| `client_id` | STRING | `""` | Client ID (optional, for multi-user output isolation) |

**Steps**:
1. Connect the processed result to `images`
2. On execution the image is written to the output directory and Photoshop picks it up automatically
3. In multi-user scenarios, set a distinct `client_id` per user

---

## Example Workflows

The `workflow/` directory ships ready-to-import examples:

| File | Contents | Nodes involved |
|------|----------|----------------|
| `workflow/workflow.json` | Batch text processing + LoRA loading | Save String to Text File, Load Text Files from Folder, Save Image to Folder, LoRA Loader (Model Only) |
| `workflow/sdxl工作流示例.json` | SDXL multi-LoRA generation | LoRA Prompt Encoder |
| `workflow/web.json` | Photoshop real-time collaboration | Get Image from PS, Send Image to PS |

Import by dragging the JSON file straight onto the ComfyUI canvas, or load it from the menu.

---

## Dependencies

- ComfyUI (a V3 API compatible version)
- Python 3.10+
- Pillow, numpy, aiohttp, typing_extensions

> These are typically already installed with ComfyUI and usually need no separate installation.
