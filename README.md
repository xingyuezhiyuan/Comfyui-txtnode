# ComfyUI String Save Node

这个ComfyUI插件提供了一个节点，可以将字符串保存为本地txt文件。

## 节点功能

- **Save String to Text File** - 将输入的字符串保存到指定的本地文件

## 节点参数

| 参数 | 类型 | 说明 |
|------|------|------|
| text | STRING | 要保存的字符串内容（强制输入） |
| file_path | STRING | 保存文件的路径（支持相对路径或绝对路径） |
| encoding | STRING | 文件编码格式（utf-8/gbk/utf-16/ascii） |
| append_mode | BOOLEAN | 是否追加模式（True为追加，False为覆盖） |

## 输出

- **file_path** - 实际保存文件的完整路径

## 安装

1. 将整个文件夹复制到 ComfyUI 的 `custom_nodes` 目录下
2. 重启 ComfyUI
3. 在节点菜单的 `Utils` 分类中找到节点

## 使用示例

1. 在工作流中添加 `Save String to Text File` 节点
2. 连接字符串输入源到 `text` 端口
3. 设置保存路径，例如 `output/result.txt`
4. 选择合适的编码格式
5. 根据需要选择是否追加模式
6. 运行工作流

## 文件结构

```
Comfyui-xingyue/
├── __init__.py          # 插件入口文件
├── nodes.py             # 节点实现
└── README.md            # 说明文档
```
