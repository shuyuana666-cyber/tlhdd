# 通利华汽车集团网站

2026-10-23 增加可选 Redis 公共接口缓存、S3 兼容媒体存储与 CDN 分发，并合并页面内容的重复查询。默认保留本地运行模式。配置、迁移、验证与回退步骤见 [Redis 与对象存储接入](docs/Redis与对象存储接入.md)。

2026-10-05 已完成项目目录归档整理、后台开发环境恢复和依赖声明精简。当前结果与验证范围见 [整理完成报告](docs/cleanup-audit-2026-10-05/RESULT.md)。后续后台开发使用 `admin-vben/`；历史源码、Git、环境配置与发布包保留在项目外归档，确认可清理的旧依赖、缓存、日志、截图和构建产物已移入 Windows 回收站。

本项目包括企业官网、车辆与配件目录、用户注册、用户中心内容发布、管理后台和 Python HTTP 服务。业务数据统一存储在 **Oracle MySQL 8.0.16 或更新版本**中，字符集为 `utf8mb4`。

## 本地启动

先安装 MySQL、创建空数据库和最小权限应用账号：

```sql
CREATE DATABASE tlhdd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tlhdd_app'@'127.0.0.1' IDENTIFIED BY 'replace-with-a-long-random-secret';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES ON tlhdd.* TO 'tlhdd_app'@'127.0.0.1';
```

安装 Python 依赖，并在 PowerShell 设置连接配置：

```powershell
python -m pip install -r requirements.txt
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_DATABASE="tlhdd"
$env:MYSQL_USER="tlhdd_app"
$env:MYSQL_PASSWORD="your-database-secret"
$env:TLHDD_ADMIN_USER="admin"
$env:TLHDD_ADMIN_PASSWORD="your-strong-initial-admin-password"
python server.py
```

管理员初始密码至少 12 位。服务首次启动会检查 MySQL 版本、创建表和索引，并补齐页面默认内容。默认只监听 `127.0.0.1:4173`；需要局域网直连时再显式设置 `HOST=0.0.0.0`。配件演示数据默认不自动发布；需要演示内容时，可在启动前显式设置 `TLHDD_ENABLE_DEMO_SEED=1`。

密码使用 PBKDF2-HMAC-SHA256（600,000 次迭代）保存。旧版 120,000 次迭代的哈希会在用户下次成功登录时自动升级，不需要批量重置密码。

## 部署前检查

先在项目根目录执行：

```powershell
python scripts/build_release.py --check
python -m py_compile server.py init_service.py content_defaults.py
node --check assets/js/main.js
```

`build_release.py` 只收集运行所需的 Python、页面、`assets/`、已构建的 `admin/` 和数据库 schema；会核对页面引用和默认图片是否在包内。构建可预览的发布包：

```powershell
python scripts/build_release.py output/tlhdd-release.tar.gz
```

开发用的 `admin-vben/` 源码、重复构建目录、测试截图、日志、数据库缓存和 `uploads/` 不进入发布包。默认展示图片已经放在 `assets/default-media/`，新装站点可以直接显示；后台上传或替换过的图片仍在 `uploads/`，必须和相应的 MySQL 数据一同迁移与备份。

## 部署

本项目已于 2026-10-01 上线到 `https://tlhdd.cn`；服务器目录、独立 MySQL、证书续期、验证结果及回滚步骤见 [上线与回滚记录](deploy/production-runbook.md)。后续代码发布不应重新导入此次迁移 SQL。

`deploy/deploy-tlhdd.ps1` 使用严格 SSH 主机校验和服务器上单独维护的环境文件。SSH 管理用户与运行网站的非 root 用户分开；前者需要创建目录与 systemd 服务的权限。先把服务器的 MySQL 配置写入 `/etc/tlhdd/tlhdd.env`（参考 `deploy/tlhdd.env.example`），并将服务器主机密钥加入本机 `known_hosts`，然后运行：

```powershell
./deploy/deploy-tlhdd.ps1 -Server example.com -SshUser deploy -ServiceUser tlhdd -ServiceName tlhdd-v2 -Port 4174 -RemoteApp /srv/tlhdd -SshKeyPath "$HOME/.ssh/id_ed25519"
```

脚本会重新校验并构建最小发布包，不会上传 `data/`、`uploads/`、日志、临时目录或环境文件。首次从旧版迁移时，先运行 `python scripts/prepare_migration.py <私有临时目录>` 导出本地 MySQL 并打包上传文件；单独备份旧服务器数据、建立新版数据库并恢复这些数据后，再执行代码部署脚本。迁移包含用户数据，不要放在网站目录或提交到版本库。部署完成后检查首页、后台、登录、询盘和图片。Nginx 示例见 `deploy/nginx/tlhdd.cn.conf`，启用前核对域名、证书和反向代理端口；服务默认只监听本机回环地址。

## 数据与备份

- MySQL 连接由 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD` 配置。
- 本地页面缓存位于 `data/exchange_rate_cache.json`，不含业务数据库。
- 上传文件位于 `uploads/YYYY/MM/`，需与 MySQL 分开纳入备份。只恢复数据库而未恢复 `uploads/` 会使既有车辆和后台自定义图片缺失。
- 后台“系统设置”下载 MySQL `.sql` 逻辑备份；备份不包含有效登录会话。
- 可选 `MYSQL_SSL_CA` 启用 MySQL TLS CA 验证。

主要模块：`server.py` 承载 HTTP/API 入口；`database.py` 负责 MySQL 连接、SQL 适配和备份，`repositories.py`、`record_utils.py` 提供通用查询与数据转换；`init_service.py` 管理 MySQL schema 初始化和默认内容，`auth_service.py` 管理账户与密码，`admin_service.py` 管理后台目录查询，`catalog_service.py`、`chat_service.py`、`forum_service.py`、`inquiry_service.py`、`content_service.py` 管理车辆配件目录、站内消息、论坛、询盘和网站内容业务，`mcp_service.py` 管理 MCP 工具 schema 与目录操作；`app_config.py` 集中环境配置与静态资源规则，`url_utils.py` 校验公开图片地址；`content_defaults.py`、`demo_seed.py` 管理初始内容；`http_utils.py`、`static_files.py`、`uploads.py` 分别处理请求安全、静态资源访问和上传；`exchange_rates.py` 管理汇率缓存。`schema.mysql.sql` 定义 MySQL 表结构。

## 管理后台

后台功能清单和日常操作说明见 [后台功能与使用手册](docs/后台功能与使用手册.md)，可编辑的 [Word 版手册](docs/后台功能与使用手册.docx) 同步保留。手册覆盖当前 11 个业务页面、操作限制、删除影响和备份范围。

管理后台已采用开源的 [Vue Vben Admin](https://github.com/vbenjs/vue-vben-admin) 5.x（MIT License）构建，定制源码位于 `admin-vben/`，构建产物位于 `admin/`。它复用当前 Python 服务的 `/api/admin/*` 接口和 HttpOnly 会话，不需要单独部署 Node 服务。具体开发与构建说明见 [`admin-vben/README.tlhdd.md`](admin-vben/README.tlhdd.md)。前台 CSS/JS 使用服务端重新验证缓存，修改后不再需要逐页手动更换 `?v=` 版本号。
