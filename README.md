# ClassLib

ClassLib 是班级内部的学习资料库。学生可以搜索和下载资料，教师可以上传和整理文件，管理员负责账户与权限组。当前版本为 1.2.0。[正式站点](https://classlib-theta.vercel.app/) · [版本记录](CHANGELOG.md)

## 开发与发布

从 `main` 建立短期主题分支，提交 PR，由 GitHub Actions 运行 Django 测试和仓库检查。合并到 `main` 后，Vercel 用生产配置构建预发布版本。通过该部署的唯一 URL 验收，再手动将同一个构建晋升到生产域名。[发布与回退](docs/deployment.md)

## 仓库导航

| 目录 | 职责 |
| --- | --- |
| `accounts/` | 身份验证、账户、权限组与对应测试 |
| `library/` | 资料目录、搜索、私有存储、直传与对应测试 |
| `config/` | Django 公共配置、生产配置、自动化测试配置和应用入口 |
| `templates/`、`static/` | 页面模板、样式、浏览器脚本 |
| `scripts/` | 部署验收与仓库审计工具，历史数据迁移工具位于 `legacy/` |
| `docs/` | 维护文档，历史需求与版本方案位于 `archive/` |

Django 保存资料元数据及权限，文件存入 Supabase 私有 bucket。云端上传使用签名凭据，大于 6 MiB 时使用 TUS 分块上传。下载由 Django 鉴权后签发 60 秒链接。账户模型及清单维护见[账户与权限组](docs/accounts.md)。
