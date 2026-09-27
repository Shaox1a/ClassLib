# 本地启动 ClassLib（暂不使用 Docker）

在项目根目录打开 PowerShell，首次运行依次执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

管理员账号创建完成后，每次启动执行：

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

打开 <http://127.0.0.1:8000/login/> 登录。管理员可以在 <http://127.0.0.1:8000/accounts/> 创建学生、教师账号并启用或停用账号。按 `Ctrl+C` 停止服务。

教师和管理员登录后可创建文件夹、上传资料；学生可浏览和下载。上传文件保存在 `private_files/`，备份时请同时备份它和 `db.sqlite3`。

搜索页可按文件名、文件夹名、学科（根目录文件夹）和标签查找。教师可在“标签”页面创建标签，并在文件详情页为文件设置标签。
