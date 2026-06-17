# ComfyUI Text Node 插件

> [English](./README_EN.md) | **中文**

基于 **ComfyUI V3 API** 构建的自定义节点插件，提供文本文件操作、图片处理、批量文件加载、LoRA 触发词管理以及模型预览图管理等实用功能。

---

## 功能特性

- **文本节点**：保存字符串到文件、从文件夹加载文本文件
- **图像节点**：保存图像到文件夹、调整图像尺寸填充、移除图像填充
- **LoRA 加载器**：两个版本的 LoRA 加载器，支持触发词管理
- **触发词选择器**：在文本节点和 LoRA 节点上提供快捷触发词选择按钮
- **模型预览图管理**：右键按钮打开管理弹窗，为模型添加/修改预览图
- **悬停预览**：右键菜单悬停模型名时自动显示预览图

---

## 节点列表

| 节点 | 分类 | 说明 |
|------|------|------|
| **Save String to Text File** | `Utils` | 将文本内容保存到本地文件 |
| **Save Image to Folder** | `Utils` | 将图片张量保存到指定文件夹 |
| **Load Text Files from Folder** | `Utils` | 按索引从文件夹加载文本文件（配合 for 循环） |
| **调整图像尺寸填充** | `image/transform` | 将图像调整尺寸并填充到指定大小 |
| **移除图像填充** | `image/transform` | 移除图像填充，恢复原始尺寸 |
| **LoRA加载器(仅模型)** | `loaders/lora` | 加载 LoRA 到模型（不含 CLIP），支持触发词管理 |
| **LoRA加载器(完整)** | `loaders/lora` | 同时加载 LoRA 到模型和 CLIP，支持触发词管理 |

---

## 安装

1. 将此仓库克隆或下载到 ComfyUI 的 `custom_nodes` 目录：
   ```
   ComfyUI/custom_nodes/Comfyui-txtnode/
   ```
2. 重启 ComfyUI
3. 节点分别出现在 `Utils`、`image/transform` 和 `loaders/lora` 分类下

---

## 节点参数

### Save String to Text File

将文本内容保存到文件。支持单文件追加和多文件分割两种模式。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | STRING | 是 | - | 要保存的文本内容（支持多行） |
| `file_name` | STRING | 是 | `output` | 文件名（不含扩展名） |
| `extension` | STRING | 是 | `txt` | 文件扩展名 |
| `encoding` | COMBO | 是 | `utf-8` | 编码格式：utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | 是 | `single_file` | 保存模式：single_file / multiple_files |
| `directory_path` | STRING | 否 | ComfyUI/output | 目标目录路径 |

**输出**：`file_path` - 保存文件的绝对路径

**模式说明**：
- `single_file`：所有输出追加到同一个文件（配合 for 循环时每次迭代追加一行）
- `multiple_files`：按换行符分割文本，每行保存为独立文件（`文件名_序号.扩展名`）

---

### Save Image to Folder

将图片张量保存到指定文件夹。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `images` | IMAGE | 是 | - | 图片张量（支持批次） |
| `file_name` | STRING | 是 | `""` | 文件名（留空自动递增命名） |
| `image_format` | COMBO | 是 | `png` | 图片格式：png / jpg / jpeg / webp |
| `output_folder` | STRING | 否 | ComfyUI/output | 输出文件夹路径 |

**输出**：`folder_path` - 输出文件夹的绝对路径

**文件名规则**：
- 指定 `file_name`：所有图片保存为该名称（批次中后面的图片会覆盖前面的）
- 留空 `file_name`：自动递增命名 `image_1.png`、`image_2.png`...

---

### Load Text Files from Folder

按索引从文件夹中加载 `.txt` 文件，专为 for 循环批量处理设计。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `folder_path` | STRING | 是 | ComfyUI/output | 包含 .txt 文件的目录 |
| `max_files` | INT | 是 | `10` | 最大文件数（1-999） |
| `index` | INT | 是 | `0` | 要加载的文件索引（从 0 开始） |

**输出**：`text` - 文件内容，`file_name` - 文件名

**使用方式**：
1. 设置 `max_files` 为文件总数
2. 将 for 循环的 index 连接到节点的 `index` 输入
3. 每次循环依次加载第 0、1、2...N 个文件

---

### 调整图像尺寸填充

