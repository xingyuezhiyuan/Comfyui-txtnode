# ComfyUI Text Node 插件

<p align="center">
  <a href="javascript:void(0)" onclick="document.querySelectorAll('.lang-cn').forEach(e=>e.style.display='');document.querySelectorAll('.lang-en').forEach(e=>e.style.display='none');document.getElementById('lang-cn-tab').style.fontWeight='bold';document.getElementById('lang-en-tab').style.fontWeight='normal'"><b id="lang-cn-tab">简体中文</b></a>
  &nbsp;|&nbsp;
  <a href="javascript:void(0)" onclick="document.querySelectorAll('.lang-cn').forEach(e=>e.style.display='none');document.querySelectorAll('.lang-en').forEach(e=>e.style.display='');document.getElementById('lang-en-tab').style.fontWeight='bold';document.getElementById('lang-cn-tab').style.fontWeight='normal'"><b id="lang-en-tab" style="font-weight:normal">English</b></a>
</p>

---

<div class="lang-cn">

## 简介

一个 ComfyUI 自定义节点插件，提供文本文件管理、图像处理、LoRA 加载与触发词管理等实用功能。

**核心功能：**
- **文本节点**：保存字符串到文件、从文件夹加载文本文件
- **图像节点**：保存图像到文件夹、调整图像尺寸填充、移除图像填充
- **LoRA 加载器**：三个版本的 LoRA 加载器，支持触发词管理
- **LoRA 提示词编码器**：集成多 LoRA 选择、提示词编辑和 CLIP 文本编码
- **触发词选择器**：在文本节点和 LoRA 节点上提供快捷触发词选择按钮
- **模型预览图管理**：右键按钮打开管理弹窗，为模型添加/修改预览图
- **悬停预览**：右键菜单悬停模型名时自动显示预览图

## 安装

1. 将此仓库克隆或下载到 ComfyUI 的 `custom_nodes` 目录：
   ```
   ComfyUI/custom_nodes/Comfyui-txtnode/
   ```
2. 重启 ComfyUI
3. 节点出现在 `Utils`、`image/transform` 和 `loaders/lora` 分类下

## 节点列表

| 节点 | 分类 | 说明 |
|------|------|------|
| **Save String to Text File** | `Utils` | 将文本内容保存到本地文件 |
| **Save Image to Folder** | `Utils` | 将图片张量保存到指定文件夹 |
| **Load Text Files from Folder** | `Utils` | 按索引从文件夹加载文本文件 |
| **调整图像尺寸填充** | `image/transform` | 将图像调整尺寸并填充到指定大小 |
| **移除图像填充** | `image/transform` | 移除图像填充，恢复原始尺寸 |
| **LoRA加载器(仅模型)** | `loaders/lora` | 加载 LoRA 到模型（不含 CLIP） |
| **LoRA加载器(完整)** | `loaders/lora` | 同时加载 LoRA 到模型和 CLIP |
| **LoRA提示词编码器** | `loaders/lora` | 多 LoRA 选择 + 提示词编辑 + CLIP 编码 |

## 节点参数

### Save String to Text File

将文本内容保存到文件。支持单文件追加和多文件分割两种模式。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | STRING | 是 | - | 要保存的文本内容 |
| `file_name` | STRING | 是 | `output` | 文件名（不含扩展名） |
| `extension` | STRING | 是 | `txt` | 文件扩展名 |
| `encoding` | COMBO | 是 | `utf-8` | 编码：utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | 是 | `single_file` | 保存模式：single_file / multiple_files |
| `directory_path` | STRING | 否 | ComfyUI/output | 目标目录路径 |

**输出**：`file_path` - 保存文件的绝对路径

- `single_file`：所有输出追加到同一文件
- `multiple_files`：按换行符分割，每行保存为独立文件

### Save Image to Folder

将图片张量保存到指定文件夹。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `images` | IMAGE | 是 | - | 图片张量（支持批次） |
| `file_name` | STRING | 是 | `""` | 文件名（留空自动递增命名） |
| `image_format` | COMBO | 是 | `png` | 图片格式：png / jpg / jpeg / webp |
| `output_folder` | STRING | 否 | ComfyUI/output | 输出文件夹路径 |

**输出**：`folder_path` - 输出文件夹的绝对路径

