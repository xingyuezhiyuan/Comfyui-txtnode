# ComfyUI Prompt Assistant 技术架构文档

## 一、项目概述

ComfyUI Prompt Assistant (提示词小助手) 是一个 ComfyUI 自定义节点插件，为 CLIPTextEncode 等文本输入节点提供增强功能工具栏，包括：

- **历史记录**：输入内容的撤销/重做
- **标签工具**：快速插入预设标签
- **提示词优化**：调用 LLM 扩写/优化提示词
- **翻译**：多语言翻译功能
- **图像/视频反推**：从图片生成提示词

## 二、项目结构

```
ComfyUI-Prompt-Assistant/
├── __init__.py                    # ComfyUI V3 扩展入口
├── server.py                      # aiohttp 后端服务
├── config_manager.py              # 配置管理
├── pyproject.toml                 # 项目配置与版本号
│
├── node/                          # ComfyUI V3 节点定义
│   ├── base/                      # 节点基类
│   ├── expand_node.py             # 提示词优化节点
│   ├── translate_node.py          # 翻译节点
│   ├── image_caption_node.py      # 图像反推节点
│   ├── video_caption_node.py      # 视频反推节点
│   └── kontext_preset_node.py     # Kontext 预设节点
│
├── services/                      # 后端服务
│   ├── core.py                    # 核心服务逻辑
│   ├── llm.py / vlm.py            # LLM/VLM 调用封装
│   ├── openai_base.py             # OpenAI API 基类
│   ├── baidu.py                   # 百度翻译服务
│   └── model_list.py              # 模型列表管理
│
├── utils/                         # 后端工具
│   ├── image.py / video.py        # 图像/视频处理
│   └── common.py                  # 通用工具函数
│
├── js/                            # 前端 (JavaScript)
│   ├── index.js                   # 主入口，注册 ComfyUI 扩展
│   ├── modules/
│   │   ├── PromptAssistant.js     # ★ 核心：提示词小助手主类
│   │   ├── AssistantContainer.js  # ★ 按钮容器组件
│   │   ├── imageCaption.js        # 图像反推模块
│   │   ├── history.js             # 历史记录管理
│   │   ├── tag.js                 # 标签工具管理
│   │   ├── settings.js            # 设置面板
│   │   ├── uiComponents.js        # UI 组件工厂
│   │   └── apiConfigManager.js    # API 配置管理器
│   │
│   ├── services/
│   │   ├── NodeMountService.js    # ★ 节点挂载服务 (关键!)
│   │   ├── btnMenu.js             # 按钮右键菜单
│   │   ├── features.js            # 功能开关管理
│   │   ├── api.js                 # API 请求封装
│   │   └── cache.js               # 缓存服务
│   │
│   ├── utils/
│   │   ├── UIToolkit.js           # ★ UI 工具包 (按钮/图标工具)
│   │   ├── resourceManager.js     # ★ 资源管理器 (SVG 图标加载)
│   │   ├── eventManager.js        # 事件管理器
│   │   ├── popupManager.js        # 弹窗管理器
│   │   ├── promptFormatter.js     # 提示词格式化
│   │   └── logger.js              # 日志工具
│   │
│   ├── assets/                    # SVG 图标资源
│   │   ├── icon-main.svg          # 主图标 (星星)
│   │   ├── icon-history.svg       # 历史记录
│   │   ├── icon-undo.svg          # 撤销
│   │   ├── icon-redo.svg          # 重做
│   │   ├── icon-tag.svg           # 标签
│   │   ├── icon-expand.svg        # 扩写
│   │   ├── icon-translate.svg     # 翻译
│   │   ├── icon-caption-zh.svg    # 中文反推
│   │   ├── icon-caption-en.svg    # 英文反推
│   │   └── icon-remove.svg        # 移除
│   │
│   └── css/
│       ├── assistant.css          # ★ 容器和按钮样式
│       ├── common.css             # 通用样式
│       ├── popup.css              # 弹窗样式
│       └── uiComponents.css       # UI 组件样式
│
├── config/                        # 配置文件模板
├── locales/                       # 国际化翻译
└── README*.md                     # 多语言文档
```