将图像调整尺寸并填充到指定大小，支持多种填充模式。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | IMAGE | 是 | - | 输入图像 |
| `target_width` | INT | 是 | `512` | 目标宽度 |
| `target_height` | INT | 是 | `512` | 目标高度 |
| `mode` | COMBO | 是 | `fit` | 填充模式：fit / fill / stretch |
| `background_color` | STRING | 否 | `#000000` | 背景颜色（十六进制） |

**输出**：`IMAGE` - 调整后的图像，`pad_info` - 填充信息（用于还原）

---

### 移除图像填充

移除图像填充，恢复原始尺寸。配合"调整图像尺寸填充"节点使用。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | IMAGE | 是 | - | 填充后的图像 |
| `pad_info` | STRING | 是 | - | 填充信息（来自上游节点） |

**输出**：`IMAGE` - 恢复原始尺寸的图像

---

### LoRA加载器(仅模型)

将 LoRA 应用到模型（不应用到 CLIP），支持触发词管理和多 LoRA 触发词链接。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | MODEL | 是 | - | 来自上游的输入模型 |
| `lora_name` | COMBO | 是 | - | LoRA 模型文件选择器 |
| `strength_model` | FLOAT | 是 | `1.0` | LoRA 模型强度（-10.0 ~ 10.0） |
| `trigger_word` | STRING | 是 | `""` | 当前 LoRA 的触发词（多行输入） |
| `upstream_trigger_word` | STRING | 否 | `""` | 上游 LoRA 的触发词（端口输入） |

**输出**：`MODEL` - 应用 LoRA 后的模型，`trigger_word` - 合并后的触发词

---

### LoRA加载器(完整)

同时将 LoRA 应用到模型和 CLIP，支持触发词管理和多 LoRA 触发词链接。

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | MODEL | 是 | - | 来自上游的输入模型 |
| `clip` | CLIP | 是 | - | 来自上游的输入 CLIP |
| `lora_name` | COMBO | 是 | - | LoRA 模型文件选择器 |
| `strength_model` | FLOAT | 是 | `1.0` | LoRA 模型强度（-10.0 ~ 10.0） |
| `strength_clip` | FLOAT | 是 | `1.0` | LoRA CLIP 强度（-10.0 ~ 10.0） |
| `trigger_word` | STRING | 是 | `""` | 当前 LoRA 的触发词（多行输入） |
| `upstream_trigger_word` | STRING | 否 | `""` | 上游 LoRA 的触发词（端口输入） |

**输出**：`MODEL` - 应用 LoRA 后的模型，`CLIP` - 应用 LoRA 后的 CLIP，`trigger_word` - 合并后的触发词

---

## 触发词管理特性

LoRA 加载器节点提供完整的触发词管理功能：

- **自动保存**：执行时将 `trigger_word` 自动保存到 `lora_trigger_words.json`
- **自动加载**：切换 LoRA 选择时，自动回填已保存的触发词
- **多级链接**：通过 `upstream_trigger_word` 端口链接多个 LoRA 节点，触发词自动合并
- **触发词选择器**：在文本节点和 LoRA 节点的输入框左下角提供快捷按钮

---

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
3. 选择图片格式
4. 图片保存到指定目录

### 使用 LoRA 触发词（单 LoRA）
1. 添加 **LoRA加载器(仅模型)** 或 **LoRA加载器(完整)** 节点
2. 选择一个 LoRA 模型
3. 在 `trigger_word` 输入框中填入该 LoRA 的触发词
4. 将 `trigger_word` 输出连接到 CLIP Text Encode 或 CR Text 的文本输入
5. 执行工作流后，触发词自动保存

### 多 LoRA 触发词链接
1. 串联两个 LoRA 加载器节点
2. 第一个节点的 `trigger_word` 输出连接到第二个节点的 `upstream_trigger_word` 输入
3. 两个节点的触发词自动合并为 `"触发词A, 触发词B"` 格式输出

### 使用触发词选择器
1. 在 **CLIP Text Encode**、**CR Text** 或 **LoRA 加载器** 节点的输入框左下角找到图标按钮
2. **左键点击** 按钮，弹出触发词选择弹窗
3. 弹窗显示已保存的触发词列表和未保存的 LoRA
   - **已保存的触发词**：点击直接应用（LoRA 节点会检查 LoRA 名称是否匹配）
   - **未保存的 LoRA**：提供输入框和保存按钮，保存后自动写入节点输入框
   - **编辑功能**：点击"修改"按钮可编辑或删除已保存的触发词

