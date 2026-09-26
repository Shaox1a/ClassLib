# ClassLib v0.1

> 面向班级内部的私有学习资料管理网站。
> 核心目标：教师方便上传和管理资料，学生能够快速查找、浏览和下载资料。

---

## 1. 项目定位

ClassLib 用于长期保存和管理班级学习资料。

```text
教师 → 上传资料 → ClassLib → 学生搜索 / 浏览 / 下载
```

聊天软件继续承担通知和交流功能，ClassLib 专注于资料管理。

### 核心原则

* **简单**：只解决资料管理问题。
* **私有**：仅允许班级成员访问。
* **权限清晰**：学生、教师、管理员拥有不同权限。
* **移动端优先**：手机浏览器正常使用。
* **文件与网站分离**：网站管理信息和权限，对象存储保存文件。

---

## 2. 功能范围

### 2.1 账户

角色及权限：

| 角色  | 权限               |
| --- | ---------------- |
| 学生  | 查看、搜索、下载         |
| 教师  | 查看、搜索、下载、上传、管理资料 |
| 管理员 | 用户、资料、权限、系统管理    |

功能：

* 登录 / 退出
* 修改密码
* 管理员创建账号
* 启用 / 禁用账号
* v0.1 不开放公开注册

---

### 2.2 文件夹

采用树状目录结构。

支持：

* 创建文件夹
* 重命名
* 删除
* 移动
* 浏览子文件夹

示例：

```text
高一资料库
├── 语文
│   ├── 课件
│   ├── 讲义
│   └── 作文
├── 英语
│   ├── 课件
│   ├── 单词
│   └── 阅读
├── 数学
├── 物理
├── 化学
└── 公共资料
```

---

### 2.3 文件

保存以下信息：

* 文件名
* 文件大小
* 文件类型
* 所在文件夹
* 上传者
* 上传时间
* 更新时间
* 对象存储 Key

支持：

* 上传
* 下载
* 重命名
* 移动
* 删除
* 搜索

第一版支持：

```text
PDF
PPT / PPTX
DOC / DOCX
XLS / XLSX
ZIP
图片
TXT
```

---

### 2.4 搜索

支持搜索：

* 文件名
* 文件夹名
* 学科
* 标签

v0.1 暂不实现文档全文搜索。

---

### 2.5 标签

一个文件可以拥有多个标签。

第一版由教师管理标签。

示例：

```text
#数学
#高一
#函数
#练习题
#期中复习
```

---

## 3. 权限模型

| 角色  | 查看 | 下载 | 上传 | 管理 |
| --- | -: | -: | -: | -: |
| 学生  |  ✓ |  ✓ |  ✗ |  ✗ |
| 教师  |  ✓ |  ✓ |  ✓ |  ✓ |
| 管理员 |  ✓ |  ✓ |  ✓ |  ✓ |

“管理”包括：

* 创建文件夹
* 删除文件
* 重命名
* 移动
* 修改资料信息

### 权限原则

所有权限必须由后端检查。

前端隐藏按钮只能作为 UI 控制，不能作为真正的权限保护。

未来可以增加文件夹级权限：

```text
FolderPermission
├── folder
├── group
├── can_view
├── can_upload
└── can_manage
```

---

## 4. 文件存储架构

网站负责：

* 用户
* 权限
* 文件夹
* 文件信息
* 搜索
* 业务逻辑

对象存储负责：

* PDF
* PPT
* Word
* Excel
* ZIP
* 图片
* 其他实际文件

架构：

```text
Django
   │
   ├── 用户
   ├── 权限
   ├── 文件夹
   ├── 文件元数据
   └── 搜索
          │
          ↓
   Object Storage
          │
          ├── PDF
          ├── PPT
          ├── DOCX
          ├── ZIP
          └── 图片
```

数据库只保存文件元数据和 `storage_key`，不保存大型文件本体。

---

## 5. 上传与下载

### 上传流程

```text
教师
  ↓
选择文件
  ↓
Django 检查权限
  ↓
生成上传凭证
  ↓
浏览器直接上传到对象存储
  ↓
上传成功
  ↓
Django 保存 File 信息
```

### 下载流程

```text
学生
  ↓
请求文件
  ↓
Django 身份验证
  ↓
Django 检查下载权限
  ↓
生成临时下载 URL
  ↓
浏览器直接从对象存储下载
```

核心原则：

```text
Django：负责身份、权限、业务逻辑
Object Storage：负责文件传输
```

这样可以减少服务器本身的文件传输压力。

---

## 6. 数据模型

### User

```text
User
├── username
├── password
├── role
├── is_active
└── created_at
```

### Folder

```text
Folder
├── name
├── parent
└── created_at
```

### File

```text
File
├── name
├── folder
├── storage_key
├── size
├── mime_type
├── uploader
├── created_at
└── updated_at
```

### Tag

```text
Tag
└── name
```

### FileTag

```text
FileTag
├── file
└── tag
```

### 后续扩展

```text
FolderPermission
├── folder
├── group
├── can_view
├── can_upload
└── can_manage
```

---

## 7. 技术栈