## 三、核心架构：按钮图标生成与挂载

### 3.1 整体流程

```
ComfyUI 启动
    ↓
__init__.py 注册扩展 (V3 API)
    ↓
index.js setup() 初始化
    ↓
PromptAssistant.initialize()
    ↓
checkAndSetupNode(node) 扫描节点
    ↓
createAssistant() 创建助手实例
    ↓
createAssistantUI() 创建 UI 容器
    ↓
addFunctionButtons() 添加功能按钮 (含图标)
    ↓
_setupUIPosition() 定位挂载到输入框
```

### 3.2 按钮图标的核心技术链

```
资源加载层        →  UI 工具层        →  容器渲染层        →  挂载定位层
ResourceManager     UIToolkit           AssistantContainer   NodeMountService
   ↓                   ↓                    ↓                    ↓
加载 SVG 图标      addIconToButton()   创建容器、排列按钮    查找输入框容器
缓存 SVG 内容      将 SVG 插入按钮     设置锚点/布局        将容器挂载到 DOM
                  处理 hover/active    拖拽排序             处理滚动条适配
```

---

## 四、关键技术详解：在 CLIP 文本编码器输入框生成按钮图标

### 4.1 第 1 层：SVG 图标资源加载 (ResourceManager)

**文件**：[`js/utils/resourceManager.js`](file:///f:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyUI-Prompt-Assistant/js/utils/resourceManager.js)

通过 `fetch` 异步加载 `js/assets/` 目录下的 SVG 文件，解析为文本后缓存。

```javascript
// 关键代码：加载所有 SVG 图标
static #loadIcons() {
    const iconsToLoad = [
        'icon-main.svg', 'icon-history.svg', 'icon-undo.svg',
        'icon-redo.svg', 'icon-tag.svg', 'icon-expand.svg',
        'icon-translate.svg', 'icon-caption-zh.svg', 'icon-caption-en.svg',
        'icon-remove.svg', 'icon-resize-handle.svg',
    ];

    iconsToLoad.forEach(iconName => {
        fetch(this.getAssetUrl(iconName))
            .then(response => response.text())
            .then(svgContent => {
                this.#iconCache.set(iconName, svgContent); // 缓存 SVG 文本
            });
    });
}

// 获取图标，返回包含 SVG 的 span 元素
static getIcon(iconName) {
    const svgContent = this.#iconCache.get(iconName);
    if (!svgContent) return null;

    const iconContainer = document.createElement('span');
    iconContainer.className = 'svg-icon';
    iconContainer.innerHTML = svgContent;

    // ★ 关键：将所有 fill/stroke 改为 currentColor
    // 使图标颜色跟随父元素的 color CSS 属性
    const svgElement = iconContainer.querySelector('svg');
    if (svgElement) {
        svgElement.style.width = '100%';
        svgElement.style.height = '100%';
        svgElement.style.fill = 'currentColor';
        svgElement.querySelectorAll('*').forEach(el => {
            if (el.hasAttribute('fill') && el.getAttribute('fill') !== 'none') {
                el.setAttribute('fill', 'currentColor');
            }
            if (el.hasAttribute('stroke') && el.getAttribute('stroke') !== 'none') {
                el.setAttribute('stroke', 'currentColor');
            }
        });
    }
    return iconContainer;
}
```

**技术要点**：
- SVG 使用 `currentColor` 实现颜色动态继承，按钮 hover 时自动变色
- 每个 SVG 文件独立存放在 `js/assets/` 目录，便于维护和替换
- 首次初始化时异步加载，不影响 UI 渲染

### 4.2 第 2 层：为按钮添加图标 (UIToolkit.addIconToButton)

**文件**：[`js/utils/UIToolkit.js`](file:///f:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyUI-Prompt-Assistant/js/utils/UIToolkit.js)

```javascript
// 关键代码：为按钮元素添加图标
static addIconToButton(button, icon, alt) {
    if (!icon) return;

    button.innerHTML = ''; // 清空按钮

    // 支持 PrimeIcons (pi-xxx)
    if (icon.startsWith('pi-')) {
        const iconSpan = document.createElement('span');
        iconSpan.className = `pi ${icon}`;
        button.appendChild(iconSpan);
        return;
    }

    // 从 ResourceManager 获取 SVG 图标
    const iconName = icon.endsWith('.svg') ? icon : `${icon}.svg`;
    const cachedImg = ResourceManager.getIcon(iconName);
    if (cachedImg) {
        button.appendChild(cachedImg);
        cachedImg.alt = alt || '';
        cachedImg.draggable = false;
    }
}
```

### 4.3 第 3 层：创建按钮容器 (AssistantContainer)

**文件**：[`js/modules/AssistantContainer.js`](file:///f:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyUI-Prompt-Assistant/js/modules/AssistantContainer.js)

`AssistantContainer` 是一个可折叠、可拖拽排序的按钮工具栏容器，支持多种锚点位置。

```javascript
class AssistantContainer {
    render() {
        this.element = document.createElement('div');
        this.element.className = `assistant-container-common prompt-assistant-container`;

        // 悬停检测区域（不可见，扩大交互热区）
        this.hoverArea = document.createElement('div');
        this.hoverArea.className = 'assistant-hover-area';
        this.element.appendChild(this.hoverArea);

        // 指示器（主图标 - 折叠时显示）
        this.indicator = document.createElement('div');
        this.indicator.className = 'assistant-indicator prompt-assistant-indicator';
        this.element.appendChild(this.indicator);

        // 按钮内容容器
        this.content = document.createElement('div');
        this.content.className = 'assistant-content';
        this.element.appendChild(this.content);

        return this.element;
    }

    // ★ 设置主图标 (通常是 icon-main.svg，一个星星图标)
    setIconContent(svgContent) {
        if (this.indicator) {
            this.indicator.innerHTML = svgContent;
        }
    }

    // 添加按钮
    addButton(buttonElement, id) {
        buttonElement.dataset.id = id;
        const buttonIndex = this.buttons.length;
        buttonElement.style.setProperty('--button-index', buttonIndex);
        this.content.appendChild(buttonElement);
        this.buttons.push({ id, element: buttonElement });
    }

    // 展开/折叠
    expand() { /* ... */ }
    collapse() { /* ... */ }
}
```

**容器定位模式**：支持 11 种锚点位置，通过 CSS 类名控制。

```
ANCHOR_POSITION = {
    TOP_LEFT_H, TOP_LEFT_V,         // 左上角 (水平/垂直)
    TOP_CENTER_H,                    // 中上
    TOP_RIGHT_H, TOP_RIGHT_V,       // 右上角 (水平/垂直)
    RIGHT_CENTER_V,                  // 右中
    BOTTOM_RIGHT_H, BOTTOM_RIGHT_V, // 右下角 (水平/垂直)
    BOTTOM_CENTER_H,                 // 中下
    BOTTOM_LEFT_H, BOTTOM_LEFT_V,   // 左下角 (水平/垂直)
    LEFT_CENTER_V                    // 左中
}
```

### 4.4 第 4 层：创建小助手并添加功能按钮 (PromptAssistant)

**文件**：[`js/modules/PromptAssistant.js`](file:///f:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyUI-Prompt-Assistant/js/modules/PromptAssistant.js)

#### 4.4.1 createAssistantUI() — 创建整体 UI

```javascript
createAssistantUI(widget, inputWidget) {
    // 1. 创建 AssistantContainer 实例
    const container = new AssistantContainer({
        nodeId: nodeId,
        type: 'prompt',
        anchorPosition: locationSetting, // 从设置读取位置
        enableDragSort: true,
    });

    // 2. 渲染容器
    const containerEl = container.render();

    // 3. ★ 设置主图标 (星星图标)
    const mainIcon = ResourceManager.getIcon('icon-main.svg');
    if (mainIcon) {
        container.indicator.innerHTML = '';
        container.indicator.appendChild(mainIcon);
    }

    // 4. 保存引用
    widget.container = container;
    widget.element = containerEl;

    // 5. ★ 添加功能按钮 (含图标)
    this.addFunctionButtons(widget);

    // 6. 定位到输入框
    this._setupUIPosition(widget, inputEl, containerEl, ...);
}
```

#### 4.4.2 addFunctionButtons() — 创建功能按钮

每个按钮的创建流程：
1. 定义按钮配置 (id, title, icon, onClick, visible)
2. `UIToolkit.addIconToButton()` 加载 SVG 图标
3. 通过 `container.addButton()` 添加到工具栏

```javascript
addFunctionButtons(widget) {
    const buttonConfigs = [
        {
            id: 'history',
            title: '历史',
            icon: 'icon-history',        // → 加载 icon-history.svg
            onClick: (e, widget) => { /* 显示历史弹窗 */ },
            visible: FEATURES.history
        },
        {
            id: 'undo',
            title: '撤销',
            icon: 'icon-undo',           // → 加载 icon-undo.svg
            onClick: (e, widget) => { /* 执行撤销 */ },
            visible: FEATURES.history
        },
        {
            id: 'redo',
            title: '重做',
            icon: 'icon-redo',           // → 加载 icon-redo.svg
            onClick: (e, widget) => { /* 执行重做 */ },
            visible: FEATURES.history
        },
        // 分割线
        { id: 'divider1', type: 'divider', visible: FEATURES.history },
        {
            id: 'tag',
            title: '标签工具',
            icon: 'icon-tag',            // → 加载 icon-tag.svg
            onClick: ...,
            visible: FEATURES.tag
        },
        {
            id: 'expand',
            title: '提示词优化',
            icon: 'icon-expand',         // → 加载 icon-expand.svg
            onClick: ...,
            visible: FEATURES.expand,
            contextMenu: async (widget) => { /* 右键菜单：切换规则/服务 */ }
        },
        {
            id: 'translate',
            title: '翻译',
            icon: 'icon-translate',      // → 加载 icon-translate.svg
            onClick: ...,
            visible: FEATURES.translate
        },
    ];

    // 遍历创建按钮
    buttonConfigs.forEach(config => {
        if (!config.visible) return;

        if (config.type === 'divider') {
            // 创建分割线
            const divider = document.createElement('div');
            divider.className = 'prompt-assistant-divider';
            widget.container.addButton(divider, config.id);
            return;
        }

        // 创建按钮元素
        const button = document.createElement('div');
        button.className = 'prompt-assistant-button';
        button.title = config.title;

        // ★ 加载 SVG 图标
        UIToolkit.addIconToButton(button, config.icon, config.title);

        // 绑定点击事件
        button.addEventListener('click', (e) => {
            config.onClick(e, widget);
        });

        // 绑定右键菜单
        if (config.contextMenu) {
            button.addEventListener('contextmenu', async (e) => {
                e.preventDefault();
                await buttonMenu.showMenu(button, await config.contextMenu(widget), { widget, buttonElement: button }, e);
            });
        }

        // 添加到容器
        widget.container.addButton(button, config.id);
        widget.buttons[config.id] = button;
    });
}
```

### 4.5 第 5 层：定位挂载 (NodeMountService)

**文件**：[`js/services/NodeMountService.js`](file:///f:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyUI-Prompt-Assistant/js/services/NodeMountService.js)

支持两种渲染模式：
1. **litegraph.js 模式**：传统 Canvas 渲染 + DOM Widget 覆盖层
2. **Vue node2.0 模式**：纯 Vue 组件渲染 (ComfyUI 新版)

```javascript
// ★ 查找输入框的挂载容器
findMountContainer(node, widget) {
    if (this.isVueNodesMode()) {
        return this._findVueNodeContainer(node, widget);
    } else {
        return this._findDomWidgetContainer(node, widget);
    }
}

// LiteGraph 模式：在 DOM Widget 容器中查找
_findDomWidgetContainer(node, widget) {
    // 通过 widget.name 找到对应的 DOM 容器
    const domWidgetContainer = node.widgets.find(w => w.name === widget.name)?.element?.parentElement;
    if (domWidgetContainer) {
        return {
            container: domWidgetContainer,  // 挂载父容器
            textarea: widget.inputEl,        // 输入框元素
            mode: RENDER_MODE.LITEGRAPH
        };
    }
    return null;
}

// Vue 模式：通过 data-node-id 属性查找
_findVueNodeContainer(node, widget) {
    const nodeContainer = document.querySelector(`[data-node-id="${node.id}"]`);
    // 多种策略匹配 textarea...
    // 策略1: 使用 widget.inputEl
    // 策略2: 通过 widget 索引匹配 DOM textarea
    // 策略3: 通过 placeholder/aria-label 模糊匹配
    // 策略4: 只有一个 textarea 时直接使用
    
    return {
        container: mountContainer,  // 挂载父容器
        textarea: textarea,         // 输入框元素
        nodeContainer: nodeContainer,
        mode: RENDER_MODE.VUE_NODES
    };
}
```

### 4.6 第 6 层：CSS 样式

**文件**：[`js/css/assistant.css`](file:///f:/ComfyUI-aki-v2/ComfyUI/custom_nodes/ComfyUI-Prompt-Assistant/js/css/assistant.css)

```css
/* 容器基础样式 */
.assistant-container-common {
    position: absolute;
    display: flex;
    align-items: center;
    z-index: 9999;
    
    /* 毛玻璃效果 */
    background-color: color-mix(in srgb, var(--node-component-header-surface), transparent 60%);
    border: 1px solid color-mix(in srgb, var(--p-panel-border-color), transparent 60%);
    border-radius: 8px;
    backdrop-filter: blur(4px);
    
    /* 过渡动画 */
    transition: width 0.3s cubic-bezier(0.25, 1, 0.5, 1),
                height 0.3s cubic-bezier(0.25, 1, 0.5, 1),
                opacity 0.3s cubic-bezier(0.25, 1, 0.5, 1);
}

/* 折叠状态 - 只显示主图标，透明背景 */
.assistant-container-common.collapsed {
    width: 28px !important;
    height: 28px !important;
    background-color: transparent !important;
    border-color: transparent !important;
    backdrop-filter: none !important;
    box-shadow: none !important;
    pointer-events: none !important; /* 允许点击穿透 */
}

/* 按钮样式 */
.prompt-assistant-button {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s, transform 0.2s, opacity 0.2s;
}

.prompt-assistant-button:hover {
    background-color: var(--p-primary-color); /* 主题色高亮 */
}

.prompt-assistant-button svg {
    width: 16px;
    height: 16px;
    display: block;
}

/* ★ 关键：SVG 图标颜色继承 */
.prompt-assistant-button .svg-icon svg,
.prompt-assistant-button svg {
    fill: currentColor;
    color: var(--p-text-color); /* 跟随主题文字颜色 */
}

.prompt-assistant-button:hover svg {
    color: #ffffff; /* hover 时变白 */
}
```

### 4.7 完整数据流总结

```
用户打开 ComfyUI
    ↓
__init__.py 加载 → index.js setup()
    ↓
PromptAssistant.initialize()
    ↓
  ├─ ResourceManager.init()    → 异步加载所有 SVG 图标到缓存
  ├─ EventManager.init()       → 初始化事件系统
  └─ 注册 canvas.onSelectionChange 事件
        ↓
用户添加 CLIPTextEncode 节点
    ↓
canvas.onSelectionChange 触发
    ↓
checkAndSetupNode(node)
    ↓
  ├─ node.widgets 中筛选有效输入 (text_positive, text_negative)
  ├─ 检查是否是 CLIP/Note/Subgraph 等有效节点
  └─ 为每个有效输入创建助手实例
        ↓
createAssistant()
    ↓
  ├─ 创建 widget 对象
  ├─ createAssistantUI()
  │   ├─ new AssistantContainer() → render()
  │   ├─ ResourceManager.getIcon('icon-main.svg') → 设置主图标
  │   ├─ addFunctionButtons()
  │   │   └─ 循环每个功能按钮:
  │   │       ├─ 创建 div.prompt-assistant-button
  │   │       ├─ UIToolkit.addIconToButton(button, 'icon-xxx.svg')
  │   │       │   └─ ResourceManager.getIcon() → 从缓存取 SVG → 插入按钮
  │   │       └─ widget.container.addButton(button, id)
  │   └─ _setupUIPosition()
  │       └─ NodeMountService.findMountContainerWithRetry()
  │           ├─ LiteGraph: 找 dom-widget 容器
  │           └─ Vue: 通过 data-node-id 找节点容器
  │               → 将 containerDiv 插入到 textarea 的父容器
  │               → 设置 position: absolute + z-index
  └─ PromptAssistant.instances.set(key, widget)
        ↓
完成！按钮工具栏显示在 CLIPTextEncode 输入框右上角
```

## 五、NodeMountService 挂载服务

### 5.1 渲染模式检测

```javascript
detectRenderMode() {
    // 使用 LiteGraph.vueNodesMode 全局标志
    return LiteGraph.vueNodesMode === true
        ? RENDER_MODE.VUE_NODES
        : RENDER_MODE.LITEGRAPH;
}
```

### 5.2 查找挂载容器 (findMountContainer)

两种模式通用返回结构：
```javascript
{
    container: HTMLElement,   // 挂载到的父容器
    textarea: HTMLElement,    // 输入框元素
    nodeContainer: HTMLElement, // Vue 节点容器 (Vue 模式)
    mode: 'litegraph' | 'vue_nodes',
    widgetName: string,
    isNoteNode: boolean
}
```

**LiteGraph 模式**：直接从 `node.widgets` 中找到对应 widget 的 DOM 父容器。

**Vue 模式**：通过 `[data-node-id="${node.id}"]` 查找 Vue 渲染的 DOM，然后通过 4 种策略匹配对应的 `textarea`：
1. **直接引用匹配**：使用 `widget.inputEl`
2. **索引匹配**：计算 widget 在所有 textarea 类型 widget 中的位置，按索引取 DOM textarea
3. **模糊匹配**：通过 `placeholder`、`aria-label`、`label` 文本匹配
4. **唯一兜底**：只有一个 textarea 时直接使用

## 六、按钮交互功能

### 6.1 右键菜单 (btnMenu.js)

每个功能按钮支持右键菜单，通过 `contextMenu` 配置项定义菜单内容。

**示例-扩写按钮的右键菜单**：
- 切换扩写规则（支持分类分组）
- 切换 LLM 服务/模型
- 打开规则管理界面

### 6.2 弹窗系统 (PopupManager)

点击按钮后，通过 `UIToolkit.handlePopupButtonClick()` 管理弹窗的打开/关闭：
- 点击同一按钮：关闭弹窗
- 点击不同按钮：关闭旧弹窗，打开新弹窗
- 保持按钮激活状态高亮

### 6.3 异步操作 (handleAsyncButtonOperation)

对于扩写/翻译等需要调用 API 的操作：
- 按钮进入 `processing` 状态（旋转动画，不可重复点击）
- 支持取消操作
- 流式输出实时更新输入框内容
- 操作完成后显示状态提示（成功/失败）

## 七、扩展开发指南

### 7.1 添加新按钮

1. 准备 SVG 图标文件 → 放入 `js/assets/`
2. 在 `ResourceManager.#loadIcons()` 注册图标名称
3. 在 `PromptAssistant.addFunctionButtons()` 的 `buttonConfigs` 数组添加配置
4. 在 `features.js` 注册功能开关（可选）
5. 在 CSS 中添加按钮样式（可选）

### 7.2 添加新节点支持

在 `UIToolkit.VALID_INPUT_IDS` 和 `UIToolkit._isVueNodesModeWidget()` 的 `supportedNodeTypes` 列表中添加新节点类型。

### 7.3 自定义锚点位置

在设置面板中通过 `PromptAssistant.Location` 设置项选择位置，或在 `AssistantContainer` 初始化时传入 `anchorPosition` 参数。

---

*本文档基于 Prompt Assistant V1.x 源码分析生成。*