- 指定 `file_name`：批次中后面的图片会覆盖前面的
- 留空 `file_name`：自动递增命名 `image_1.png`、`image_2.png`...

### Load Text Files from Folder

按索引从文件夹中加载 `.txt` 文件，专为 for 循环批量处理设计。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `folder_path` | STRING | 是 | ComfyUI/output | 包含 .txt 文件的目录 |
| `max_files` | INT | 是 | `10` | 最大文件数（1-999） |
| `index` | INT | 是 | `0` | 要加载的文件索引（从 0 开始） |

**输出**：`text` - 文件内容，`file_name` - 文件名

### 调整图像尺寸填充

将图像调整尺寸并填充到指定大小，支持多种填充模式。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | IMAGE | 是 | - | 输入图像 |
| `target_width` | INT | 是 | `512` | 目标宽度 |
| `target_height` | INT | 是 | `512` | 目标高度 |
| `mode` | COMBO | 是 | `fit` | 填充模式：fit / fill / stretch |
| `background_color` | STRING | 否 | `#000000` | 背景颜色（十六进制） |

**输出**：`IMAGE` - 调整后的图像，`pad_info` - 填充信息

### 移除图像填充

移除图像填充，恢复原始尺寸。配合"调整图像尺寸填充"节点使用。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | IMAGE | 是 | - | 填充后的图像 |
| `pad_info` | STRING | 是 | - | 填充信息（来自上游节点） |

**输出**：`IMAGE` - 恢复原始尺寸的图像

### LoRA加载器(仅模型)

将 LoRA 应用到模型（不应用到 CLIP），支持触发词管理和多 LoRA 触发词链接。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | MODEL | 是 | - | 来自上游的输入模型 |
| `lora_name` | COMBO | 是 | - | LoRA 模型文件选择器 |
| `strength_model` | FLOAT | 是 | `1.0` | LoRA 模型强度（-10.0 ~ 10.0） |
| `trigger_word` | STRING | 是 | `""` | 当前 LoRA 的触发词 |
| `upstream_trigger_word` | STRING | 否 | `""` | 上游 LoRA 的触发词 |

**输出**：`MODEL` - 应用 LoRA 后的模型，`trigger_word` - 合并后的触发词

### LoRA加载器(完整)

同时将 LoRA 应用到模型和 CLIP，支持触发词管理和多 LoRA 触发词链接。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | MODEL | 是 | - | 来自上游的输入模型 |
| `clip` | CLIP | 是 | - | 来自上游的输入 CLIP |
| `lora_name` | COMBO | 是 | - | LoRA 模型文件选择器 |
| `strength_model` | FLOAT | 是 | `1.0` | LoRA 模型强度（-10.0 ~ 10.0） |
| `strength_clip` | FLOAT | 是 | `1.0` | LoRA CLIP 强度（-10.0 ~ 10.0） |
| `trigger_word` | STRING | 是 | `""` | 当前 LoRA 的触发词 |
| `upstream_trigger_word` | STRING | 否 | `""` | 上游 LoRA 的触发词 |

**输出**：`MODEL`、`CLIP` - 应用 LoRA 后的模型和 CLIP，`trigger_word` - 合并后的触发词

### LoRA提示词编码器

集成多 LoRA 选择、提示词编辑和 CLIP 文本编码。支持同时加载多个 LoRA 并独立调节强度。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | MODEL | 是 | - | 来自上游的输入模型 |
| `clip` | CLIP | 是 | - | 来自上游的输入 CLIP |
| `selected_loras_json` | STRING | 是 | `"[]"` | 已选 LoRA 列表（JSON 格式，由前端 UI 生成） |
| `positive_prompt` | STRING | 是 | `""` | 正面提示词 |
| `negative_prompt` | STRING | 是 | `""` | 负面提示词 |

**输出**：`MODEL` - 应用所有 LoRA 后的模型，`CONDITIONING` - 正面条件，`NEGATIVE_CONDITIONING` - 负面条件

**前端 UI 功能**：
- 左侧面板：正面/负面提示词编辑 + 已选 LoRA 列表（含强度滑块）
- 右侧面板：搜索框 + 文件夹筛选 + 缩略图网格 + 分页控制
- 左键点击缩略图：编辑触发词
- 右键点击缩略图：上传/修改预览图

