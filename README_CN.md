# ComfyUI Text Node 插件

[English](./README.md) | **简体中文**

ComfyUI 自定义节点插件集合，共 12 个节点，覆盖文本文件批处理、图像填充与还原、LoRA 加载与触发词管理、条件路由控制、Photoshop 实时桥接。本文档按节点用法组织，每个节点包含：**作用 → 接线方式 → 参数说明 → 使用步骤**。

## 安装

### 通过 ComfyUI Manager 安装（推荐）

在 ComfyUI Manager 中搜索 `Comfyui-txtnode` 并点击安装，重启 ComfyUI。

### 手动安装

1. 克隆本仓库到 ComfyUI 的 `custom_nodes` 目录：
   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/your-username/Comfyui-txtnode.git
   ```
2. 安装依赖：`pip install -r requirements.txt`
3. 重启 ComfyUI

## 节点一览

双击画布或右键 → Add Node，在以下分类中搜索节点名（表中为 ComfyUI 界面显示名）：

| 节点 | 分类 | 作用 |
|------|------|------|
| Save String to Text File | `Utils` | 文本保存到本地文件（单文件追加 / 多文件分割） |
| Save Image to Folder | `Utils` | 图片保存到指定文件夹 |
| Load Text Files from Folder | `Utils` | 按索引加载 .txt 文件，配合 for 循环批处理 |
| 调整图像尺寸填充 | `txtnode` | 图像等比缩放并居中填充到正方形画布 |
| 移除图像填充 | `txtnode` | 按填充元数据裁剪，恢复原始尺寸 |
| LoRA加载器(仅模型) | `loaders/lora` | LoRA 仅应用到模型，含触发词管理 |
| LoRA加载器(完整) | `loaders/lora` | LoRA 同时应用到模型和 CLIP |
| LoRA提示词编码器 | `loaders/lora` | 多 LoRA 选择 + 提示词编辑 + CLIP 编码一体化 |
| 是否阻断 | `txtnode` | 手动控制万能线路：透传 / 置空 / 静默中断 |
| 是否存在 | `txtnode` | 检测万能线路有无数据，输出占位值与布尔结果 |
| 从PS获取图像 | `PS Bridge` | 读取 Photoshop 导出的画布和遮罩 |
| 发送图像到PS | `PS Bridge` | 将图像发送回 Photoshop |

---

## 文本 / 文件工具

### Save String to Text File

**作用**：将文本写入本地文件。`single_file` 模式把所有内容追加到同一文件（for 循环多次执行时逐次累积）；`multiple_files` 模式按换行符分割，每行保存为独立文件。

**接线**：上游任意文本源（提示词节点、文本拼接节点等）连到 `text` 输入。输出 `file_path` 为保存后的绝对路径，一般无需连接下游。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | STRING | - | 要保存的文本（多行输入框） |
| `file_name` | STRING | `output` | 文件名（不含扩展名） |
| `extension` | STRING | `txt` | 文件扩展名 |
| `encoding` | COMBO | `utf-8` | 编码：utf-8 / gbk / utf-16 / ascii |
| `save_mode` | COMBO | `single_file` | 保存模式：single_file / multiple_files |
| `directory_path` | STRING | ComfyUI/output | 目标目录（可选，留空用默认输出目录） |

**输出**：`file_path` — 文件绝对路径（multiple_files 模式返回第一个文件的路径）

**使用步骤**：
1. 批量保存提示词到独立文件：`text` 接多行文本 → `save_mode` 选 `multiple_files` → 每行保存为 `{file_name}_1.txt`、`{file_name}_2.txt`…（空行自动跳过）
2. for 循环累积到单文件：`save_mode` 保持 `single_file`，每次执行自动追加（行间自动插入换行符）

### Save Image to Folder

**作用**：将图片保存到指定文件夹，支持批次和自定义命名。

**接线**：上游图像输出（VAE Decode、KSampler 后处理等）连到 `images`。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `images` | IMAGE | - | 图片张量（支持批次） |
| `file_name` | STRING | `""` | 文件名；留空则自动递增命名 |
| `image_format` | COMBO | `png` | 格式：png / jpg / jpeg / webp |
| `output_folder` | STRING | ComfyUI/output | 输出文件夹（可选） |

**输出**：`folder_path` — 输出文件夹绝对路径

**使用步骤**：
1. 将图片输出连到 `images`
2. 指定 `file_name`：批次中后面的图片会覆盖前面的；留空则自动递增命名 `image_1.png`、`image_2.png`…（跳过已存在的编号）
3. 选择格式，执行后图片保存到指定目录

### Load Text Files from Folder

**作用**：按索引从文件夹加载 `.txt` 文件，专为 for 循环批量处理设计，每次执行加载 1 个文件。

**接线**：for 循环节点的 `index` 输出连到本节点的 `index` 输入；`text` 输出连到下游提示词输入（如 CLIP Text Encode）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `folder_path` | STRING | ComfyUI/output | 包含 .txt 文件的目录 |
| `max_files` | INT | `10` | 最大文件数（1-999，按文件名排序取前 N 个） |
| `index` | INT | `0` | 要加载的文件索引（从 0 开始） |

**输出**：`text` — 文件内容，`file_name` — 文件名

**使用步骤**：
1. 先用 **Save String to Text File**（multiple_files 模式）生成文件
2. 添加 for 循环，循环次数与文件总数一致
3. `max_files` 设为文件总数，for 循环的 index 连到本节点 `index`
4. 每次循环依次加载第 0、1、2… 个文件（按文件名排序，UTF-8 读取）

---

## 图像处理

### 调整图像尺寸填充

**作用**：将图像等比缩放并居中填充到正方形画布（黑色填充），同时输出填充元数据 `image_info`，供下游"移除图像填充"节点精确裁剪。适合把任意比例图像送入只接受正方形输入的模型。

**接线**：上游图像连到 `input_image`；`output_image` 连到后续处理；`image_info` **必须**连到"移除图像填充"的 `image_info` 输入才能还原。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_image` | IMAGE | - | 输入图像 |
| `target_size` | INT | `1024` | 目标尺寸（64-8192，自动吸附到对齐倍数） |
| `resolution_multiple` | INT | `8` | 对齐倍数（0-128，步长 8；为 0 时不修正 target_size） |
| `upscale_method` | COMBO | `lanczos` | 缩放算法：lanczos / bicubic / area / nearest |
| `resize_and_pad` | BOOLEAN | `true` | 关闭时旁路直通，原图原样输出 |

