# 夸克网盘分享链接转存 Skill

## 📋 技能描述

这是一个用于 **夸克网盘分享链接转存** 的 Agent Skill。当用户发送夸克分享链接后，能够：

1. 🔍 **提取分享链接中的文件列表** - 显示所有可访问的文件和文件夹
2. ✅ **让用户选择要转存的文件** - 支持选择多个文件或整个文件夹
3. 📤 **将选中的文件转存到用户指定的夸克网盘目录** - 支持指定目标路径

## 🛠 技术架构

### 核心组件

| 文件 | 说明 |
|------|------|
| `quark_client.py` | 夸克网盘客户端，封装所有 API 调用 |
| `main.py` | 主入口脚本，提供 CLI 接口 |
| `set_cookie.py` | Cookie 设置工具 |
| `list_files.py` | 递归显示文件列表 |
| `test_save.py` | 转存功能测试脚本 |
| `requirements.txt` | Python 依赖 |
| `README.md` | 详细使用说明 |

### 技术栈

- **语言**: Python 3.7+
- **网络请求**: `requests` 库
- **认证管理**: Cookie 持久化（JSON 格式）
- **数据格式**: JSON

## 📦 安装步骤

### 1. 安装依赖

```bash
cd ~/.openclaw/workspace/skills/quark-save
pip3 install -r requirements.txt
```

或

```bash
pip install requests
```

### 2. 首次登录配置 Cookie

```bash
# 方法 1：运行登录命令（会提示从浏览器复制 Cookie）
python3 main.py login

# 方法 2：使用 set_cookie.py（非交互式）
python3 set_cookie.py "你的 Cookie 字符串"
```

Cookie 会自动保存到：`~/.config/quark/cookies.txt`

## 💡 使用方法

### 命令行用法

```bash
# 查看分享文件列表
python main.py list <share_url> [--password <密码>] [--depth <深度>] [--json]

# 转存文件
python main.py save <share_url> <文件 ID 列表> <目标目录路径> [--password <密码>] [--json]

# 查看我的目录结构
python main.py dirs [--json] [--json-only]

# 创建新目录
python main.py create_dir <目录名称> [--parent_fid <父目录 ID>] [--json]

# 登录（重新配置 Cookie）
python main.py login
```

### 输出格式控制

所有命令支持以下参数控制输出格式：

| 参数 | 说明 | 示例 |
|------|------|------|
| （默认） | 只显示人类可读格式（树形结构） | `python3 main.py dirs` |
| `--json` | 显示树形结构 + JSON | `python3 main.py dirs --json` |
| `--json-only` | 只显示 JSON | `python3 main.py dirs --json-only` |

**设计说明**：
- **默认行为**：只显示人类可读的树形结构，适合直接在终端查看
- **`--json`**：同时显示树形和 JSON，方便调试和程序调用
- **`--json-only`**：只输出 JSON，适合脚本自动化处理

### 示例场景

```bash
# 1️⃣ 用户发送分享链接
https://pan.quark.cn/s/abcd1234

# 2️⃣ 列出文件（递归显示所有层级）
python3 main.py list https://pan.quark.cn/s/abcd1234

# 输出示例：
# 📂 文件列表:
# ================================================================================
# └─ 📁 电视剧/
#    ├─ 📄 S01E01.mp4 (1.25 GB) [1]
#    ├─ 📄 S01E02.mp4 (1.18 GB) [2]
#    └─ 📄 S01E03.mp4 (1.32 GB) [3]
# ================================================================================

# 3️⃣ 用户选择文件 1,2 转存到 "/我的视频/电视剧"
python3 main.py save https://pan.quark.cn/s/abcd1234 "1,2" "/我的视频/电视剧"

# 4️⃣ 查看转存进度和结果
# 🚀 开始转存 2 个文件...
# ✅ 转存任务已创建：xxxxx
# ⏳ 等待任务完成...
# ✅ 转存完成！
```

### 带提取码的链接

```bash
# 有提取码的链接
python3 main.py list https://pan.quark.cn/s/abcd1234?pwd=1234

# 或使用 --password 参数
python3 main.py list https://pan.quark.cn/s/abcd1234 --password 1234
```