## 触发词管理

LoRA 加载器节点提供完整的触发词管理功能：

- **自动保存**：执行时将触发词自动保存到 `lora_trigger_words.json`
- **自动加载**：切换 LoRA 选择时，自动回填已保存的触发词
- **多级链接**：通过 `upstream_trigger_word` 端口链接多个 LoRA 节点，触发词自动合并
- **触发词选择器**：在文本节点和 LoRA 节点的输入框左下角提供快捷按钮

## 使用示例

### 批量保存提示词到独立文件
1. 将多行文本连接到 **Save String to Text File** 的 `text` 输入
2. 设置 `save_mode` 为 `multiple_files`
3. 每行文本保存为一个独立文件

### 批量处理文本文件
1. 使用 **Save String to Text File**（multiple_files 模式）生成文件
2. 配合 for 循环使用 **Load Text Files from Folder**
3. 设置 `max_files` 与文件总数一致
4. 每次循环加载一个文件的内容

### 自定义名称保存图片
1. 将图片输出连接到 **Save Image to Folder**
2. 在 `file_name` 中输入自定义文件名
3. 选择图片格式，图片保存到指定目录

### 使用 LoRA 触发词（单 LoRA）
1. 添加 LoRA 加载器节点，选择一个 LoRA 模型
2. 在 `trigger_word` 输入框中填入触发词
3. 将输出连接到 CLIP Text Encode 的文本输入
4. 执行工作流后，触发词自动保存

### 多 LoRA 触发词链接
1. 串联两个 LoRA 加载器节点
2. 第一个节点的输出连接到第二个节点的 `upstream_trigger_word`
3. 触发词自动合并为 `"触发词A, 触发词B"` 格式

### 使用触发词选择器
1. 在文本节点或 LoRA 节点输入框左下角找到图标按钮
2. **左键点击** 弹出触发词选择弹窗
3. 已保存的触发词：点击直接应用
4. 未保存的 LoRA：输入并保存

### 使用模型预览图管理
1. 在节点输入框左下角找到图标按钮
2. **右键点击** 弹出模型预览图管理窗口
3. 自动扫描工作流中的模型加载器节点
4. 点击 `[增加]` 或 `[修改]` 上传预览图

### 使用右键菜单悬停预览
1. 在模型加载器节点上右键打开模型选择菜单
2. 鼠标悬停在模型名称上，自动弹出预览图
3. 点击菜单或按鼠标任意键隐藏预览图

## 文件结构

```
Comfyui-txtnode/
── __init__.py                    # 插件入口，V3 扩展注册
├── server.py                      # API 路由（触发词 + 模型预览图）
├── requirements.txt               # 项目依赖
├── Comfyui-txtnode.json           # 节点中文翻译配置
├── lora_trigger_words.json        # 触发词配置文件（自动生成）
│
├── nodes/                         # 后端节点逻辑
│   ├── __init__.py                # 节点类统一导出
│   ├── utils.py                   # 路径工具函数
│   ├── save_string.py             # 保存字符串到文本节点
│   ├── save_image.py              # 保存图像到文件夹节点
│   ├── load_text.py               # 批量加载文本文件节点
│   ├── resize_pad.py              # 调整图像尺寸填充节点
│   ├── lora_loader_node.py        # LoRA 加载器（仅模型）
│   ├── lora_loader_full_node.py   # LoRA 加载器（完整版）
│   ├── lora_prompt_encoder.py     # LoRA 提示词编码器
│   └── trigger_word_manager.py    # 触发词配置管理
│
── web/                           # 前端扩展
│   ├── icon.png                   # TW 按钮图标
│   ├── icon2.png                  # 操作按钮图标
│   ├── lora_loader.js             # LoRA 加载器前端扩展
│   ├── lora_prompt_encoder.js     # LoRA 提示词编码器 DOM UI
│   ├── trigger_word_picker.js     # 触发词选择器
│   ├── model_preview.js           # 右键菜单悬停预览图
│   ├── model_preview_manager.js   # 模型预览图管理弹窗
│   └── utils/
│       ├── trigger-word-api.js    # 触发词 API 封装
│       └── lora-actions.js        # LoRA 操作共享工具
│
└── workflow/                      # 示例工作流
    ├── workflow.json
    └── sdxl工作流示例.json
```

