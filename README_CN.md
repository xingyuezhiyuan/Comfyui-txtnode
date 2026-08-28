# ComfyUI Text Node 插件

[English](./README.md) | **简体中文**

一个 ComfyUI 自定义节点插件集合，提供文本文件管理、图像处理、LoRA 加载与触发词管理、Photoshop 桥接、风格提示词卡片等实用功能。

## 安装

### 通过 ComfyUI Manager 安装（推荐）

在 ComfyUI Manager 中搜索 `Comfyui-txtnode` 并点击安装。

### 手动安装

1. 将此仓库克隆到 ComfyUI 的 `custom_nodes` 目录：
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/your-username/Comfyui-txtnode.git
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 重启 ComfyUI

## 节点一览

| 节点 | 分类 | 说明 |
|------|------|------|
| **Save String to Text File** | `Utils` | 将文本内容保存到本地文件 |
| **Save Image to Folder** | `Utils` | 将图片保存到指定文件夹 |
| **Load Text Files from Folder** | `Utils` | 按索引从文件夹加载文本文件 |
| **调整图像尺寸填充** | `txtnode` | 将图像等比缩放并填充到正方形画布 |
| **移除图像填充** | `txtnode` | 移除填充，恢复原始尺寸 |
| **LoRA加载器(仅模型)** | `loaders/lora` | 加载 LoRA 到模型（不含 CLIP） |
| **LoRA加载器(完整)** | `loaders/lora` | 同时加载 LoRA 到模型和 CLIP |
| **LoRA提示词编码器** | `loaders/lora` | 多 LoRA 选择 + 提示词编辑 + CLIP 编码 |
| **从PS获取图像** | `PS Bridge` | 从 Photoshop 获取画布和遮罩 |
| **发送图像到PS** | `PS Bridge` | 将图像发送到 Photoshop |

---

## 文本/文件工具

### Save String to Text File

将文本内容保存到文件。支持单文件追加和多文件分割两种模式。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | STRING | - | 要保存的文本内容 |
| `file_name` | STRING | `output` | 文件名（不含扩展名） |
| `extension` | STRING | `txt` | 文件扩展名 |
| `encoding` | COMBO | `utf-8` | 编码：utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | `single_file` | 保存模式：single_file / multiple_files |
| `directory_path` | STRING | ComfyUI/output | 目标目录路径（可选） |

**输出**：`file_path` — 保存文件的绝对路径

- `single_file`：所有内容追加到同一文件
- `multiple_files`：按换行符分割，每行保存为独立文件（适配 for 循环批量处理）

### Save Image to Folder

将图片保存到指定文件夹。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `images` | IMAGE | - | 图片张量（支持批次） |
| `file_name` | STRING | `""` | 文件名（留空自动递增命名） |
| `image_format` | COMBO | `png` | 图片格式：png / jpg / jpeg / webp |
| `output_folder` | STRING | ComfyUI/output | 输出文件夹路径（可选） |

**输出**：`folder_path` — 输出文件夹的绝对路径

- 指定 `file_name`：批次中后面的图片会覆盖前面的
- 留空 `file_name`：自动递增命名 `image_1.png`、`image_2.png`...

### Load Text Files from Folder

按索引从文件夹中加载 `.txt` 文件，专为 for 循环批量处理设计。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `folder_path` | STRING | ComfyUI/output | 包含 .txt 文件的目录 |
| `max_files` | INT | `10` | 最大文件数（1-999） |
| `index` | INT | `0` | 要加载的文件索引（从 0 开始） |

**输出**：`text` — 文件内容，`file_name` — 文件名

---

## 图像处理

### 调整图像尺寸填充

