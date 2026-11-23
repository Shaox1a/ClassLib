# ClassLib

ClassLib 是班级内部的学习资料库。学生可以搜索和下载资料，教师可以上传和整理文件，管理员负责账户与权限组。当前版本为 1.2.0。[正式站点](https://classlib-theta.vercel.app/) · [版本记录](CHANGELOG.md)

## 开发与发布

从 `main` 建立短期主题分支，提交 PR，由 GitHub Actions 运行 Django 测试和仓库检查。合并到 `main` 后，Vercel 用生产配置构建预发布版本。通过该部署的唯一 URL 验收，再手动将同一个构建晋升到生产域名。[发布与回退](docs/deployment.md)

## 验证改动

在已安装 Python 3.12 的环境中，从仓库根目录执行以下命令。Django 测试使用临时 SQLite 数据库和测试存储，无需启动网站或配置生产凭据。

```sh
python -m pip install -r requirements.txt
python manage.py makemigrations --check --dry-run --settings=config.test_settings
python manage.py test accounts library --settings=config.test_settings
python scripts/audit_secrets.py
```

账户测试放在 `accounts/tests/`，资料库测试放在 `library/tests/`。可按模块单独运行，例如 `python manage.py test library.tests.test_direct_upload`。

仓库审计检查工作区及已获取的分支、标签和 PR 历史。若根目录存在私有 `账户.md`，脚本还会对照部署端清单检查账户信息。CI 使用公开规则检查凭据格式和忽略配置。使用 `--all-refs` 可将本机备份引用和工具快照也纳入审计。

## 仓库导航

| 目录 | 职责 |
| --- | --- |
| `accounts/` | 身份验证、账户、权限组与对应测试 |
| `library/` | 资料目录、搜索、私有存储、直传与对应测试 |
| `config/` | Django 公共配置、生产配置、自动化测试配置和应用入口 |
| `templates/`、`static/` | 页面模板、样式、浏览器脚本 |
| `scripts/` | 候选部署的只读 HTTP 验收和仓库敏感信息审计 |
| `docs/` | 维护文档，历史需求与版本方案位于 `archive/` |

Django 保存资料元数据及权限，文件存入 Supabase 私有 bucket。云端上传使用签名凭据，大于 6 MiB 时使用 TUS 分块上传。下载由 Django 鉴权后签发 60 秒链接。账户模型及清单维护见[账户与权限组](docs/accounts.md)。