## 技术架构

- **V3 API**：所有节点继承 `io.ComfyNode`，使用 `define_schema()` + `execute()` 模式
- **扩展注册**：通过 `ComfyExtension` + `comfy_entrypoint()` 注册
- **前端扩展**：`WEB_DIRECTORY = "./web"` 加载前端 JS
  - `lora_loader.js`：LoRA 节点触发词管理
  - `lora_prompt_encoder.js`：LoRA 提示词编码器完整 DOM UI
  - `trigger_word_picker.js`：触发词选择器
  - `model_preview.js`：右键菜单悬停预览图
  - `model_preview_manager.js`：模型预览图管理弹窗
- **API 服务**：`server.py` 注册 HTTP 路由
  - `POST /comfyui-txtnode/save_trigger_word` - 保存触发词
  - `GET /comfyui-txtnode/get_trigger_word` - 获取单个触发词
  - `GET /comfyui-txtnode/get_all_trigger_words` - 获取所有触发词
  - `GET /model_preview/get_image_by_name` - 获取模型预览图
  - `POST /model_preview/upload_preview_image` - 上传模型预览图

## 依赖

- ComfyUI（支持 V3 API 的版本）
- Python 3.10+
- Pillow（图片处理）
- numpy（数组操作）
- torch（张量处理）
- aiohttp（HTTP 路由）
- typing_extensions（类型支持）

</div>

<div class="lang-en" style="display:none">

## Introduction

A ComfyUI custom node plugin that provides text file management, image processing, LoRA loading, and trigger word management utilities.

**Core Features:**
- **Text Nodes**: Save strings to files, load text files from folders
- **Image Nodes**: Save images to folders, resize and pad images, remove padding
- **LoRA Loaders**: Three versions of LoRA loaders with trigger word management
- **LoRA Prompt Encoder**: Integrated multi-LoRA selection, prompt editing and CLIP text encoding
- **Trigger Word Picker**: Quick trigger word selection buttons on text and LoRA nodes
- **Model Preview Manager**: Right-click button to open manager dialog, add/modify model previews
- **Hover Preview**: Automatically display preview images when hovering over model names in context menus

## Installation

1. Clone or download this repository to ComfyUI's `custom_nodes` directory:
   ```
   ComfyUI/custom_nodes/Comfyui-txtnode/
   ```
2. Restart ComfyUI
3. Nodes will appear under `Utils`, `image/transform`, and `loaders/lora` categories

## Node List

| Node | Category | Description |
|------|----------|-------------|
| **Save String to Text File** | `Utils` | Save text content to local file |
| **Save Image to Folder** | `Utils` | Save image tensor to specified folder |
| **Load Text Files from Folder** | `Utils` | Load text files by index from folder |
| **Resize and Pad Image** | `image/transform` | Resize image and pad to target size |
| **Remove Pad from Image** | `image/transform` | Remove padding, restore original size |
| **LoRA Loader (Model Only)** | `loaders/lora` | Load LoRA to model only (no CLIP) |
| **LoRA Loader (Full)** | `loaders/lora` | Load LoRA to both model and CLIP |
| **LoRA Prompt Encoder** | `loaders/lora` | Multi-LoRA selection + prompt editing + CLIP encoding |

## Node Parameters

### Save String to Text File

Save text content to file. Supports single file append and multiple file split modes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `text` | STRING | Yes | - | Text content to save |
| `file_name` | STRING | Yes | `output` | File name (without extension) |
| `extension` | STRING | Yes | `txt` | File extension |
| `encoding` | COMBO | Yes | `utf-8` | Encoding: utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | Yes | `single_file` | Save mode: single_file / multiple_files |
| `directory_path` | STRING | No | ComfyUI/output | Target directory path |

**Output**: `file_path` - Absolute path of saved file

- `single_file`: All output appended to same file
- `multiple_files`: Split by newlines, each line saved as separate file

### Save Image to Folder

Save image tensor to specified folder.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `images` | IMAGE | Yes | - | Image tensor (supports batches) |
| `file_name` | STRING | Yes | `""` | File name (empty for auto-increment) |
| `image_format` | COMBO | Yes | `png` | Image format: png / jpg / jpeg / webp |
| `output_folder` | STRING | No | ComfyUI/output | Output folder path |