将图像等比缩放并居中填充到正方形画布，同时记录填充元数据供下游节点裁剪使用。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_image` | IMAGE | - | 输入图像 |
| `target_size` | INT | `1024` | 目标尺寸（64-8192，自动吸附到对齐倍数） |
| `resolution_multiple` | INT | `32` | 对齐倍数（8-128） |
| `upscale_method` | COMBO | `lanczos` | 缩放算法：lanczos / bicubic / area / nearest |
| `resize_and_pad` | BOOLEAN | `true` | 是否启用（关闭时旁路直通） |

**输出**：`output_image` — 调整后的图像，`image_info` — 填充元数据

### 移除图像填充

根据填充元数据裁剪填充区域，恢复图像原始宽高比。配合"调整图像尺寸填充"节点使用。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_image` | IMAGE | - | 填充后的图像 |
| `image_info` | IMAGE_INFO | - | 填充元数据（来自上游节点） |
| `remove_pad` | BOOLEAN | `true` | 是否启用（关闭时旁路直通） |
| `latent_scale` | FLOAT | `0.0` | Latent 空间缩放因子（可选，用于精确匹配） |

**输出**：`output_image` — 恢复原始尺寸的图像

---

## LoRA 加载器

### LoRA加载器(仅模型)

将 LoRA 应用到模型（不应用到 CLIP），支持触发词管理和多 LoRA 触发词链接。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | MODEL | - | 来自上游的输入模型 |
| `lora_name` | COMBO | - | LoRA 模型文件选择器 |
| `strength_model` | FLOAT | `1.0` | LoRA 模型强度（-10.0 ~ 10.0） |
| `trigger_word` | STRING | `""` | 当前 LoRA 的触发词 |
| `upstream_trigger_word` | STRING | `""` | 上游 LoRA 的触发词（可选） |

**输出**：`MODEL` — 应用 LoRA 后的模型，`trigger_word` — 合并后的触发词

### LoRA加载器(完整)

同时将 LoRA 应用到模型和 CLIP，支持触发词管理和多 LoRA 触发词链接。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | MODEL | - | 来自上游的输入模型 |
| `clip` | CLIP | - | 来自上游的输入 CLIP |
| `lora_name` | COMBO | - | LoRA 模型文件选择器 |
| `strength_model` | FLOAT | `1.0` | LoRA 模型强度（-10.0 ~ 10.0） |
| `strength_clip` | FLOAT | `1.0` | LoRA CLIP 强度（-10.0 ~ 10.0） |
| `trigger_word` | STRING | `""` | 当前 LoRA 的触发词 |
| `upstream_trigger_word` | STRING | `""` | 上游 LoRA 的触发词（可选） |

**输出**：`MODEL`、`CLIP` — 应用 LoRA 后的模型和 CLIP，`trigger_word` — 合并后的触发词

### LoRA提示词编码器

集成多 LoRA 选择、提示词编辑和 CLIP 文本编码。支持同时加载多个 LoRA 并独立调节强度。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | MODEL | - | 来自上游的输入模型 |
| `clip` | CLIP | - | 来自上游的输入 CLIP |
| `positive_prompt` | STRING | `""` | 正面提示词（可选输入端口） |
| `negative_prompt` | STRING | `""` | 负面提示词（可选输入端口） |

**输出**：`MODEL` — 应用所有 LoRA 后的模型，`CONDITIONING` — 正面条件，`NEGATIVE_CONDITIONING` — 负面条件

**前端 UI 功能**：
- 左侧面板：正面/负面提示词编辑 + 已选 LoRA 列表（含强度滑块）
- 右侧面板：搜索框 + 文件夹筛选 + 缩略图网格 + 分页控制
- 左键点击缩略图：编辑触发词
- 右键点击缩略图：上传/修改预览图

---

## PS Bridge（Photoshop 桥接）

需要配合 Photoshop UXP 插件使用，实现 ComfyUI 与 Photoshop 之间的实时图像传输。

### 从PS获取图像

从 ComfyUI input 目录读取 Photoshop 导出的画布和遮罩。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `image_filename` | STRING | `""` | 画布文件名（可选，默认 `xyps_canvas.png`） |
| `mask_filename` | STRING | `""` | 遮罩文件名（可选，默认 `xyps_mask.png`） |

