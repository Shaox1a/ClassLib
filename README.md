# ClassLib 1.0

正式站点：[classlib-theta.vercel.app](https://classlib-theta.vercel.app/)。使用原有 ClassLib 班级账号登录。

当前正式版为 **1.0.0**，发布说明见 [CHANGELOG.md](CHANGELOG.md)。1.0 已移除标签功能，搜索保留名称和学科筛选。

从旧版本升级时，先备份并部署新代码，再执行数据库迁移。生产备份与升级可分别运行 `python scripts/upgrade_release.py backup` 和 `python scripts/upgrade_release.py migrate`；本地使用 `python manage.py migrate`。历史迁移文件必须保留。`python scripts/audit_secrets.py` 检查密钥忽略规则和 Git 历史，`python scripts/smoke_production.py` 验证生产功能并自动清理临时测试数据。

ClassLib 是面向班级内部的私有学习资料库。项目分为 Django 主体和存储层：主体负责账号、权限、页面和元数据；存储层在本地使用 SQLite 与私有目录，在生产环境使用 Supabase Postgres 与私有 Storage bucket。

生产部署：在 Supabase 建立私有 bucket `classlib-private`；在 Vercel 配置 `DATABASE_URL`、`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`DJANGO_SECRET_KEY`、`DJANGO_DEBUG=0`、`DJANGO_ALLOWED_HOSTS` 和必要时的 `DJANGO_CSRF_TRUSTED_ORIGINS`。服务密钥只放在服务端环境变量中。

首次迁移现有本地资料时，在本地 `.env` 填好连接信息，依次执行 `python scripts/deploy_data.py verify`、`export`、`migrate`、`files`、`audit`。`migrate` 会建立不向 Data API 开放的 `classlib` schema，导入账号和资料元数据并开启 RLS；`files` 上传原有文件并校验 SHA-256。目标已有业务数据时会拒绝再次导入。导出文件存于被 Git 和 Vercel 排除的 `deploy-private/`。后续普通结构迁移使用同一数据库连接执行 `python manage.py migrate`，新表同样应启用 RLS。

云端上传使用临时签名 URL，由浏览器直接传至 Supabase 的 `pending/` 路径；Django 复核实际大小和文件内容后，复制到最终对象并登记元数据。bucket 的 `file_size_limit` 应设为 `52428800`（50 MiB）。下载经 Django 鉴权后跳转至有效期 60 秒的私有签名链接，避免文件流量受到 Vercel 请求体限制。上传中断后遗留的 `pending/` 对象不会出现在资料列表，可在签名失效后清理（至少等待两小时）。

`SUPABASE_SERVICE_ROLE_KEY` 同时兼容新版 `sb_secret_` Secret key 与旧版 service_role JWT。Vercel 环境缺少必要配置时会停止启动，避免意外使用开发数据库或默认密钥。

暂不使用 Docker 时，请按 [START.md](START.md) 启动网站。

## Docker 开发环境

Docker Desktop 可用后执行：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

首次启动会自动迁移数据库。首次使用时再运行：

```powershell
docker compose exec web python manage.py createsuperuser
```

网站位于 <http://127.0.0.1:8000/>；停止服务使用 `docker compose down`。

## 项目说明

- [PROJECT.md](PROJECT.md)：需求与开发路线。
- [START.md](START.md)：本地启动步骤。
- `accounts/`：用户、角色和账号管理。
- `library/`：文件夹、文件、权限、搜索和私有存储。
- `private_files/`：开发阶段的私有文件存储目录，由 Django 验证身份后提供下载，不会被 Git 跟踪。