**输出**：`output_image` — 填充后的正方形图像，`image_info` — 填充元数据（IMAGE_INFO 类型）

**使用步骤**：
1. 图像连入 `input_image`，设置 `target_size`（如 1024）
2. 缩放规则：按宽高较小比例等比缩放，完整放入正方形画布并居中，四周黑色填充
3. 将 `image_info` 输出跨节点连到下游"移除图像填充"

### 移除图像填充

**作用**：根据 `image_info` 元数据裁剪填充区域，恢复图像原始宽高比。配合"调整图像尺寸填充"成对使用。

**接线**：处理后的图像连到 `input_image`；上游"调整图像尺寸填充"的 `image_info` 输出连到本节点 `image_info`。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_image` | IMAGE | - | 待裁剪图像 |
| `image_info` | IMAGE_INFO | - | 填充元数据（来自上游节点） |
| `remove_pad` | BOOLEAN | `true` | 关闭时旁路直通 |
| `latent_scale` | FLOAT | `0.0` | Latent 空间缩放因子（可选，用于精确匹配） |

**输出**：`output_image` — 恢复原始尺寸的图像

**使用步骤**：
1. 图像经过潜空间处理（如 KSampler）后尺寸可能变化，本节点会按当前尺寸与 `original_size` 的比例自动缩放裁剪坐标
2. 若从 Latent 反推的缩放比例有偏差，可手动填 `latent_scale`：与自动计算值在 10% 容差内时优先采用手动值
3. `image_info` 无效或填充为零时直接透传原图，不会报错

---

## LoRA 加载器

三个 LoRA 节点均支持**触发词管理**：执行时触发词自动保存到 `lora_trigger_words.json`；切换 LoRA 选择时自动回填已保存的触发词；通过 `upstream_trigger_word` 端口可多级链接，触发词自动合并。

### LoRA加载器(仅模型)

**作用**：将 LoRA 只应用到模型（不应用到 CLIP），适合不需要改变文本编码风格的 LoRA。

**接线**：上游 MODEL 连到 `model`；`MODEL` 输出连向 KSampler；`trigger_word` 输出连到 CLIP Text Encode 的文本输入（可与提示词拼接后使用）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | MODEL | - | 上游输入模型 |
| `lora_name` | COMBO | - | LoRA 文件选择器（扫描 loras 目录） |
| `strength_model` | FLOAT | `1.0` | 模型强度（-10.0 ~ 10.0，步长 0.01） |
| `trigger_word` | STRING | `""` | 当前 LoRA 的触发词（多行） |
| `upstream_trigger_word` | STRING | `""` | 上游 LoRA 的触发词（可选输入端口） |

**输出**：`MODEL` — 应用 LoRA 后的模型，`trigger_word` — 合并后的触发词（`"上游触发词, 当前触发词"` 格式，空值不参与拼接）

**使用步骤**：
1. 串联到模型加载器与 KSampler 之间，选择 LoRA 并调节强度
2. 在 `trigger_word` 填入触发词，执行后自动保存
3. 多 LoRA 链接：第一个加载器的 `trigger_word` 输出连到第二个的 `upstream_trigger_word`，触发词自动合并
4. **触发词选择器**：输入框左下角图标按钮，**左键点击**弹出选择弹窗——已保存的触发词点击直接应用，未保存的 LoRA 可输入并保存

### LoRA加载器(完整)

**作用**：将 LoRA 同时应用到模型和 CLIP，适合带文本编码器部分的 LoRA（如风格、概念类）。

**接线**：上游 MODEL 连 `model`、CLIP 连 `clip`；`MODEL`/`CLIP` 输出继续向下游传递；`trigger_word` 输出连到 CLIP Text Encode。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | MODEL | - | 上游输入模型 |
| `clip` | CLIP | - | 上游输入 CLIP |
| `lora_name` | COMBO | - | LoRA 文件选择器 |
| `strength_model` | FLOAT | `1.0` | 模型强度（-10.0 ~ 10.0） |
| `strength_clip` | FLOAT | `1.0` | CLIP 强度（-10.0 ~ 10.0） |
| `trigger_word` | STRING | `""` | 当前 LoRA 的触发词 |
| `upstream_trigger_word` | STRING | `""` | 上游 LoRA 的触发词（可选输入端口） |

**输出**：`MODEL`、`CLIP` — 应用 LoRA 后的模型和 CLIP，`trigger_word` — 合并后的触发词

**使用步骤**：与"仅模型"版相同，额外需要传递 CLIP 链路。

### 模型预览图管理（适用于 LoRA 加载器及各类模型加载器节点）

- **右键点击**节点输入框左下角的图标按钮，弹出模型预览图管理窗口
- 自动扫描工作流中的模型加载器节点，点击 `[增加]` 或 `[修改]` 上传预览图
- 在模型加载器节点上**右键打开模型选择菜单**，鼠标悬停模型名称自动弹出预览图，点击菜单或任意鼠标键隐藏

### LoRA提示词编码器

**作用**：集成多 LoRA 选择、提示词编辑和 CLIP 文本编码于一体的节点。一个节点完成"加载 N 个 LoRA + 写正/负面提示词 + 输出 CONDITIONING"，替代传统的多个 LoRA Loader 串联 + 两个 CLIP Text Encode。

**接线**：上游 MODEL 连 `model`、CLIP 连 `clip`；`MODEL` 连 KSampler；`CONDITIONING` / `NEGATIVE_CONDITIONING` 分别连 KSampler 的正/负面条件。`positive_prompt` / `negative_prompt` 为可选输入端口，可外接文本节点覆盖面板内提示词。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | MODEL | - | 上游输入模型 |
| `clip` | CLIP | - | 上游输入 CLIP |
| `positive_prompt` | STRING | `""` | 正面提示词（可选输入端口） |
| `negative_prompt` | STRING | `""` | 负面提示词（可选输入端口） |

**输出**：`MODEL` — 应用所有已选 LoRA 后的模型，`CONDITIONING` — 正面条件，`NEGATIVE_CONDITIONING` — 负面条件

**前端面板布局**：
- 左侧：正面/负面提示词编辑区 + 已选 LoRA 列表（每项带强度滑块、禁用开关、✕ 移除按钮）
- 右侧：搜索框 + 文件夹筛选 + LoRA 缩略图网格 + 分页控制

**使用步骤**：
1. 右侧网格中点击缩略图将 LoRA 加入已选列表，其触发词自动追加到正面提示词末尾
2. 在左侧调节每个 LoRA 的强度，编写正/负面提示词
3. 理解两种状态的区别：
   - **禁用**（toggle 开关）：临时暂停生效——跳过模型加载、从提示词移除触发词，但条目和强度保留，再拨回即恢复
   - **移除**（✕ 按钮 / 点击启用中的卡片）：永久删除条目并移除其触发词
4. 左键点击缩略图：编辑该 LoRA 的触发词；右键点击缩略图：上传/修改预览图
5. **风格提示词卡片**：面板内置 9 种预设艺术风格卡片（动漫CG、二分动漫、3D平面、像素、卡通色块、可爱2头、手绘画笔、水彩、简笔动漫），点击即向提示词注入对应风格；支持自定义添加/编辑/删除，用户卡片独立存储，插件更新不丢失

---

## 条件路由

用于在工作流中控制数据线路的通断。两个节点通过**万能线路**（可连接任意类型数据的插槽）协作。

### 是否阻断

**作用**：手动控制一条线路通断的开关节点。关闭时数据原样透传；打开后按**阻断模式**决定下游收到空值还是整条支路静默跳过。

**接线**：任意类型数据连到 `any` 输入，`any` 输出连到下游，串接在需要开关的线路中间。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `block_switch` | BOOLEAN | `false` | 阻断开关：开=阻断，关=通过 |
| `block_mode` | COMBO | `仅输出空值` | 阻断模式：仅输出空值 / 中断后续分支 |
| `any` | AnyType | - | 万能线路输入（可选） |

**输出**：`any` — 透传/置空/阻断后的线路

**两种阻断模式**：
- **仅输出空值**：输出 None，下游节点仍会执行，需自行容错
- **中断后续分支**：下游整条支路静默跳过，不报错、省算力（等效于 Ctrl+M 禁用支路）

**使用步骤**：
1. 把节点串进线路（如 KSampler 与解码器之间）
2. 关闭开关正常出图；打开开关选择模式，临时切断该支路而无需删除连线

### 是否存在

**作用**：检测万能线路上有无有效数据。有数据时透传并输出布尔 `true`；为空时按线路类型输出**占位值**并输出 `false`，保证下游类型校验不报错。常与"是否阻断"或切换节点配合，实现"有图则处理、无图则跳过"的分支逻辑。

**接线**：待检测线路连到 `any`；`any` 输出（透传值或占位值）连下游数据流；`布尔` 输出连到需要判断真假的节点。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `any` | AnyType | - | 万能线路输入（可选） |

**输出**：`any` — 原数据或占位值，`布尔` — 是否存在有效数据

**占位值规则**（线路为空时按类型生成）：

| 类型 | 占位值 |
|------|--------|
| IMAGE | 64×64 黑图 |
| MASK | 64×64 全黑遮罩 |
| LATENT | 1×4×1×1 空潜空间 |
| CONDITIONING | 空列表 |
| STRING / INT / FLOAT / BOOLEAN | `""` / `0` / `0.0` / `False` |
| MODEL / CLIP / VAE | None（无法凭空构造有效对象） |

**判空细节**：
- 纯黑遮罩、以及可见度低于 2% 的近黑残差遮罩视为空
- `0` 和 `False` 是有效内容，不判为空
- 前端自动识别万能线路类型，节点标签随来源类型变化

**使用步骤**：
1. 将可能为空的线路（如"是否阻断"的输出）连到 `any`
2. 下游直接消费 `any` 输出（空时得到占位值，不会类型报错）
3. 用 `布尔` 输出驱动条件分支（配合其他切换/循环节点）

---

## PS Bridge（Photoshop 桥接）

需要配合 Photoshop UXP 插件使用，通过文件交换实现 ComfyUI 与 Photoshop 之间的实时图像传输。

### 从PS获取图像

**作用**：从 ComfyUI input 目录读取 Photoshop 导出的画布和遮罩。

**接线**：`image` 输出连到图像输入（如 VAE Encode、IPAdapter），`mask` 输出连到遮罩输入（如 Inpaint 流程）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `image_filename` | STRING | `""` | 画布文件名（可选，默认 `xyps_canvas.png`） |
| `mask_filename` | STRING | `""` | 遮罩文件名（可选，默认 `xyps_mask.png`） |

**输出**：`image` — 画布图像，`mask` — 遮罩（取红色通道作为灰度遮罩）

**使用步骤**：
1. 在 Photoshop 中编辑画布和遮罩，由 UXP 插件导出到 ComfyUI input 目录
2. 节点自动检测文件变化并触发重新执行，无需手动刷新
3. 文件不存在时使用灰色棋盘格占位图和全白遮罩，工作流不报错
4. 局域网多用户场景：为每个用户指定不同文件名实现隔离

### 发送图像到PS

**作用**：将图像保存到 output 目录并通知 Photoshop 插件自动载入。纯输出节点，不向后传递图像张量。

**接线**：生成结果（VAE Decode 输出等）连到 `images`，作为工作流末端节点。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `images` | IMAGE | - | 输入图像张量 |
| `client_id` | STRING | `""` | 客户端 ID（可选，用于多用户输出隔离） |

**使用步骤**：
1. 把处理结果连到 `images`
2. 执行后图像写入 output 目录，Photoshop 端自动接收
3. 多用户场景下填写各自 `client_id` 隔离输出

---

## 示例工作流

`workflow/` 目录提供可直接导入的示例：

| 文件 | 内容 | 涉及节点 |
|------|------|----------|
| `workflow/workflow.json` | 文本批处理 + LoRA 加载 | Save String to Text File、Load Text Files from Folder、Save Image to Folder、LoRA加载器(仅模型) |
| `workflow/sdxl工作流示例.json` | SDXL 多 LoRA 生成 | LoRA提示词编码器 |
| `workflow/web.json` | Photoshop 实时协作 | 从PS获取图像、发送图像到PS |

导入方式：将 JSON 文件直接拖入 ComfyUI 画布窗口，或通过菜单加载。

---

## 依赖

- ComfyUI（支持 V3 API 的版本）
- Python 3.10+
- Pillow、numpy、aiohttp、typing_extensions

> 以上依赖包通常已随 ComfyUI 安装，一般无需额外安装。
