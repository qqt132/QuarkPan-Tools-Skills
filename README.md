# 夸克网盘分享链接转存 Skill

## 简介

这是一个用于夸克网盘分享链接转存的 Agent Skill。用户可以发送夸克分享链接，Skill 能够：

1. 🔍 **提取文件列表** - 从分享链接中获取所有文件信息
2. ✅ **智能文件选择** - 支持多种选择方式（序号、范围、通配符、类型）
3. 📤 **转存功能** - 将选中的文件保存到指定目录
4. 📋 **树形显示** - 以树形结构展示文件夹层级

## 技术特点

- **基于 QuarkPanTool** - 参考开源项目的核心代码
- **API 封装** - 封装夸克网盘全部 API
- **交互式 CLI** - 支持命令行交互操作
- **JSON 输出** - 支持程序化调用和结果解析
- **递归遍历** - 支持递归获取子文件夹内容
- **智能选择** - 支持多种文件选择方式

## 安装步骤

### 1. 安装 Python 依赖

```bash
cd ~/.openclaw/workspace/skills/quark-save
pip3 install -r requirements.txt
```

或

```bash
pip install requests
```

### 2. 配置 Cookie（首次使用）

```bash
# 方法 1：手动登录（推荐）
python main.py login

# 方法 2：从浏览器复制 Cookie
# 1. 打开 https://pan.quark.cn 并登录
# 2. 按 F12 打开开发者工具
# 3. 找到请求的 Cookie，复制粘贴

# 方法 3：使用 set_cookie.py（非交互式）
python set_cookie.py "你的 Cookie 字符串"
```

Cookie 会自动保存到：`~/.config/quark/cookies.txt`

## 使用方法

### 命令行用法

```bash
# 查看分享文件列表（递归显示所有文件）
python3 main.py list <share_url> [--password <pwd>] [--depth <n>] [--json]

# 转存文件
python3 main.py save <share_url> <fid_list> <to_dir> [--password <pwd>] [--json]

# 查看我的目录
python3 main.py dirs [--json] [--json-only]

# 创建新目录
python3 main.py create_dir <dir_name> [--parent_fid <fid>] [--json]

# 登录
python main.py login
```

### 输出格式参数

所有命令支持以下参数控制输出格式：

| 参数 | 说明 | 示例 |
|------|------|------|
| （默认） | 只显示人类可读格式（树形结构） | `python3 main.py dirs` |
| `--json` | 显示树形结构 + JSON | `python3 main.py dirs --json` |
| `--json-only` | 只显示 JSON（不显示树形） | `python3 main.py dirs --json-only` |

**设计说明**：
- **默认行为**：只显示人类可读的树形结构，适合直接在终端查看
- **`--json`**：同时显示树形和 JSON，方便调试和程序调用
- **`--json-only`**：只输出 JSON，适合脚本自动化处理

### 使用交互式保存助手

```bash
# 交互式选择文件并转存
python save_helper.py <share_url> [--password <pwd>]

# 自动模式（选择所有文件，保存到根目录）
python save_helper.py <share_url> --auto
```

### 示例

```bash
# 1. 查看分享文件列表
python3 main.py list https://pan.quark.cn/s/xxxxx

# 2. 使用提取码查看
python3 main.py list https://pan.quark.cn/s/xxxxx --password 1234

# 3. 只显示第一层
python3 main.py list https://pan.quark.cn/s/xxxxx --depth 1

# 4. 查看文件列表后，选择文件 ID 转存
python3 main.py save https://pan.quark.cn/s/xxxxx "1,2,3" "/我的视频"

# 5. 查看我的目录结构
python3 main.py dirs

# 6. 创建新目录
python3 main.py create_dir "我的电影" --parent_fid 0

# 7. 使用交互式保存助手
python3 save_helper.py https://pan.quark.cn/s/xxxxx
```

### 文件选择方式

支持多种选择方式：

