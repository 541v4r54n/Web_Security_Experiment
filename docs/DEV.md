# 开发文档（DEV）

## 1. 环境要求

- Windows / Linux / macOS
- Python 3.10+（推荐 3.13）
- 可选：`mise`（用于固定 Python 版本与任务编排）

## 2. 初始化

在仓库根目录执行（二选一）：

方式 A（无需 mise）：

- `python tools/bootstrap.py setup`

方式 B（使用 mise）：

- `mise trust`
- `mise run setup`

初始化会：
- 创建虚拟环境 `.venv` 并安装依赖 `requirements.txt`
- 初始化 sqlite 数据库 `var/app.db`
- 生成自签名证书 `var/certs/localhost.crt|localhost.key`

## 3. 启动

方式 A：

- HTTP：`python tools/bootstrap.py run-http`
- HTTPS：`python tools/bootstrap.py run-https`

方式 B：

- HTTP：`mise run run-http`
- HTTPS：`mise run run-https`

## 4. 目录结构

- `websec_app/`：后端应用（Flask）
- `websec_app/templates/`：页面模板（Bootstrap + 少量 JS）
- `var/`：运行时数据（db、上传文件、证书等，不纳入 git）
- `docs/`：开发/说明/API 文档
- `reports/`：实验报告
- `tools/`：测试/辅助脚本（例如简易 fuzz）

## 5. 常用命令

- 自检：`python tools/bootstrap.py self-check`（或 `mise run self-check`）
- 仅初始化数据库：`.venv/bin/python -m websec_app init-db`（Windows：`.venv\\Scripts\\python -m websec_app init-db`）
- 重新生成证书：`.venv/bin/python -m websec_app gen-cert --force`（Windows：`.venv\\Scripts\\python -m websec_app gen-cert --force`）
