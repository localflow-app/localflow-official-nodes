# localflow-official-nodes

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

为 [LocalFlow](https://github.com/localflow-app/localflow) 工作流引擎提供的官方集成节点集合。

The official collection of integration nodes for the [LocalFlow](https://github.com/localflow-app/localflow) workflow engine.

---

## 目录

- [已有节点](#已有节点)
- [节点标准格式](#节点标准格式)
  - [目录结构](#目录结构)
  - [node.json 配置文件](#nodejson-配置文件)
  - [node.py 执行脚本](#nodepy-执行脚本)
  - [进度报告](#进度报告)
  - [manifest.json 仓库清单](#manifestjson-仓库清单)
- [添加新节点](#添加新节点)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 已有节点

| 节点类型 | 名称 | 分类 | 说明 |
|----------|------|------|------|
| `demo_node` | Demo 节点 | 示例 | 用于验证节点加载流程的示例节点 |
| `clipboard_send` | 剪贴板发送 | 桌面自动化 | 将文本写入剪贴板并通过快捷键粘贴、发送 |

---

## 节点标准格式

每个节点是一个**独立的子目录**，目录名即 `node_type`（蛇形命名 snake_case）。每个节点目录至少包含两个文件：

### 目录结构

```
<node_type>/
├── node.json       # 节点元数据配置（必需）
└── node.py         # 节点执行脚本（必需，可通过 entry_file 指定其他名称）
```

对于 Playwright 节点，还会有额外的脚本文件：

```
<playwright_node>/
├── node.json       # 节点元数据
├── node.py         # 执行包装器
└── script.py       # Playwright 脚本本体
```

### node.json 配置文件

`node.json` 是节点的核心元数据文件，定义了节点的身份、配置项和依赖：

```json
{
  "node_type": "my_node",
  "name": "我的节点",
  "description": "节点的功能描述",
  "category": "分类名称",
  "version": "1.0.0",
  "entry_file": "node.py",
  "dependencies": [],
  "config_schema": {},
  "metadata": {}
}
```

#### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `node_type` | string | 是 | 节点唯一标识，蛇形命名（snake_case），必须与目录名一致 |
| `name` | string | 是 | 节点显示名称，支持中文 |
| `description` | string | 是 | 节点功能描述 |
| `category` | string | 是 | 节点分类，用于节点浏览器分组（如"数据处理"、"桌面自动化"） |
| `version` | string | 是 | 节点版本号，遵循语义化版本（SemVer） |
| `entry_file` | string | 否 | 入口文件名，默认 `"node.py"` |
| `dependencies` | string[] | 否 | pip 依赖包列表，如 `["pandas", "requests"]` |
| `config_schema` | object | 否 | 配置项定义，用于 UI 自动生成配置表单 |
| `metadata` | object | 否 | 附加元数据（可选，Playwright 节点使用） |

#### config_schema 配置项

`config_schema` 定义了节点在 UI 中的可配置参数，每个参数的格式如下：

```json
{
  "param_key": {
    "type": "string | int | float | bool | enum",
    "label": "参数显示标签",
    "description": "参数说明（可选）",
    "default": "默认值（可选）",
    "options": ["选项1", "选项2"]
  }
}
```

**参数类型说明：**

| 类型 | 说明 | 额外字段 |
|------|------|----------|
| `string` | 字符串输入 | - |
| `int` | 整数输入 | - |
| `float` | 浮点数输入 | - |
| `bool` | 布尔开关 | - |
| `enum` | 枚举选择 | 必须提供 `options` 数组 |

**完整示例：**

```json
{
  "file_path": {
    "type": "string",
    "label": "文件路径",
    "description": "输入文件的完整路径"
  },
  "max_count": {
    "type": "int",
    "label": "最大数量",
    "default": 100
  },
  "threshold": {
    "type": "float",
    "label": "阈值",
    "default": 0.5
  },
  "verbose": {
    "type": "bool",
    "label": "详细输出",
    "default": false
  },
  "encoding": {
    "type": "enum",
    "label": "编码格式",
    "options": ["UTF-8", "GBK", "ASCII"],
    "default": "UTF-8"
  }
}
```

### node.py 执行脚本

`node.py` 是节点的执行逻辑，必须定义一个 `execute` 方法：

```python
def execute(self, input_data: dict) -> dict:
    """
    执行节点逻辑

    Args:
        input_data: 输入数据字典，包含上游节点的输出

    Returns:
        输出数据字典，将传递给下游节点
    """
    # 读取配置参数（来自 config_schema）
    param1 = self.config.get("param1", "默认值")

    # 读取上游输入数据
    input_val = input_data.get("input_key", None)

    # 执行业务逻辑
    result = do_something(param1, input_val)

    # 返回输出（建议包含 input_data 以传递上游数据）
    return {**input_data, "output_key": result}
```

**关键约定：**

1. **方法签名固定**：`execute(self, input_data)` — 不可更改
2. **读取配置**：通过 `self.config.get("key", default)` 获取 `config_schema` 中定义的运行时配置值
3. **读取输入**：通过 `input_data.get("key", default)` 获取上游节点传递的数据
4. **返回值**：必须返回 `dict`，建议使用 `{**input_data, ...}` 格式以传递上游数据给下游
5. **依赖声明**：如果使用了第三方库，必须在 `node.json` 的 `dependencies` 中声明，LocalFlow 会自动安装
6. **进度报告**：对于耗时操作（如循环处理、网络请求），可调用 `report_progress()` 向 UI 报告执行进度

### 进度报告

当节点包含循环、批量网络请求等耗时操作时，可以在 `execute` 方法中调用 `report_progress()` 函数向 UI 实时报告进度，用户将在节点卡片上看到进度条和百分比。

```python
def report_progress(percent: int, message: str = ""):
    """
    报告节点执行进度

    Args:
        percent: 进度百分比 (0-100)
        message: 进度描述信息（可选）
    """
```

**使用示例：**

```python
def execute(self, input_data):
    items = input_data.get("items", [])
    results = []

    for i, item in enumerate(items):
        # 处理每个条目...
        results.append(process(item))

        # 报告进度：百分比 + 描述信息
        report_progress(int((i + 1) / len(items) * 100), f"处理中 {i+1}/{len(items)}")

    return {**input_data, "results": results}
```

**注意事项：**

- `percent` 范围为 0-100，超出范围会自动截断
- `message` 为可选参数，用于在 UI 上显示当前处理步骤的描述
- `report_progress()` 由 LocalFlow 运行时自动注入，无需 import
- 进度报告不会影响节点执行性能，可放心在循环中使用
- 如果节点不调用 `report_progress()`，UI 将显示默认的旋转动画指示器

**实际示例（demo_node）：**

```python
def execute(self, input_data):
    """Demo 节点 - 输出问候语"""
    greeting = self.config.get("greeting", "Hello LocalFlow!")
    return {**input_data, "demo_output": greeting}
```

**实际示例（clipboard_send）：**

```python
def execute(self, input_data):
    """剪贴板发送节点"""
    import pyperclip
    import pyautogui

    text_var = self.config.get("text_var", "rendered_text")
    text = input_data.get(text_var, "")
    pyperclip.copy(str(text))

    paste_hotkey = self.config.get("paste_hotkey", "ctrl+v")
    send_hotkey = self.config.get("send_hotkey", "enter")

    pyautogui.hotkey(*paste_hotkey.split("+"))
    pyautogui.press(send_hotkey.replace("enter", "return"))

    return {**input_data, self.config.get("output_var", "send_result"): True}
```

### manifest.json 仓库清单

仓库根目录的 `manifest.json` 记录了所有可用节点的清单：

```json
{
  "repo_name": "localflow-official-nodes",
  "repo_url": "https://github.com/localflow-app/localflow-official-nodes",
  "snapshot_version": "1.0.0",
  "snapshot_commit": "",
  "nodes": [
    "demo_node",
    "clipboard_send"
  ]
}
```

| 字段 | 说明 |
|------|------|
| `repo_name` | 仓库名称 |
| `repo_url` | 仓库 URL |
| `snapshot_version` | 快照版本号 |
| `snapshot_commit` | 快照对应的 Git commit SHA |
| `nodes` | 所有节点类型的列表（与各节点目录名一致） |

> **重要**：添加新节点后，务必更新 `manifest.json` 的 `nodes` 数组，将新节点的 `node_type` 加入其中，否则 LocalFlow 无法发现该节点。

---

## 添加新节点

以创建一个 `csv_reader` 节点为例：

### 1. 创建节点目录

```bash
mkdir csv_reader
```

### 2. 编写 node.json

```json
{
  "node_type": "csv_reader",
  "name": "CSV 读取器",
  "description": "读取 CSV 文件并返回行数和列数",
  "category": "数据处理",
  "version": "1.0.0",
  "entry_file": "node.py",
  "dependencies": [],
  "config_schema": {
    "file_path": {
      "type": "string",
      "label": "CSV 文件路径",
      "description": "输入 CSV 文件的完整路径"
    },
    "encoding": {
      "type": "enum",
      "label": "编码格式",
      "options": ["UTF-8", "GBK", "Latin-1"],
      "default": "UTF-8"
    }
  }
}
```

### 3. 编写 node.py

```python
import csv
import os

def execute(self, input_data):
    file_path = self.config.get("file_path", "")
    encoding = self.config.get("encoding", "UTF-8")

    if not file_path:
        return {**input_data, "success": False, "error": "未提供文件路径"}
    if not os.path.exists(file_path):
        return {**input_data, "success": False, "error": f"文件不存在: {file_path}"}

    try:
        with open(file_path, "r", encoding=encoding) as f:
            reader = csv.reader(f)
            rows = list(reader)
        report_progress(100, f"读取完成，共 {len(rows)} 行")
        return {
            **input_data,
            "success": True,
            "row_count": len(rows),
            "column_count": len(rows[0]) if rows else 0,
        }
    except Exception as e:
        return {**input_data, "success": False, "error": str(e)}
```

### 4. 更新 manifest.json

在 `manifest.json` 的 `nodes` 数组中添加 `"csv_reader"`：

```json
{
  "nodes": [
    "demo_node",
    "clipboard_send",
    "csv_reader"
  ]
}
```

### 5. 本地测试

在 LocalFlow 中，将节点目录复制到 `user_data/official_nodes/` 下，重启应用即可在节点浏览器中看到新节点。

---

## 贡献指南

我们欢迎社区贡献新的节点或改进现有节点！

### 贡献方式

- **新增节点** — 按照上述标准格式添加新节点
- **改进节点** — 优化现有节点的功能或性能
- **修复 Bug** — 修复节点执行中的问题
- **完善文档** — 改进节点描述或补充使用说明

### 贡献流程

1. **Fork 本仓库** — 点击右上角 Fork 按钮
2. **克隆到本地**
   ```bash
   git clone https://github.com/<your-username>/localflow-official-nodes.git
   cd localflow-official-nodes
   ```
3. **创建特性分支**
   ```bash
   git checkout -b feature/your-new-node
   ```
4. **添加或修改节点** — 遵循[节点标准格式](#节点标准格式)
5. **更新 manifest.json** — 将新节点加入 `nodes` 数组
6. **本地测试** — 将节点放入 LocalFlow 的 `user_data/official_nodes/` 目录验证功能
7. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add your-new-node node"
   ```
8. **推送到 Fork**
   ```bash
   git push origin feature/your-new-node
   ```
9. **创建 Pull Request** — 在 GitHub 上向 `main` 分支提交 PR

### 提交规范

请遵循 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat` | 新增节点或功能 | `feat: add csv_reader node` |
| `fix` | 修复 Bug | `fix: fix encoding issue in csv_reader` |
| `docs` | 文档变更 | `docs: update node description` |
| `refactor` | 重构 | `refactor: simplify clipboard_send logic` |
| `chore` | 杂项 | `chore: update manifest.json` |

### PR 检查清单

提交 Pull Request 前，请确认：

- [ ] `node.json` 字段完整且格式正确
- [ ] `node.py` 包含有效的 `execute(self, input_data)` 方法
- [ ] 耗时操作（循环、批量请求等）中调用了 `report_progress()` 报告进度
- [ ] `dependencies` 中声明了所有使用的第三方库
- [ ] `manifest.json` 已更新，包含新节点
- [ ] 节点在 LocalFlow 中本地测试通过
- [ ] `node_type` 与目录名一致，使用蛇形命名
- [ ] 没有硬编码的密钥或敏感信息

---

## 许可证

本项目采用 [Apache License 2.0](LICENSE) 开源许可证。
