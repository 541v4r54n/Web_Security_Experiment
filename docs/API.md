# 接口设计（API）

说明：本项目以页面为主，同时提供少量 JSON 接口便于抓包与测试。

## 1. 页面路由

- `GET /`：主页
- `GET /register` / `POST /register`：注册
- `GET /login` / `POST /login`：登录
- `POST /logout`：登出
- `GET /profile` / `POST /profile`：个人信息维护
- `POST /account/delete`：账号删除
- `GET /users`：用户管理（Admin）
- `POST /users/<id>/delete`：删除用户（Admin）
- `GET /audit`：查看个人操作记录
- `GET /images` / `POST /images/upload`：图片列表 / 上传并生成水印
- `GET /images/<id>`：图片详情
- `GET /images/<id>/download`：下载水印图
- `GET /labs`：实验入口
- `GET /labs/sql-injection`：SQL 注入实验页
- `POST /labs/sql-injection/insecure`：漏洞版检索
- `POST /labs/sql-injection/secure`：防御版检索
- `GET /labs/command-injection`：命令注入实验页
- `POST /labs/command-injection/insecure`：漏洞版 ping
- `POST /labs/command-injection/secure`：防御版 ping

## 2. JSON 接口

- `GET /api/health`：健康检查
  - 输出：`{ "ok": true, "time": "...", "user": { "id": 1, "username": "..." } | null }`
- `GET /api/audit`：当前用户操作日志（最近 50 条）
- `GET /api/images`：当前用户图片列表

## 3. 通用参数与返回

- 表单提交均包含 CSRF 字段：`csrf_token`
- 成功：页面跳转或返回 JSON
- 失败：HTTP 400/401/403/500 + 错误提示