### 使用模型预览图管理
1. 在文本节点或 LoRA 节点的输入框左下角找到图标按钮
2. **右键点击** 该按钮，弹出模型预览图管理窗口
3. 窗口自动扫描工作流中的模型加载器节点：
   - CheckpointLoaderSimple（Checkpoint 模型）
   - LoraLoader / LoraLoaderModelOnly / LoRALoaderModelOnly / LoRALoaderFull（LoRA 模型）
   - UNETLoader / UnetLoader（UNet/Diffusion 模型）
4. 列表显示所有检测到的模型，每个模型旁边标注类型
   - **有预览图**：显示缩略图 + `[修改]` 按钮
   - **无预览图**：显示 `[增加]` 按钮
5. 点击 `[增加]` 或 `[修改]` 按钮：
   - 弹出文件选择对话框，选择图片文件（支持 png/jpg/webp）
   - 显示图片预览确认对话框
   - 确认后图片自动重命名为模型同名，保存到模型所在目录
6. 上传成功后列表自动刷新

### 使用右键菜单预览图（悬停预览）
1. 在模型加载器节点（Checkpoint/LoRA/UNet）上右键打开模型选择菜单
2. 鼠标悬停在模型名称上，自动弹出同名预览图
3. 预览图显示在菜单右侧，超出屏幕时自动翻转到左侧
4. 点击菜单或按鼠标任意键，预览图自动隐藏

---

## 文件结构

```
Comfyui-txtnode/
├── __init__.py                    # 插件入口，V3 扩展注册（ComfyExtension + comfy_entrypoint）
├── nodes/                         # 文件操作节点包
│   ├── __init__.py                # 节点重新导出
│   ├── utils.py                   # 共享路径工具函数
│   ├── save_string.py             # 保存字符串到文本节点
│   ├── save_image.py              # 保存图像到文件夹节点
│   ├── load_text.py               # 批量加载文本文件节点
│   └── resize_pad.py              # 调整图像尺寸填充节点
├── lora_loader_node.py            # LoRA 加载器节点实现（仅模型）
├── lora_loader_full_node.py       # LoRA 加载器节点实现（完整版）
├── trigger_word_manager.py        # 触发词配置管理模块（集中读写逻辑）
├── server.py                      # API 路由（触发词 + 模型预览图）
├── lora_trigger_words.json        # 触发词配置文件（自动生成）
├── requirements.txt               # 项目依赖
├── web/
│   ├── icon.png                   # 触发词选择器图标
│   ├── lora_loader.js             # LoRA 节点前端扩展（触发词管理）
│   ├── trigger_word_picker.js     # 触发词选择器（文本节点 + LoRA 节点）
│   ├── model_preview.js           # 右键菜单悬停预览图功能
│   ├── model_preview_manager.js   # 模型预览图管理弹窗（右键 TW 按钮）
│   └── utils/
│       └── trigger-word-api.js    # 触发词 API 封装模块
├── CLAUDE.md                      # 项目开发规范
├── README.md                      # 本文档（中文）
└── README_EN.md                   # 英文文档
```

---

## 技术架构

- **V3 API**：所有节点继承 `io.ComfyNode`，使用 `define_schema()` + `execute()` 模式
- **扩展注册**：通过 `ComfyExtension` + `comfy_entrypoint()` 注册（ComfyUI 新版入口）
- **前端扩展**：`WEB_DIRECTORY = "./web"` 加载前端 JS 文件
  - `lora_loader.js`：LoRA 节点触发词管理（保存按钮、自动加载、右键菜单）
  - `trigger_word_picker.js`：触发词选择器（支持文本节点和 LoRA 节点）
  - `model_preview.js`：右键菜单悬停预览图（Monkey Patch LiteGraph.ContextMenu）
  - `model_preview_manager.js`：模型预览图管理弹窗（右键 TW 按钮打开）
- **API 服务**：`server.py` 注册 HTTP 路由
  - `POST /comfyui-txtnode/save_trigger_word` - 保存触发词
  - `GET /comfyui-txtnode/get_trigger_word` - 获取单个触发词
  - `GET /comfyui-txtnode/get_all_trigger_words` - 获取所有触发词
  - `GET /model_preview/get_image_by_name` - 获取模型同名预览图
  - `POST /model_preview/upload_preview_image` - 上传模型预览图（JSON + base64）

---

## 依赖

- ComfyUI（支持 V3 API 的版本）
- Python 3.10+
- Pillow（图片处理）
- numpy（数组操作）
- torch（张量处理）
- aiohttp（HTTP 路由）
- typing_extensions（类型支持）
