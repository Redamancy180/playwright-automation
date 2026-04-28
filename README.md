# Playwright Automation

基于 Python + Playwright 的浏览器自动化项目模板，适合团队统一维护、复用和持续集成。

## 项目目标

这个仓库用于沉淀通用浏览器自动化能力，而不是只存放一次性脚本。整理成仓库后，团队可以获得这些能力：

- 统一安装和运行方式
- 统一配置管理
- 统一版本管理
- 统一 CI 检查
- 便于后续扩展业务脚本和运维流程

## 目录结构

```text
playwright-automation/
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ scripts/
│  └─ run_demo.py
├─ src/
│  └─ pw_automation/
│     ├─ __init__.py
│     ├─ browser.py
│     ├─ config.py
│     └─ runner.py
├─ tests/
│  └─ test_config.py
├─ .env.example
├─ .gitignore
├─ pyproject.toml
├─ requirements.txt
├─ requirements-dev.txt
└─ README.md
```

## 环境要求

- Windows 10/11
- Python 3.10 及以上
- Google Chrome
- Git

如果后续要在 GitHub Actions 或 Linux 服务器上运行，建议把依赖调试端口的逻辑和标准无头运行逻辑分开维护。

## 首次使用

### 1. 克隆仓库

```bash
git clone https://github.com/Redamancy180/playwright-automation.git
cd playwright-automation
```

### 2. 创建虚拟环境

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. 安装依赖

```bash
pip install -r requirements-dev.txt
```

### 4. 安装 Playwright 浏览器

```bash
python -m playwright install chromium
```

### 5. 配置本地环境变量

```bash
copy .env.example .env
```

然后根据本机实际环境修改 `.env`。

## 配置说明

项目使用 `.env` 管理本地配置，主要参数如下：

- `PW_DEBUG_PORT`
  Chrome 远程调试端口

- `PW_USER_DATA_DIR`
  Chrome 用户数据目录，用于复用登录态或浏览器会话

- `PW_CHROME_PATH`
  本机 Chrome 可执行文件路径

- `PW_DEFAULT_TIMEOUT_MS`
  默认等待超时，单位毫秒

- `PW_KEEP_BROWSER_OPEN_ON_ERROR`
  自动化失败时是否保留浏览器窗口，方便排查

示例：

```env
PW_DEBUG_PORT=9555
PW_USER_DATA_DIR=C:\Temp\PlaywrightSession
PW_CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
PW_DEFAULT_TIMEOUT_MS=600000
PW_KEEP_BROWSER_OPEN_ON_ERROR=true
```

## 运行方式

### 方式 1：直接运行演示脚本

```bash
python scripts/run_demo.py --url https://example.com
```

### 方式 2：使用包入口运行

如果已经按 `pyproject.toml` 安装为本地包，可以使用：

```bash
pw-auto --url https://example.com
```

## 代码结构说明

### `src/pw_automation/browser.py`

浏览器公共能力层，主要负责：

- 启动或复用 Chrome 调试实例
- 激活浏览器窗口
- 连接 Playwright 到现有浏览器
- 页面打开和关闭
- 常见元素交互封装

### `src/pw_automation/config.py`

负责统一读取环境变量，避免把路径、端口、超时等配置硬编码到业务代码里。

### `src/pw_automation/runner.py`

命令行运行入口，适合作为统一调试入口和后续脚本接入点。

## 团队开发建议

### 新增业务自动化时

建议遵守下面的分层方式：

- `src/pw_automation/`
  存放公共浏览器方法和可复用能力

- `scripts/`
  存放临时调试脚本或演示入口

- 具体业务流程
  可以后续单独建模块，例如 `src/pw_automation/oms/`、`src/pw_automation/report/`

不要把所有业务逻辑都直接堆在 `browser.py` 里，否则后面会越来越难维护。

### 提交代码时

建议走标准流程：

```bash
git checkout -b feature/your-topic
git add .
git commit -m "feat: add your feature"
git push -u origin feature/your-topic
```

然后在 GitHub 发起 Pull Request。

## 测试与检查

### 本地检查

```bash
python -m compileall src
pytest
```

### GitHub Actions

仓库已配置基础 CI，在以下场景自动执行：

- push 到 `main`
- pull request 合并到 `main`

CI 当前会执行：

- 安装 Python 3.11
- 安装项目依赖
- 安装 Playwright Chromium
- 编译 `src`
- 运行 `pytest`

## 运维建议

如果后续要长期运行任务，建议增加这些能力：

- 统一日志输出目录
- 失败自动截图
- 页面 HTML 留档
- Trace 文件留档
- 失败通知到企业微信、飞书或邮件
- 定时任务调度

如果是本机可视化自动化场景，建议固定一台运维机运行，不要一开始就强依赖 GitHub Actions。

## 安全约定

- 不要把账号密码写死在代码里
- 不要提交 `.env`
- 不要提交浏览器缓存、日志、截图和临时文件
- 涉及敏感凭证时，优先使用 GitHub Secrets 或系统环境变量

## 常见问题

### 1. `git push` 需要认证

优先使用以下任一方式：

- GitHub 网页授权登录
- Personal Access Token
- SSH Key

### 2. 本机 Chrome 路径不一致

修改 `.env` 中的 `PW_CHROME_PATH` 即可。

### 3. 浏览器会话无法复用

检查：

- 调试端口是否被占用
- `PW_USER_DATA_DIR` 是否可写
- Chrome 是否被安全软件限制

### 4. CI 运行通过，但本机运行失败

通常是因为本机运行依赖已打开的 Chrome 调试实例，而 CI 使用的是标准安装环境。后续如果要增强稳定性，建议补一套独立的无头运行逻辑。

## 后续可扩展项

建议按优先级逐步补充：

1. 日志模块
2. 截图和 trace 输出
3. 更完整的测试用例
4. 业务模块拆分
5. 发布版本 tag
6. GitHub Release 和变更记录