| 方式 | 示例 | 说明 |
|------|------|------|
| 全部 | `all` | 选择所有文件 |
| 序号 | `1,2,3` | 选择序号 1, 2, 3 的文件 |
| 范围 | `1-10` | 选择序号 1 到 10 的文件 |
| 通配符 | `*.mkv` | 选择所有 mkv 文件 |
| 类型 | `video` | 选择所有视频文件 |
| 扩展名 | `mkv,pdf,zip` | 选择指定扩展名的文件 |

### 环境变量

```bash
# 自定义 Cookie 文件路径
export QUARK_COOKIES_PATH=~/.config/quark/cookies.txt
```

## API 接口说明

### QuarkClient 类

#### 核心方法

| 方法 | 功能 | 返回值 |
|------|------|--------|
| `login()` | 验证 Cookie | `bool` |
| `parse_share_url(url)` | 解析分享链接 | `dict: {pwd_id, password}` |
| `get_stoken(pwd_id, password='')` | 获取访问令牌 | `str` |
| `get_file_list(pwd_id, stoken, pdir_fid='0')` | 获取文件列表 | `List[Dict]` |
| `get_all_files_recursive(...)` | 递归获取所有文件 | `List[Dict]` |
| `get_folder_tree(...)` | 获取文件夹树结构 | `Dict` |
| `save_files(...)` | 转存文件 | `str: task_id` |
| `check_task_status(task_id)` | 查询任务状态 | `Dict` |
| `wait_task_complete(...)` | 等待任务完成 | `bool` |
| `get_user_dirs()` | 获取目录列表 | `List[Dict]` |
| `get_dir_by_path(path)` | 根据路径获取目录ID | `str` |
| `create_dir(...)` | 创建目录 | `str: dir_id` |

#### 数据结构

**文件信息 (Dict)**:
```python
{
    'fid': '文件ID',
    'name': '文件名',
    'size': 文件大小(字节),
    'type': 'file/folder',
    'is_file': True/False,
    'pdir_fid': '父目录ID',
    'obj_category': '文件分类'
}
```

**目录信息 (Dict)**:
```python
{
    'fid': '目录ID',
    'name': '目录名',
    'path': '/完整/路径',
    'pdir_fid': '父目录ID'
}
```

**任务状态 (Dict)**:
```python
{
    'status': 'pending/processing/completed/failed/cancelled',
    'progress': 0-100,
    'message': '状态消息'
}
```

## 输出示例

### list 命令输出

```bash
$ python3 main.py list https://pan.quark.cn/s/xxxxx

================================================================================
序号    名称                                   大小         类型        
================================================================================
[1]   movie                                 1.25 GB     📄 文件
[2]   tv_series                             5.00 GB     📄 文件
[3]   music                                 -           📁 文件夹
[4]   documents                             2.50 GB     📄 文件
================================================================================
共 4 个项目

{
    "action": "list",
    "status": "success",
    "files": [...],
    "count": 4,
    "index_map": ["1", "2", "3", "4"]
}
```

### 交互式文件选择

```
📝 请选择要转存的文件

支持的选择方式：
  all              - 选择所有文件
  1,2,3            - 选择序号 1, 2, 3 的文件
  1-10             - 选择序号 1 到 10 的文件
  *.mkv            - 选择所有 mkv 文件
  video            - 选择所有视频文件
  zip              - 选择所有压缩包
  mkv,pdf,mp4      - 选择指定扩展名的文件

请输入选择: all

✅ 选中 15 个文件：
  1. 📄 movie001.mkv (3.88 GB)
  2. 📄 movie002.mkv (3.62 GB)
  3. 📄 movie003.mkv (3.41 GB)
  ...
```

### save_helper.py 交互式使用

