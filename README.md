# ClassLib

ClassLib 是面向班级内部的私有学习资料库。当前代码完成开发路线的 Phase 1：Django 项目骨架、SQLite、基础页面和 Docker 开发环境。

## 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

打开 <http://127.0.0.1:8000/>。登录页面位于 `/login/`，管理员后台位于 `/admin/`。

## Docker 开发环境

确认 Docker Desktop 已启动后，在项目根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

首次启动会自动执行 SQLite 迁移，访问 <http://127.0.0.1:8000/>。

停止服务：

```powershell
docker compose down
```

## Git

项目使用根目录的 `.gitignore`、`.gitattributes` 和 `.env.example`。初始化仓库后：

```powershell
git init
git add .
git commit -m "Initialize ClassLib Phase 1"
```

如果 Git 尚未配置提交身份，请先执行：

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Phase 2 会加入自定义用户角色、账号管理和账号启用/停用功能；Phase 3 再接入文件夹和文件模型。
