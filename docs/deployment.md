# 从候选构建发布 ClassLib

## 分支和配置

`main` 是生产来源分支。每项变更从最新 `main` 创建短期主题分支，例如 `feat/bulk-download` 或 `fix/search-order`，提交 PR，检查通过后合并。主题分支在 GitHub Actions 上验证，只有 `main` 自动触发 Vercel 部署。预发布和正式站点使用同一个提交和构建，均使用 Vercel **Production** 变量。

在 Vercel 项目 **classlib → Settings → Environments → Production → Branch Tracking** 确认生产分支为 `main`，关闭 **Auto-assign Custom Production Domains**，并启用系统环境变量以提供 `VERCEL_URL`。逐项在 Vercel 配置 [.env.example](../.env.example) 中的生产变量。使用正式域名作为 `DJANGO_ALLOWED_HOSTS`，候选部署的精确主机名由应用从 `VERCEL_URL` 加入。服务端密钥仅存放在 Vercel 或维护者私有凭据中。[Vercel 官方流程](https://vercel.com/docs/deployments/environments#verifying-a-production-build-before-promotion)

## 验收与晋升

1. 合并 PR 后，在 Deployments 中打开对应 `main` 提交的 Production 部署。等待 **Ready**，核对提交 SHA，复制该次部署的唯一 HTTPS URL。手动从已关联的项目创建候选版本也可运行 `vercel deploy --prod --skip-domain`。
2. 对这个 URL 运行 `python scripts/check_deployment.py https://<该次部署主机>`。检查覆盖匿名首页跳转、登录表单、CSS 和 JavaScript。若启用了 Deployment Protection，在已登录 Vercel 的浏览器中通过保护页，再检查这些页面及资源。用已有班级账户抽查资料列表、搜索、授权下载。候选版本连接真实生产资料库和私有 bucket，上传、重置密码、删除资料都会立即影响线上数据。
3. 验收通过后，在该部署菜单选择 **Promote to Production**，或执行 `vercel promote https://<同一个部署主机>`。Vercel 将生产域名指向已验收的构建。打开正式站点复核登录与资料访问。验收失败时修复并生成新的候选构建。
4. 如需回退，在 Deployments 中选择上一个已知正常的生产构建并执行 **Instant Rollback**。数据库与对象存储的变更需要单独处理。

## 数据与管理命令

数据库使用 Supabase PostgreSQL 的 `classlib` schema，私有 bucket 默认为 `classlib-private`。需要数据库迁移的发布，先备份并核对迁移计划，从有生产变量的受控终端执行 `python manage.py migrate`。新结构须兼容当前线上版本，待旧版本退出后再清理旧结构。新表应启用 RLS。账户导入和替换见[账户与权限组](accounts.md)。

首次从旧 SQLite 与私有目录导入资料时，使用 `scripts/legacy/deploy_data.py` 的 `verify`、`export`、`migrate`、`files`、`audit` 子命令。历史标签清理工具 `scripts/legacy/upgrade_release.py` 仅用于对应旧版本。历史工具从仓库根目录的私有 `.env` 读取连接信息，备份与导出位于 `deploy-private/`。日常发布使用上面的候选构建流程。

## 自动化检查

GitHub Actions 在临时 SQLite 数据库中运行单元测试，存储接口使用测试替身或临时目录。可用同样的命令复现，无需运行本地网站或提供生产凭据。

```sh
python -m pip install -r requirements.txt
python manage.py makemigrations --check --dry-run --settings=config.test_settings
python manage.py test accounts library --settings=config.test_settings
python scripts/audit_secrets.py
```

`scripts/smoke_production.py` 是可选的生产端到端写入检查，创建临时用户、会话、文件和文件夹，需要生产数据库、私有存储访问和根目录私有 `.env`。日常候选验收使用上面的只读检查。