```
📁 文件树：
------------------------------------------------
  [1] 📄 movie001.mkv (3.88 GB)
  [2] 📄 movie002.mkv (3.62 GB)
  [3] 📄 movie003.mkv (3.41 GB)
  [4] 📁 subfolder/
------------------------------------------------
共 4 个项目

📝 请选择要转存的文件: 1-3

✅ 选中 3 个文件：
  1. 📄 movie001.mkv (3.88 GB)
  2. 📄 movie002.mkv (3.62 GB)
  3. 📄 movie003.mkv (3.41 GB)

确认选择吗？(y/n): y

📂 选择目标目录:
  /              - 根目录
  /路径/目录     - 指定目录
  new:目录名     - 创建新目录
  home           - 使用根目录 (/)

请输入目标路径: /我的视频

📤 开始转存
================================================
文件数: 3
目标目录: /我的视频 (ID: 12345)

✅ 转存任务已创建: task_xxx

⏳ 转存进度: 50% - 正在处理...
⏳ 转存进度: 100% - 正在保存...
✅ 转存完成！
```

## 错误处理

| 错误类型 | 说明 | 解决方法 |
|---------|------|---------|
| Cookie 失效 | Cookie 过期或无效 | 运行 `python main.py login` |
| 提取码错误 | 分享链接需要提取码但未提供 | 使用 `--password` 参数 |
| 目录不存在 | 目标目录不存在 | 使用 `python main.py dirs` 查看 |
| 容量不足 | 网盘空间不足 | 清理网盘空间 |
| 网络错误 | 网络连接问题 | 检查网络连接 |

## 与 OpenClaw 集成

作为 Skill 被 Worker 引用时，会自动：

1. 从 `~/.config/quark/cookies.txt` 读取 Cookie
2. 根据参数执行相应操作
3. 返回 JSON 格式结果

### Worker 调用示例

```bash
# 列出文件
python main.py list https://pan.quark.cn/s/xxxxx

# 转存文件（fid_list 为文件序号列表，to_dir 为目录路径）
python main.py save https://pan.quark.cn/s/xxxxx "1,2,3" "/我的视频"
```

### save_helper.py 作为独立脚本

```bash
# 交互式保存（适合客服模式）
python save_helper.py https://pan.quark.cn/s/xxxxx
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `quark_client.py` | 夸克网盘客户端，封装所有 API 调用 |
| `main.py` | 主入口脚本，提供 CLI 接口 |
| `save_helper.py` | 交互式保存助手 |
| `set_cookie.py` | Cookie 设置工具 |
| `test_api.py` | API 测试工具 |
| `requirements.txt` | Python 依赖 |
| `README.md` | 本文件 |

## 注意事项

1. **首次使用必须登录** - 需要配置 Cookie 才能使用
2. **Cookie 有效期** - 建议每 30 天更新一次
3. **提取码处理** - 有提取码的链接必须提供密码
4. **大文件转存** - 大文件可能需要等待较长时间
5. **递归深度** - 默认无限深度，可使用 `--depth` 限制

## 故障排查

### 问题：Cookie 验证失败

```bash
# 重新登录
python main.py login
```

### 问题：无法获取文件列表

```bash
# 检查分享链接格式
# 正确格式: https://pan.quark.cn/s/xxxxx
# 带密码: https://pan.quark.cn/s/xxxxx?pwd=1234

# 使用 --password 参数
python main.py list <url> --password 1234
```

### 问题：转存失败

```bash
# 检查目标目录是否存在
python main.py dirs

# 创建目录
python main.py create_dir "新目录"
```

### 问题：文件选择不工作

```bash
# 检查文件序号
python main.py list <url>

# 使用正确的序号格式
python main.py list <url> --depth 1  # 只看第一层
```

## 更新日志

### v2.0.0
- ✅ 添加递归获取文件夹内容功能
- ✅ 添加 `get_folder_tree()` 方法
- ✅ 增强 `list` 命令，支持 `--depth` 参数
- ✅ 优化输出格式，显示树形结构
- ✅ 增强文件选择功能（支持范围、通配符、类型）
- ✅ 创建交互式保存助手 `save_helper.py`
- ✅ 更新 `set_cookie.py` 使用正确的 API 端点
- ✅ 优化错误处理和用户体验

### v1.0.0
- ✅ 实现基本转存功能
- ✅ 支持文件列表显示
- ✅ 支持目录管理
- ✅ 支持任务状态查询

## 致谢

- **QuarkPanTool** - 开源项目，提供技术参考
- **OpenClaw** - 提供 Agent Skill 框架

## 许可证

MIT License
