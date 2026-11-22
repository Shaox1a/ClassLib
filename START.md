# 本地启动 ClassLib（暂不使用 Docker）

## 一键启动（Windows）

双击项目根目录的 `start-local.cmd`，或在 PowerShell 中运行：

```powershell
cd E:\projects\ClassLib
.\start-local.cmd
```

脚本会创建虚拟环境（缺失时）、安装依赖（首次或 requirements.txt 变更时）、检查配置、迁移本地数据库并启动网站。打开 <http://127.0.0.1:8000/login/>，按 `Ctrl+C` 停止。

脚本使用本地 SQLite 和 `private_files/`；环境覆盖仅对运行期间的进程有效，不读取或修改 `.env`，结束时恢复终端原有环境变量。已有本地账号可直接登录，新增管理员使用：

```powershell
.\start-local.cmd -CreateAdmin
```

其他选项：`-Port 8001` 更换端口；`-SetupOnly` 只准备环境；`-SkipInstall` 跳过依赖安装（依赖已安装时使用）；`-NoReload` 关闭开发自动重载。

## 手动启动

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

搜索页可按文件名、文件夹名和学科（根目录文件夹）查找。

## 1.1 本地体验

上传页可一次多选任意格式文件（包括空文件），逐项显示结果，失败后可点击重试。首页、文件夹和搜索页的“大图标 / 列表”按钮切换显示方式。登录失败会在当前页面保留遮罩密码，方便修改重试。

应用不设文件大小上限；本地上传以磁盘临时文件方式处理。云端实际可上传大小受存储平台上限影响。