**Output**: `folder_path` - Absolute path of output folder

- Specified `file_name`: Later images overwrite earlier ones
- Empty `file_name`: Auto-increment naming `image_1.png`, `image_2.png`...

### Load Text Files from Folder

Load `.txt` files by index, designed for batch processing with for loops.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `folder_path` | STRING | Yes | ComfyUI/output | Directory containing .txt files |
| `max_files` | INT | Yes | `10` | Maximum file count (1-999) |
| `index` | INT | Yes | `0` | File index to load (starts from 0) |

**Output**: `text` - File content, `file_name` - File name

### Resize and Pad Image

Resize image and pad to target size, supports multiple padding modes.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image` | IMAGE | Yes | - | Input image |
| `target_width` | INT | Yes | `512` | Target width |
| `target_height` | INT | Yes | `512` | Target height |
| `mode` | COMBO | Yes | `fit` | Padding mode: fit / fill / stretch |
| `background_color` | STRING | No | `#000000` | Background color (hex) |

**Output**: `IMAGE` - Resized image, `pad_info` - Padding info

### Remove Pad from Image

Remove image padding, restore original size. Use with "Resize and Pad Image" node.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `image` | IMAGE | Yes | - | Padded image |
| `pad_info` | STRING | Yes | - | Padding info (from upstream node) |

**Output**: `IMAGE` - Image restored to original size

### LoRA Loader (Model Only)

Apply LoRA to model only (not CLIP), supports trigger word management and multi-LoRA chaining.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | MODEL | Yes | - | Input model from upstream |
| `lora_name` | COMBO | Yes | - | LoRA model file selector |
| `strength_model` | FLOAT | Yes | `1.0` | LoRA model strength (-10.0 ~ 10.0) |
| `trigger_word` | STRING | Yes | `""` | Current LoRA trigger word |
| `upstream_trigger_word` | STRING | No | `""` | Upstream LoRA trigger word |

**Output**: `MODEL` - Model after LoRA, `trigger_word` - Merged trigger word

### LoRA Loader (Full)

Apply LoRA to both model and CLIP, supports trigger word management and multi-LoRA chaining.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | MODEL | Yes | - | Input model from upstream |
| `clip` | CLIP | Yes | - | Input CLIP from upstream |
| `lora_name` | COMBO | Yes | - | LoRA model file selector |
| `strength_model` | FLOAT | Yes | `1.0` | LoRA model strength (-10.0 ~ 10.0) |
| `strength_clip` | FLOAT | Yes | `1.0` | LoRA CLIP strength (-10.0 ~ 10.0) |
| `trigger_word` | STRING | Yes | `""` | Current LoRA trigger word |
| `upstream_trigger_word` | STRING | No | `""` | Upstream LoRA trigger word |

**Output**: `MODEL`, `CLIP` - Model and CLIP after LoRA, `trigger_word` - Merged trigger word

### LoRA Prompt Encoder

Integrated multi-LoRA selection, prompt editing and CLIP text encoding. Supports loading multiple LoRAs with independent strength control.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | MODEL | Yes | - | Input model from upstream |
| `clip` | CLIP | Yes | - | Input CLIP from upstream |
| `selected_loras_json` | STRING | Yes | `"[]"` | Selected LoRA list (JSON, generated by frontend UI) |
| `positive_prompt` | STRING | Yes | `""` | Positive prompt |
| `negative_prompt` | STRING | Yes | `""` | Negative prompt |

**Output**: `MODEL` - Model with all LoRAs applied, `CONDITIONING` - Positive, `NEGATIVE_CONDITIONING` - Negative

**Frontend UI Features**:
- Left panel: Positive/negative prompt editing + Selected LoRA list (with strength sliders)
- Right panel: Search box + Folder filter + Thumbnail grid + Pagination
- Left-click thumbnail: Edit trigger word
- Right-click thumbnail: Upload/modify preview image

## Trigger Word Management

LoRA loader nodes provide complete trigger word management:

- **Auto Save**: Automatically save trigger word to `lora_trigger_words.json` on execution
- **Auto Load**: Automatically fill in saved trigger word when switching LoRA selection
- **Multi-level Chaining**: Link multiple LoRA nodes via `upstream_trigger_word` port, trigger words auto-merge
- **Trigger Word Picker**: Quick buttons at bottom-left of input fields on text and LoRA nodes

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
3. Select image format, images saved to specified directory

