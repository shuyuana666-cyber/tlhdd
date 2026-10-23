# 通利华后台的 Vben Admin 前端

`admin-vben/` 基于 [vbenjs/vue-vben-admin](https://github.com/vbenjs/vue-vben-admin) 5.x（MIT License，基线提交 `c5204a69b8374682c59cb35e7a43d474cf125a82`）定制，使用 Vue 3、Vite、TypeScript 和 Ant Design Vue。

## 目录

- `apps/web-antd/src/api`：将 Vben 请求层接到当前 Python 服务的 `/api/admin/*` 接口。
- `apps/web-antd/src/router/routes/modules`：运营总览、车辆管理、配件管理、页面配置、页面内容、分类标签、询盘管理、在线消息、注册用户和系统设置菜单。
- `apps/web-antd/src/views`：按车辆、配件、首页、其他页面、分类标签、询盘、在线消息和用户拆分的业务页面。
- `admin/`：已经构建好的静态产物，由 `server.py` 在 `/admin/` 提供。

## 开发与构建

```powershell
cd admin-vben
pnpm install
pnpm --filter @vben/web-antd dev
pnpm --filter @vben/web-antd build
```

生产构建默认输出到项目根目录的 `admin-vben-build/`。复制到根目录的 `admin/` 后，Python 服务即可提供最新后台：

```powershell
Copy-Item ..\admin-vben-build\* ..\admin -Recurse -Force
python ..\scripts\prepare_admin.py
python ..\scripts\build_release.py --check
```

`prepare_admin.py` 将构建生成的加载主题脚本提取为本站静态文件，使后台符合服务器的 `script-src 'self'` 安全策略。每次复制新构建后都应执行它。

`admin/lucide-local.js` 同时被官网页面使用。构建中转目录不会生成它，因此发布时应保留该文件，不能直接清空整个 `admin/`。开发工具包的 `dist/` 也是 package 入口，不能与应用构建中转目录一起清理。

## 当前维护位置与验证

自 2026-10-05 起，使用本目录作为开发入口；依赖已经按锁文件离线安装，Git 历史也已保留在本目录。原 `tmp/vue-vben-admin/` 连同其 Git、环境配置、未提交改动和旧 content 页面，完整归档到：

```text
C:\Users\admin\AppData\Local\tlhdd-project-archives\20261005-cleanup\vue-vben-admin
```

没有提交、重置或推送 Git。历史目录只用于恢复和对照，后续开发请修改本目录。Windows 归档路径较长，部分依赖文件需要支持长路径的工具；恢复整个目录到较短路径可保留其相对符号链接。

本次通过的验证命令：

```powershell
pnpm --filter @vben/web-antd typecheck
pnpm test:unit
pnpm --filter @vben/web-antd build
```

验证构建实际使用 Vite 的 `--outDir` 指向项目外的归档验证目录，未覆盖正在使用的 `admin/`。旧 `admin-vben-build/` 已归档，下次常规构建会重新生成该中转目录。

应用目前使用前端路由模式。`/api/menu/all` 没有 Python 后端实现；在实现相应接口前，不应切换到 backend/mixed 动态菜单模式。相关基础设施保留。

完整整理记录及保留项见 `../docs/cleanup-audit-2026-10-05/RESULT.md`。

后台登录使用数据库中现有的管理员账号和密码；`TLHDD_ADMIN_USER` / `TLHDD_ADMIN_PASSWORD` 仅在首次创建空站点管理员时使用。会话由服务端 HttpOnly Cookie 管理。

列表记录的删除操作会写入后端 `DELETE` 接口并永久删除数据库记录。删除注册用户时，会同时删除其关联询盘、在线消息会话、论坛帖子、上传额度记录和登录会话；删除消息会话时会级联删除聊天消息。内置分类标签也可删除，默认页面数据只在首次初始化时写入，之后不会因重启而恢复已删除记录。

“页面配置”和“页面内容”中的图片槽支持预览、上传替换、清除和还原默认。图片只接受通过服务端校验的 jpg、png、webp 文件，单张最大 20MB；清除图片会保留槽位，彻底删除素材槽则会从网站对应位置移除图片。

车辆管理和配件管理支持“批量删除”：点击后显示当前页的多选框，可全选、取消多选，确认后通过 `POST /api/admin/{vehicles|parts}/bulk-delete` 原子删除选中记录。每次最多 100 条；翻页、筛选或刷新会清空选择。如果某条记录已被删除，整批操作不执行，需刷新后重新选择。上传文件保持原有删除规则，以免影响其他页面共用的素材。