| 部分      | 技术                                          |
| ------- | ------------------------------------------- |
| 后端      | Python + Django 5.2 LTS                     |
| 前端      | Django Templates + HTMX + Tailwind CSS      |
| 前端增强    | 少量 Alpine.js                                |
| 开发数据库   | SQLite                                      |
| 生产数据库   | PostgreSQL                                  |
| 文件存储    | 腾讯云 COS / 阿里云 OSS / 七牛 Kodo / Cloudflare R2 |
| Web 服务器 | Nginx                                       |
| 部署      | Docker                                      |
| HTTPS   | Let's Encrypt / 云厂商证书                       |
| 可选加速    | EdgeOne                                     |

### 架构原则

第一版采用单体架构：

```text
浏览器
   ↓
Nginx
   ↓
Django
   ├── PostgreSQL
   └── Object Storage
```

暂不引入 React / Vue 前后端分离架构。

---

## 8. 项目结构

```text
classlib/
│
├── manage.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── accounts/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   └── admin.py
│
├── library/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── forms.py
│   ├── permissions.py
│   ├── services.py
│   └── admin.py
│
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── home.html
│   ├── folder.html
│   └── file.html
│
├── static/
│   ├── css/
│   └── js/
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### 模块职责

```text
accounts/
    用户、登录、角色

library/
    文件夹、文件、标签、搜索

permissions.py
    权限判断

services.py
    上传、下载、对象存储业务逻辑
```

---

## 9. 页面规划

第一版核心页面：

```text
/login
    登录页面

/
    首页 / 资料库首页

/folder/<id>
    文件夹内容

/file/<id>
    文件详情

/search
    搜索结果

/admin/
    管理后台
```

### 首页示例

```text
┌──────────────────────────────┐
│ ClassLib            🔍 搜索  │
├──────────────────────────────┤
│ 📁 语文                       │
│ 📁 英语                       │
│ 📁 数学                       │
│ 📁 物理                       │
│ 📁 化学                       │
│ 📁 公共资料                   │
└──────────────────────────────┘
```

移动端优先设计，保证手机浏览器操作方便。

---

## 10. 安全要求

第一版至少实现：

* HTTPS
* Django 密码哈希
* Session 登录认证
* CSRF 防护
* 后端权限检查
* 文件类型校验
* 上传大小限制
* 私有对象存储
* 临时下载 URL
* 禁止未授权访问

重点：

```text
用户是否有权限访问文件
        ↓
      后端判断
        ↓
  有权限 → 返回临时 URL
  无权限 → 拒绝访问
```

---

## 11. 开发路线

### Phase 1：项目基础

* 创建 Django 项目
* SQLite
* 基础模板
* 基础页面
* Docker 开发环境

### Phase 2：账户系统

* 登录 / 退出
* 用户模型
* Student / Teacher / Admin
* 管理员创建账号
* 启用 / 禁用账号

### Phase 3：资料库

* Folder
* File
* 文件上传
* 文件下载
* 文件夹浏览
* 重命名
* 删除
* 移动

### Phase 4：权限与搜索

* 后端权限系统
* 文件名搜索
* 文件夹搜索
* 标签
* 教师管理功能

### Phase 5：对象存储

* 接入 COS / OSS / Kodo / R2
* 临时上传凭证
* 临时下载 URL
* 文件与网站服务器分离

### Phase 6：生产部署

* PostgreSQL
* Docker Compose
* Nginx
* HTTPS
* 域名
* 可选 EdgeOne

---

## 12. MVP 完成标准

```text
[ ] 用户可以登录
[ ] 管理员可以创建学生 / 教师账号
[ ] 管理员可以禁用账号
[ ] 教师可以创建文件夹
[ ] 教师可以上传文件
[ ] 学生可以浏览资料
[ ] 学生可以搜索资料
[ ] 学生可以下载资料
[ ] 学生不能上传文件
[ ] 学生不能删除资料
[ ] 教师可以删除 / 重命名 / 移动资料
[ ] 文件存储与网站逻辑分离
[ ] 手机浏览器可以正常使用
[ ] 网站使用 HTTPS
[ ] 未授权访问会被拒绝
```

完成这些功能后，ClassLib v0.1 即可投入班级内部使用。

---

## 13. 暂不开发的功能

为了控制项目规模，以下功能暂时保留：

```text
聊天
评论
点赞
收藏
私信
在线 Office 编辑
文件版本管理
回收站
多人协作编辑
OCR
文档全文搜索
AI 搜索
公开注册
多班级管理
复杂分享链接
```

---

## 14. 最终架构

```text
                     用户
                      │
                      ↓
                    HTTPS
                      │
                      ↓
                    Nginx
                      │
                      ↓
                   Django
                 ┌────┴────┐
                 ↓         ↓
            PostgreSQL   Object Storage
                           │
                  ┌────────┼────────┐
                  ↓        ↓        ↓
                 PDF      PPT      ZIP
```

可选加入 CDN / EdgeOne：

```text
用户
 ↓
EdgeOne
 ↓
Nginx
 ↓
Django
 ├── PostgreSQL
 └── Object Storage
```

---

## 15. 核心使用逻辑

```text
管理员
  ↓
创建学生 / 教师账号

教师
  ↓
创建目录
  ↓
上传学习资料
  ↓
整理 / 重命名 / 移动 / 删除

学生
  ↓
进入资料库
  ↓
搜索 / 浏览
  ↓
下载资料
```

ClassLib 的核心只围绕三件事：

```text
账户
权限
资料
```

在这个核心基础上，再逐步增加搜索、标签、对象存储和部署能力。