### 递归深度控制

```bash
# 只显示第一层
python3 main.py list https://pan.quark.cn/s/abcd1234 --depth 1

# 显示前 3 层
python3 main.py list https://pan.quark.cn/s/abcd1234 --depth 3

# 显示所有层级（默认）
python3 main.py list https://pan.quark.cn/s/abcd1234
```

### 文件选择方式

`save` 命令支持多种文件选择方式：

| 方式 | 示例 | 说明 |
|------|------|------|
| 序号 | `1,2,3` | 选择序号 1, 2, 3 的文件 |
| 范围 | `1-10` | 选择序号 1 到 10 的文件 |
| 全部 | `all` | 选择所有文件 |
| 类型 | `video` | 选择所有视频文件 |
| 扩展名 | `*.mkv` | 选择所有 mkv 文件 |

```bash
# 示例：选择前 5 个文件
python3 main.py save https://pan.quark.cn/s/abcd1234 "1-5" "/我的视频"

# 示例：选择所有视频文件
python3 main.py save https://pan.quark.cn/s/abcd1234 "video" "/我的视频"

# 示例：选择所有 mkv 文件
python3 main.py save https://pan.quark.cn/s/abcd1234 "*.mkv" "/我的视频"
```

## 🔑 API 接口

### 核心 API 端点

| 功能 | 方法 | 端点 |
|------|------|------|
| 获取访问令牌 | POST | `/1/clouddrive/share/sharepage/token` |
| 获取分享详情 | GET | `/1/clouddrive/share/sharepage/detail` |
| 转存文件 | POST | `/1/clouddrive/share/sharepage/save` |
| 查询任务状态 | GET | `/1/clouddrive/task` |
| 获取目录列表 | GET | `/1/clouddrive/file/sort` |
| 创建目录 | POST | `/1/clouddrive/file` |

**基础域名**: `https://drive-pc.quark.cn`

### 认证方式

所有 API 请求需要携带 Cookie，关键 Cookie 字段：
- `__puus` - 用户会话
- `__pus` - 用户标识
- `__kp` - 密钥
- `ctoken` - CSRF token

Cookie 以 JSON 格式保存到 `~/.config/quark/cookies.txt`

## ⚠️ 注意事项

1. **Cookie 有效期**：Cookie 会过期，如果提示"Cookie 失效"，请重新登录
2. **网盘容量**：转存前确保网盘有足够空间
3. **分享链接有效期**：部分分享链接有过期时间
4. **文件大小限制**：单个文件最大支持转存 100GB
5. **并发限制**：避免同时发起大量请求

## 🐛 常见问题

### Q: 提示"Cookie 失效"怎么办？
A: 重新运行 `python3 main.py login` 或 `python3 set_cookie.py "新的 Cookie"`

### Q: 转存失败怎么办？
A: 检查：
1. Cookie 是否有效
2. 网盘容量是否足够
3. 分享链接是否过期
4. 目标目录是否存在

### Q: 如何查看目标目录 ID？
A: 运行 `python3 main.py dirs` 查看所有目录及其 ID

### Q: 如何只查看第一层文件？
A: 使用 `--depth 1` 参数：`python3 main.py list <url> --depth 1`

### Q: JSON 输出太多怎么办？
A: 默认只显示树形结构，不会输出 JSON。只有添加 `--json` 参数才会显示 JSON。

## 📝 更新日志

### 2026-02-27
- ✅ 添加 `--json` 和 `--json-only` 参数控制输出格式
- ✅ 修复所有 API 调用（GET 使用 params，POST 使用 json + params）
- ✅ 支持递归深度控制（`--depth` 参数）
- ✅ 支持多种文件选择方式（序号、范围、通配符、类型）
- ✅ 优化目录列表显示（树形结构）

## 🔗 参考项目

- [QuarkPanTool](https://github.com/ihmily/QuarkPanTool) - 夸克网盘工具

---

**Skill 位置**: `~/.openclaw/workspace/skills/quark-save/`

**作者**: OpenClaw Agent Skill

**版本**: 1.0
