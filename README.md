# Web安全实验作业（作业一 & 作业二）

本仓库实现一个可本地部署的 Web 应用作为实验平台（用户管理 + 会话管理 + 核心业务：图片水印管理），并在同一平台上完成“SQL 注入 + 命令注入”的攻防对比实验与安全测试说明。

## 快速开始（Windows / Linux / macOS）

无需 `mise`（推荐）：

- `python tools/bootstrap.py setup`
- `python tools/bootstrap.py run-http`（HTTP）
- `python tools/bootstrap.py run-https`（HTTPS，自签名证书，浏览器会提示不受信任）

使用 `mise`（可选）：

- `mise trust`
- `mise run setup`
- `mise run run-http`
- `mise run run-https`

默认地址：
- HTTP：`http://127.0.0.1:5000`
- HTTPS：`https://127.0.0.1:5443`

## 文档

- 开发文档：`docs/DEV.md`
- 使用说明：`docs/USAGE.md`
- 接口设计：`docs/API.md`
- 实验报告：`reports/实验作业二-实验报告.md`（包含作业一产品描述）