### Using LoRA Trigger Words (Single LoRA)
1. Add LoRA loader node, select a LoRA model
2. Fill in trigger word in `trigger_word` input
3. Connect output to CLIP Text Encode text input
4. Trigger word auto-saved after workflow execution

### Multi-LoRA Trigger Word Chaining
1. Chain two LoRA loader nodes
2. Connect first node's output to second node's `upstream_trigger_word`
3. Trigger words auto-merge as `"TriggerA, TriggerB"` format

### Using Trigger Word Picker
1. Find icon button at bottom-left of input field
2. **Left-click** to open trigger word selection popup
3. Saved trigger words: Click to apply directly
4. Unsaved LoRAs: Input and save

### Using Model Preview Manager
1. Find icon button at bottom-left of input field
2. **Right-click** to open model preview manager
3. Auto-scans workflow for model loader nodes
4. Click `[Add]` or `[Edit]` to upload preview image

### Using Context Menu Hover Preview
1. Right-click on model loader node to open model selection menu
2. Hover over model name, preview image auto-appears
3. Click menu or any mouse button to hide preview

## File Structure

```
Comfyui-txtnode/
├── __init__.py                    # Plugin entry, V3 extension registration
├── server.py                      # API routes (trigger words + model previews)
├── requirements.txt               # Project dependencies
├── Comfyui-txtnode.json           # Node i18n (Chinese translations)
├── lora_trigger_words.json        # Trigger word config (auto-generated)
│
├── nodes/                         # Backend node logic
│   ├── __init__.py                # Node class exports
│   ├── utils.py                   # Path utility functions
│   ├── save_string.py             # Save string to text node
│   ├── save_image.py              # Save image to folder node
│   ├── load_text.py               # Batch load text files node
│   ├── resize_pad.py              # Resize and pad image node
│   ├── lora_loader_node.py        # LoRA loader (model only)
│   ├── lora_loader_full_node.py   # LoRA loader (full version)
│   ├── lora_prompt_encoder.py     # LoRA prompt encoder
│   └── trigger_word_manager.py    # Trigger word config manager
│
── web/                           # Frontend extensions
│   ├── icon.png                   # TW button icon
│   ├── icon2.png                  # Action button icon
│   ├── lora_loader.js             # LoRA loader frontend extension
│   ├── lora_prompt_encoder.js     # LoRA prompt encoder DOM UI
│   ├── trigger_word_picker.js     # Trigger word picker
│   ├── model_preview.js           # Context menu hover preview
│   ├── model_preview_manager.js   # Model preview manager dialog
│   └── utils/
│       ├── trigger-word-api.js    # Trigger word API wrapper
│       └── lora-actions.js        # LoRA action shared utilities
│
└── workflow/                      # Example workflows
    ├── workflow.json
    └── sdxl工作流示例.json
```

## Technical Architecture

- **V3 API**: All nodes inherit from `io.ComfyNode`, using `define_schema()` + `execute()` pattern
- **Extension Registration**: Via `ComfyExtension` + `comfy_entrypoint()`
- **Frontend Extensions**: `WEB_DIRECTORY = "./web"` loads frontend JS
  - `lora_loader.js`: LoRA node trigger word management
  - `lora_prompt_encoder.js`: LoRA prompt encoder full DOM UI
  - `trigger_word_picker.js`: Trigger word picker
  - `model_preview.js`: Context menu hover preview
  - `model_preview_manager.js`: Model preview manager dialog
- **API Service**: `server.py` registers HTTP routes
  - `POST /comfyui-txtnode/save_trigger_word` - Save trigger word
  - `GET /comfyui-txtnode/get_trigger_word` - Get single trigger word
  - `GET /comfyui-txtnode/get_all_trigger_words` - Get all trigger words
  - `GET /model_preview/get_image_by_name` - Get model preview image
  - `POST /model_preview/upload_preview_image` - Upload model preview

## Dependencies

- ComfyUI (V3 API compatible version)
- Python 3.10+
- Pillow (image processing)
- numpy (array operations)
- torch (tensor processing)
- aiohttp (HTTP routing)
- typing_extensions (type support)

</div>