**输出**：`image` — 画布图像，`mask` — 遮罩（取红色通道作为灰度遮罩）

- 文件不存在时使用灰色棋盘格占位图和全白遮罩
- 支持通过指定文件名实现局域网多用户隔离
- 自动检测文件变化触发重新执行

### 发送图像到PS

将图像保存到 output 目录并通知 Photoshop 插件。纯输出节点，不传递图像张量。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `images` | IMAGE | - | 输入图像张量 |
| `client_id` | STRING | `""` | 客户端 ID（可选，用于多用户输出隔离） |

---

## 前端功能

### 触发词管理

LoRA 加载器节点提供完整的触发词管理功能：

- **自动保存**：执行时将触发词自动保存到 `lora_trigger_words.json`
- **自动加载**：切换 LoRA 选择时，自动回填已保存的触发词
- **多级链接**：通过 `upstream_trigger_word` 端口链接多个 LoRA 节点，触发词自动合并

### 触发词选择器

在文本节点和 LoRA 节点输入框左下角提供快捷按钮：

- **左键点击** 弹出触发词选择弹窗
- 已保存的触发词：点击直接应用
- 未保存的 LoRA：输入并保存

### 模型预览图管理

- 在节点输入框左下角找到图标按钮
- **右键点击** 弹出模型预览图管理窗口
- 自动扫描工作流中的模型加载器节点
- 点击 `[增加]` 或 `[修改]` 上传预览图

### 右键菜单悬停预览

- 在模型加载器节点上右键打开模型选择菜单
- 鼠标悬停在模型名称上，自动弹出预览图
- 点击菜单或按鼠标任意键隐藏预览图

### 风格提示词卡片

提供多种预设艺术风格提示词卡片，可在 LoRA 提示词编码器中使用：

- 内置 9 种风格：动漫CG、二分动漫、3D平面、像素、卡通色块、可爱2头、手绘画笔、水彩、简笔动漫
- 支持自定义添加/编辑/删除风格卡片
- 用户卡片数据独立存储，插件更新不会丢失

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
3. 选择图片格式，图片保存到指定目录

### 图像等比缩放与还原
1. 使用 **调整图像尺寸填充** 将图像等比缩放到正方形画布
2. 将 `image_info` 输出连接到 **移除图像填充** 的 `image_info` 输入
3. 处理完成后，**移除图像填充** 自动裁剪恢复原始比例

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

### Photoshop 实时协作
1. 在 Photoshop 中编辑画布和遮罩
2. 使用 **从PS获取图像** 节点导入画布和遮罩
3. 连接处理流程
4. 使用 **发送图像到PS** 节点将结果回传到 Photoshop

---

## 适配插件

本插件与以下 ComfyUI 插件具有良好的兼容性或协作关系：

| 插件 | 关系 | 说明 |
|------|------|------|
| [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) | 安装管理 | 支持通过 Manager 安装和管理本插件 |
| [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) | 协作 | LoRA 加载器可与 Impact-Pack 的 Detailer 等节点配合使用 |
| [ComfyUI-Easy-Use](https://github.com/yolain/ComfyUI-Easy-Use) | 协作 | 文本/图像工具节点可与 Easy-Use 的批处理节点配合 |
| [comfyui-photoshop](https://github.com/NimaNzrii/comfyui-photoshop) | PS Bridge | 同为 Photoshop 桥接方案，本插件的 PS Bridge 节点提供独立的文件传输方案 |
| [ComfyUI-KJNodes](https://github.com/kijai/ComfyUI-KJNodes) | 协作 | 图像处理节点可与 KJNodes 的图像工具互补使用 |
| [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) | 协作 | 文本文件批量处理可与视频帧处理流程配合 |

---

## 依赖

- ComfyUI（支持 V3 API 的版本）
- Python 3.10+
- Pillow（图片处理）
- numpy（数组操作）
- aiohttp（HTTP 路由）
- typing_extensions（类型支持）

> 以上依赖包通常已随 ComfyUI 安装，一般无需额外安装。
