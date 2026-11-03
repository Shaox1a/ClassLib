# ClassLib

ClassLib 是面向班级内部的私有学习资料库。项目分为 Django 主体和存储层：主体负责账号、权限、页面和元数据；存储层在本地使用 SQLite 与私有目录，在生产环境使用 Supabase Postgres 与私有 Storage bucket。

生产部署：在 Supabase 建立私有 bucket `classlib-private`；在 Vercel 配置 `DATABASE_URL`、`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`DJANGO_SECRET_KEY`、`DJANGO_DEBUG=0`、`DJANGO_ALLOWED_HOSTS` 和 `DJANGO_CSRF_TRUSTED_ORIGINS`。首次部署前对 Supabase Postgres 执行 `python manage.py migrate`。服务密钥只放在 Vercel 服务端环境变量中。

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
- `library/`：文件夹、文件、标签、权限、搜索和私有存储。
- `private_files/`：开发阶段的私有文件存储目录，由 Django 验证身份后提供下载，不会被 Git 跟踪。
