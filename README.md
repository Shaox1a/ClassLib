# ClassLib 1.2

正式站点：[classlib-theta.vercel.app](https://classlib-theta.vercel.app/)。使用班级账户的 ID 或昵称登录。

当前版本为 **1.2.0**，发布说明见 [CHANGELOG.md](CHANGELOG.md)。已移除标签功能，搜索保留名称和学科筛选。

1.2.0 新增：固定 ID + 唯一昵称 + 密码哈希 + 可编辑权限组，支持 ID/昵称登录、个人账户信息、管理员批量操作与权限组管理；文件夹内支持多选后批量移动、删除。窄屏工具栏分组换行，静态资源使用内容版本号防止旧缓存。清单和迁移规则见 [账户与权限组](docs/accounts.md)。

1.1.0 新增：允许任意文件类型且不设应用层大小上限、多文件上传、详细信息列表，以及登录失败时在当前页面保留密码输入。列表包含名称、上传日期、类型、大小和上传者；名称和上传日期支持正倒序，默认最新上传优先，文件夹始终排在文件前面。大图标使用三列等尺寸卡片。大文件采用流式/分块处理，实际容量由存储服务的配额决定。具体交互和验收标准见 [1.1.0 优化方案](docs/1.1.0-plan.md)。

从旧版本升级时，先备份，准备待发布构建，再执行数据库迁移并切换生产流量。1.2.0 账户清单的切换规则见 [账户与权限组](docs/accounts.md)；`scripts/upgrade_release.py` 仅适用于历史标签清理，不用于此次账户升级。本地使用 `python manage.py migrate`。历史迁移文件必须保留。`python scripts/audit_secrets.py` 检查密钥忽略规则和 Git 历史，`python scripts/smoke_production.py` 验证生产功能并自动清理临时测试数据。

ClassLib 是面向班级内部的私有学习资料库。Django 负责账号、权限、页面和元数据。本地使用 SQLite 与私有文件目录，生产使用 Vercel Marketplace 的 Neon PostgreSQL 和七牛 KODO 私有空间。

在 Vercel 生产环境设置 Neon 的 `DATABASE_URL`、七牛的 `KODO_BUCKET`、`KODO_REGION`、`KODO_ACCESS_KEY` 和 `KODO_SECRET_KEY`，以及 Django 的 `DJANGO_SECRET_KEY`、`DJANGO_DEBUG=0`、`DJANGO_ALLOWED_HOSTS`。需要额外信任的来源可通过 `DJANGO_CSRF_TRUSTED_ORIGINS` 配置。ClassLib 使用 PostgreSQL 的 `classlib` schema 和七牛华东浙江（`cn-east-1`）的 `class-lib` 私有空间。

已有站点迁移到 Neon 时，复制整个 `classlib` schema，包括约束、索引、账号密码哈希和序列。文件按数据库记录里的存储键复制，切换流量前逐个比对 SHA-256。后续结构升级使用同一数据库连接执行 `python manage.py migrate`。历史 Supabase 导入工具为 `scripts/deploy_data.py`。

云端上传由 Django 验证用户权限，并为每个文件分片签发临时 PUT 地址。浏览器将文件直传七牛；Django 核对分片和总大小，完成合并后登记文件。空间的跨域规则应允许正式站来源发起 PUT，允许 Content-Type 请求头。下载先验证权限，再返回有效期 60 秒的签名链接。

七牛密钥放在服务端，权限限定到班级的私有空间。

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
