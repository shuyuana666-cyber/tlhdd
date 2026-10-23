# 项目清理审计报告

> 本文保留清理前的审计结论与候选清单。用户随后授权处理后，已执行可恢复归档、恢复正式开发环境并移除 5 项冗余依赖声明。**当前状态请查看 [整理完成报告](RESULT.md)、`execution.json` 与 `validation-after.json`。** 下文的“尚未删除”是初始报告时的状态，不表示候选目录现在仍在原位。

审计日期：2026-10-05（北京时间）。项目：`C:\Users\admin\Desktop\tlhdd`。

**当前完成的是扫描、依赖分析和清理前基线验证。遵照“先不要删除文件”，没有执行删除，也没有修改业务代码、数据库记录、环境配置或部署配置。**

实际删除文件 **0** 个，实际删除文件夹 **0** 个，实际释放空间 **0**。以下均为建议，不能把候选空间当成已释放空间。

## 范围、方法与限制

- 遍历全部目录，包括隐藏文件、安装依赖、临时源码副本、Git 元数据、上传文件和构建产物。盘点得到 **151,723 个文件、19,215 个目录、2,070,297,327 字节，约 1.93 GiB**；未遇到读取错误，遍历不跟随目录符号链接。初次记录漏记了被跳过的链接，执行阶段补查确认临时 pnpm 工作区有 **5,859 个符号链接**，已全部保留；详见 `execution.json`。
- 大小是文件逻辑大小之和，不是 NTFS 实际分配空间；硬链接、压缩和簇大小会影响真正释放的空间。上述盘点不包含本次新增报告。
- 检查根目录 Python 的 AST、import 引用图、入口和运维脚本；检查 pnpm workspace、package manifests、构建配置、路由、动态加载、CI、Docker、部署脚本、Nginx、数据库 schema、环境配置文件位置以及 README 中的操作方式。
- 对不属于安装依赖和 `.git` 内部的 **6,947 个文件**按大小和 SHA-256 检查内容重复。`node_modules` 内部按目录、清单和用途评估，没有逐个把第三方内部模块当作项目未使用代码。
- 检查正式后台产物的真实 JS import、动态 import 和 Vite preload 依赖映射，避免把打包器内部模块名称误当成磁盘路径。
- 使用已有 MySQL 配置做只读事务检查，只记录表数量、引用数量和缺失文件情况，没有把密码、连接配置值或客户记录写入报告。
- 无引用只是候选线索。数据库、浏览器生成地址、动态组件加载、外部链接、另一环境和人工运维用途仍会使文件有用。
- 当前前端缺少已安装依赖，无法完成正式源码的 TypeScript、Vue 单元测试和生产构建；浏览器视觉与交互未执行。本报告不声称已经证明所有前端变量、导出和依赖均被使用，也不声称全链路测试通过。

## A. 建议直接删除

这些是第一阶段的低风险候选。删除缓存前仍应结束使用对应缓存的开发工具；未来运行会重新产生缓存。这份清单不包含源代码、用户数据、构建中转产物、环境文件或 `.git`。

| 路径 | 类型 / 数量 | 删除原因与证据 | 风险等级 |
|---|---|---|---|
| `__pycache__/` | Python 字节码缓存；21 文件；301,994 字节 | 对应源文件仍在；Python 从源码重新生成；README、发布包收集和入口均使用源码，发布包不含此目录。 | 低 |
| `scripts/__pycache__/` | 运维脚本字节码缓存；4 文件；23,615 字节 | 四个运维脚本源码仍在；文档直接运行 `.py`；缓存不承担迁移或备份数据用途。 | 低 |
| `.playwright-cli/` | 历史浏览器临时输出；150 文件；3,009,597 字节 | 39 个 console 日志、102 个页面快照、9 张截图；未发现应用、构建、部署脚本读取这些文件。`app_config.py` 中的出现是禁止公开访问的目录名，不是资源读取依赖。不是浏览器登录 profile。 | 低 |
| `tmp/backups/` | 空目录 | 扫描时没有文件或子目录；未发现项目命令依赖该本地目录。不会触碰服务器回滚备份。 | 低 |
| `admin-vben/apps/web-antd/src/views/content/` | 空目录 | 正式源码目录中没有组件，路由入口也没有导入 content 模块；现有 `import.meta.glob('../views/**/*.vue')` 不会从空目录加载组件。 | 低 |

**A 合计：175 个文件、5 个目录，逻辑大小 3,335,206 字节，约 3.18 MiB。** 两个空目录已经包含在 5 个目录中，没有重复计数。完整文件路径及 SHA-256 见 `candidates.json`。这不包括 `tmp/vue-vben-admin/` 中另一个仍有内容的 `views/content/`。

## B. 建议确认后删除

下面均为“需要人工确认”，当前不删除。目录条目不是授权递归删除其中全部内容，尤其不能连带删除 `.git`、`.env`、锁文件、用户数据和数据库文件。

| 路径 | 删除原因 / 候选依据 | 可能影响 / 删除前必要条件 | 风险等级 |
|---|---|---|---|
| `tmp/vue-vben-admin/node_modules/` 及其工作区依赖链接/安装记录 | 安装依赖逻辑大小约 1.60 GiB，是最大空间来源；可由锁文件安装恢复。 | 正式 `admin-vben/` 没有 `node_modules`，这份副本目前是项目内已有依赖的开发环境。先在正式目录安装并验证构建、类型检查、测试，以及是否需要离线开发；不能按未使用包名逐个剪裁 pnpm 存储。 | 中 |
| `tmp/vue-vben-admin/` 中重复源码 | 与正式源码有 2,045 个文件完全一致，存在重复维护。 | **禁止整目录删除**：内含独立 `.git`、未提交修改、`.env` 和锁文件。需先归档差异、明确工作副本用途，再逐文件决定哪些重复源码可移出工作目录；Git 和环境文件始终保留。 | 高 |
| `tmp/vue-vben-admin/apps/web-antd/src/router/routes/modules/content.ts`、`tmp/vue-vben-admin/apps/web-antd/src/views/content/index.vue` | 临时副本独有的旧“商品与内容”合并页面，正式版本已拆分为车辆、配件、首页、页面等功能。 | 路由入口没有注册旧 content 模块，但动态 views glob 仍能收集组件；还属于 Git 未跟踪的本地定制内容。先确认历史用途与是否要归档，不能当成无主文件。 | 中 |
| `admin-vben-build/` | 237 个文件、约 3.86 MiB；与 `admin/` 有 236 个完全相同的文件。 | Vite 的 `outDir` 和 README 的复制流程明确使用该目录；是构建中转站。当前正式源码不能重建。仅在成功重建/复制、保留正式 `admin/` 后，才能清理旧中转内容。 | 中 |
| `output/playwright/*.png` | 32 张历史 UI 截图，是输出而非应用输入。 | 可能是前后效果比较、移动端问题或上线验收的唯一证据。确认留存需求后再删除或归档。 | 低 |
| `output/playwright/*.js` | 14 个检查或发布辅助脚本，未进入发布包，正式文档启动不依赖它们。 | 部分脚本包含真实线上检查/发布流程，可能仍有人手动运行。先判断哪些需要迁入正式 `scripts/`；审计未运行这些发布脚本。 | 中 |
| `output/tlhdd-release-20261001-bulk.tar.gz` | 旧发布包，约 3.15 MiB。 | 上线 runbook 记录了该文件及 SHA-256；回滚、复现与审计可能使用。须先确认外部备份完整并同步留存记录。 | 中 |
| `output/tlhdd-release-20261001-speed.tar.gz` | 历史发布包，约 3.15 MiB。 | 同样有 runbook 与校验值，不因日期较旧就认为失效。须确认是否为当前回滚依据及外部归档是否完整。 | 中 |
| `logs/*.log` | 9 个历史运行日志，共 243,107 字节。 | 日志有排障用途；`启动网站.bat` 实际创建 `logs/` 并向 `logs/server.log` 追加。先停止使用日志的进程、确认保留期；建议轮转日志内容，保留目录和脚本规则。 | 低 |
| `data/used_vehicles_export.json` | 8,383 字节；未在正式源码、配置、脚本和文档发现文件名引用。 | 这是车辆导出数据，可能是人工导入、迁移、备份或其他工具输入。未知原始来源和是否为唯一副本，不能直接删除。 | 中 |
| 当前数据库引用匹配不到的 16 个 `uploads/` 文件 | 只读扫描数据库字符串地址，并补充现有缩略图/优化图派生地址后，仍有 16 个未匹配。 | 只检查了本地数据库；原图保存、外部链接、线上数据库或备份仍可能使用。**不认定为孤儿文件，不删除**。没有进行跨环境引用合并。 | 高 |
| `uploads/` 中相同内容的不同路径 | 发现 146 组涉及上传资源的相同内容，上传目录内的理论冗余约 32.23 MiB。 | 不同 URL 可能由不同记录或外部链接引用；重复内容不等于重复用途。需要事务性更新全部引用、保留原图及备份，并完成回滚设计后才可考虑去重。 | 高 |

`output/playwright/` 合计 46 个文件、约 9.24 MiB。B 中有重叠范围，不应简单相加；1.60 GiB 的依赖和 32.23 MiB 的资源理论重复量都不是安全可直接释放空间。

## C. 建议保留

| 路径 / 内容 | 看起来可能多余但必须保留的原因 |
|---|---|
| `admin/` 全目录 | 实际公开后台 `/admin/` 的静态产物；发布包明确收集。其哈希块有动态加载关系，不能凭文件名删 demo、旧风格名称或 vendor 块。 |
| `admin/lucide-local.js` | 13 个官网 HTML 页面显式使用它；不仅是后台图标脚本。发布校验也要求存在。 |
| `admin/loading-theme.js` 和处理后的 `admin/index.html` | 实际运行版本完成了内联脚本外置，符合 CSP。原始 build 与正式 index 不相同，不能以“重复产物”覆盖正式版本。 |
| `admin-vben/` 源码、`internal/`、`packages/`、工具目录内 `dist/` | pnpm workspace 与包 manifest 形成开发依赖图；例如 `@vben/vite-config` 的入口指向 `dist/index.mjs`，构建工具包的 dist 不能统一删除。 |
| 根目录 21 个 `.py` 模块 | 从 `server.py` 入口均可到达；没有发现完全未引用的根目录模块。 |
| `demo_seed.py` | 被 `init_service.py` 导入，通过 `TLHDD_ENABLE_DEMO_SEED` 显式启用；当前默认关闭不等于废弃。 |
| `mcp_service.py` | HTTP 服务挂载 `/mcp` 并使用 schema 和工具处理函数；可选功能仍有真实入口。 |
| `app_config.py` 中退休 page keys 及初始化兼容逻辑 | 正在过滤/整理旧页面数据；这是兼容与迁移逻辑，不能按 retired/legacy 标签删掉。 |
| `schema.mysql.sql`、`database.py`、`init_service.py`、`scripts/prepare_migration.py` | 数据初始化、MySQL 访问、上传引用校验和迁移/备份需要。 |
| `requirements.txt` | `PyMySQL[rsa]` 被 MySQL 层实际使用；`Pillow` 被上传处理与批量图片优化脚本实际使用，没有发现可证明未使用的 Python 依赖。 |
| 所有 `.env`、`deploy/tlhdd.env.example`、package manifests、pnpm 锁文件与 workspace 配置 | 环境、可重建性、工作区解析的基础。发现 51 个环境文件/模板（含临时副本），均保护；未向报告复制其内容。 |
| `tmp/vue-vben-admin/.git/` | 实际存在的 Git 仓库，含 33 个文件；有已修改和未跟踪的定制源码。**不得删除，也不得被清理父目录连带删除。** 项目根目录本身不是 Git 仓库。 |
| `.gitignore`、`.gitattributes`、`.gitconfig`、`.github/` | 版本控制、Git 配置及自动化配置保护。上游 workflow 当前是否执行不作为删除依据。 |
| `deploy/`、Nginx、部署运行手册、SSL 配置路径 | 生产 systemd、SSH、MySQL、Nginx、回滚流程依赖。TLS 证书引用在服务器上，不因本机不存在对应 `/etc/letsencrypt/` 路径判为失效。 |
| `admin-vben/scripts/deploy/Dockerfile`、Docker 构建脚本与 Nginx | 根 package 的 `build:docker` 仍指向该流程；Dockerfile 使用 `playground/dist`，因此 playground 不是可直接删除的例子目录。 |
| `uploads/` 全部 2,032 个文件，约 280.17 MiB | 用户原图、优化图与缩略图；数据库和运行时生成 URL 共用。既是运行资源也是用户数据。 |
| `assets/default-media/*-thumb.webp` | 五个缩略图没有完整文件名的直接文本引用，但 `assets/js/main.js` 会按原地址生成 thumbnail/optimized URL，不能用全文搜索的无结果判为未使用。 |
| 默认媒体与 uploads 中的相同图片 | 新装站点使用打包在 assets 的默认图片，已有业务记录使用 uploads 地址；两种用途不同。 |
| 根目录及 `assets/images/` 的 favicon / touch icon | 三组内容相同，总计约 54.86 KiB；根目录是公开文件白名单的一部分，assets 版本被前端引用。要先统一 URL 并考虑浏览器缓存/默认 favicon 请求，不能直接删一个位置。 |
| `6ef28aa143fc6f2c0549afdc7e3f26c1.txt` | 在公开根文件白名单和发布包内，可能是站点验证文件；不能按随机文件名删除。 |
| `data/exchange_rate_cache.json`、`data/.gitkeep` | 前者运行时读取，外部汇率接口不可用时可提供旧值；虽然可重新生成，当前只有约 1 KiB，清理收益低而影响可用性。后者维持必要数据目录。 |
| 正式测试、测试快照、LICENSE、品牌来源与许可证 | 测试断言快照不是废弃测试输出；开源许可和资源来源不是运行 import 但对维护和分发重要。 |

## D. 可优化但不建议直接删除

1. **统一维护与构建位置。** 正式源码与临时 Git 副本大部分相同，但后者保留独有 content 页面。两份 Vite 配置只是相对深度不同：正式目录 `../../../admin-vben-build`，临时目录 `../../../../admin-vben-build`，都指向项目根同一构建输出。先在正式目录完成依赖安装、构建与测试，再明确临时副本的归档角色；Git、环境文件和独有改动始终保护。
2. **梳理上游 workspace 应用。** `backend-mock`、其他四种 UI 应用、`docs`、`playground` 不属于仅从根工具依赖与 `web-antd` 出发的 manifest 依赖闭包，但它们仍被 workspace glob、根 package 命令、CI、测试或 Docker 引用。七个目录约 6.27 MiB；去掉源码本身节省有限。若确定长期只维护 Ant Design 版本，应配套调整 workspace、catalog、锁文件、根命令、CI、Docker 和测试范围，再决定精简，不直接删除目录或包名。
3. **保留或补齐动态菜单能力。** `apps/web-antd/src/api/core/menu.ts` 请求 `/menu/all`；request 基址将其对应到 `/api/menu/all`，Python 服务没有该接口。默认 `accessMode='frontend'` 时走前端路由，不调用 backend 菜单回调；切换 backend/mixed 时可能失败。它有函数引用和运行时模式分支，不能当未调用函数删除，应明确支持模式并调整配置或后端。
4. **移除无业务效果的示例偏好需独立评估。** `apps/web-antd/src/preferences.ts` 的 `tenantMode`、`reportTitle`、`defaultTableSize`、`enableFormFullscreen` 未在该 app 的其他业务源码发现字段名使用，但 `definePreferencesExtension` 会动态生成偏好 UI。可精简示例功能及相应文案，不能按静态变量无调用立即删除。
5. **构建后发布流程自动化。** 已存在 `prepare_admin.py` 外置 loading script 的步骤；`lucide-local.js` 是正式 admin 独有的全站依赖。若将中转 build 完全替换 admin，必须保证图标脚本和 CSP 处理后 index 可恢复。优化为可重复的发布准备流程并验证完整性，比手动删构建文件可靠。
6. **日志轮转与产物保留期。** 将 `logs/`、发布包和 UI 验收截图按明确周期归档，避免既有 `.gitignore` 已忽略但磁盘持续增长。不要运行 `git clean -fdx`；保护的上传、环境、临时 Git 仓库和依赖都可能位于忽略目录。
7. **数据库引用与资源去重。** 上传去重需要原图/变体分组、全库引用、线上环境和外链共同分析，采用可回滚方式迁移 URL。当前 146 组重复及 16 个未匹配文件只作为人工调查线索。
8. **梳理文档与发行记录。** 两份中文文档分别承担启动/部署说明和使用说明，有重叠但用途不同；runbook 含实测上线与回滚记录，不能用发布日期当废弃判断。可相互引用，减少重复维护。
9. **修正环境模板的版本跟踪规则可单独处理。** 根 `.gitignore` 中 `.env.*` 会匹配常见 `.env.example`，但当前模板是 `deploy/tlhdd.env.example`。若未来新增 `.env.example`，应明确例外规则。本次没有改 Git 配置。

## 重复代码、废弃代码与依赖结论

- **精确重复：** 非安装依赖、非 `.git` 文件有 2,178 组相同非空内容。主要来自两份 Vben 源码、两套后台产物、上传图片和图标。重复分组见 `duplicates.json`，重复数量不是可删除数量。
- **正式后台产物对比：** admin 有 239 文件，build 有 237；236 个相同，`index.html` 不同，admin 独有 `loading-theme.js` 和 `lucide-local.js`。
- **源码副本对比：** 排除安装依赖、Git 元数据后，正式源码 2,047 文件、临时副本 2,048 文件；2,045 相同，Vite 配置不同，正式独有 `README.tlhdd.md`，临时独有旧 content 路由与页面。
- **Python 未使用代码：** AST 检查没有发现根目录完全未引用模块、顶层未引用函数/类或未使用 import。没有因此进行“代码洁癖”删除。普通局部变量、字符串反射和全部 Vue/TypeScript 导出不属于这项保证。
- **旧实现：** 临时副本中的 content 合并页面是被正式分页面实现替代的候选；它仍被动态 glob 收集且是独有 Git 内容，需要确认。
- **未使用依赖：** Python 两项都有用途；前端未发现足以安全直接删除的包。声明图、barrel export、配置插件、测试工具、CLI 命令、peer 依赖与其他 workspace 均需要一起考虑。由于正式目录没有依赖，未执行完整的前端依赖/未使用导出 lint，不能把静态检查范围外的问题说成不存在。

## 已执行的基线验证

| 检查 | 结果 | 说明 |
|---|---|---|
| `python -B scripts/build_release.py --check` | 通过 | 338 个发布文件，约 6.4 MiB；页面与默认媒体引用、后台文件、CSP script 处理满足已有校验。没有生成新发布包。 |
| 25 个 Python 源文件内存语法编译 | 通过 | 包含 21 个根模块和 4 个运维脚本；使用 Python `compile()`，未向项目生成新 `.pyc`。 |
| 232 个 JS 的 `node --check` | 通过 | 含 assets 前端代码和 admin 产物；语法检查不等于浏览器交互测试。 |
| 实际 `TlhddHandler` HTTP 基线 | **320/320** 符合预期 | 临时回环随机端口提供全部官网页、admin 入口、公开资源、车辆/配件/页面/论坛/site API；未登录账户接口按预期 401。数据库连接强制只读，服务结束后关闭。 |
| 后台 JS import / 动态 import / preload 路径 | 通过 | AST 检查 1,786 项真实模块/预加载引用，未发现缺失文件。打包器内嵌模块 key 与图标对象 key 不作磁盘文件引用。 |
| MySQL 只读引用检查 | 通过 | 本机 MySQL 8.4.9；18 表，687 个 uploads 地址、23 个 assets 地址，缺失资源 0。本机车辆 41、配件 349；未将其当作线上数据状态。 |
| 已有两份发布包 SHA-256 | 与 runbook 一致 | bulk：`f52891d1be327a44dbeed472575135853d2936c13bb94abe969d47a079e4959f`；speed：`36c3487083cdfd1b5dde1689568b12b4d6a79f2862f31207c2d3d6d0576efc85`。 |
| `pnpm --filter @vben/web-antd build` | 未通过 | 正式目录未安装依赖，`vite` 不存在。是清理前已存在的环境缺项。 |
| `pnpm --filter @vben/web-antd typecheck` | 未通过 | 同因缺依赖，`vue-tsc` 不存在。 |
| `pnpm test:unit` | 未通过 | 同因缺依赖，`vitest` 不存在。没有把未运行的断言标为通过。 |
| `python -m pip check` | 未通过 | 全局环境有 6 项其他已安装工具包版本冲突，涉及 mcp、spotdl、sse-starlette、torchvision；项目 requirements 未声明这些工具，MySQL与Pillow实际导入和上述服务验证成功。没有改动全局 Python 环境。 |
| 完整 `python server.py` 初始化启动 | 未执行 | 真正 main 先运行 `init_db()`，可能写 schema/默认数据；报告阶段用已有 HTTP handler 与现有库验证，跳过数据库初始化。不能据此声称新空库启动已验证。 |
| Docker、Nginx 和线上部署 | 未执行实测 | 本机没有 docker 命令；仅静态检查 Docker、Nginx 与部署路径，没有部署、重启或修改线上。 |
| 浏览器视觉、后台登录与写 API | 未执行 | 没有验证动画、图片最终呈现、鉴权后的管理页、上传、删除、写操作或 MCP 全部工具。报告阶段不为清理扫描创建客户记录/会话。 |

项目依赖实际可导入：PyMySQL 1.2.3、Pillow 12.2.0、cryptography 46.0.5。`validation.json` 保存 HTTP 检查清单和路径检查结果，没有响应内容与客户数据。

## 第一阶段执行与后续验证顺序

当前仅建议，尚未删除：

1. 只采用 A 和 `candidates.json` 白名单；删除前重新核对 SHA-256、文件大小、目录是否仍为空以及路径是否仍位于项目根内。若文件已变、出现新文件、变成链接或被工具占用，则跳过并标为人工确认。
2. 缓存/临时输出只删白名单内文件，空目录只在确实为空时移除。**不扩大到 `tmp/`、`admin-vben/`、`uploads/` 或 `output/` 整目录。保护任意层级 `.git`。**
3. 重新执行发布校验、Python/JS 语法、模块/预加载路径、公开 HTTP/API 基线与只读资源完整性检查，与本次结果比较。
4. 完整前端验证前，先补齐正式开发环境。用锁文件完成依赖安装和构建、类型检查、测试后，再评估 B 的依赖目录和中转产物。
5. Docker 与服务器 Nginx 验证需在具备相应运行环境时执行；不因本机缺工具就报告通过。前端视觉、后台登录、上传与写 API 应在有隔离测试数据的环境验证。

## 当前目录与预期精简结构

目前未清理，目录仍为：

```text
tlhdd/
├── *.py                         # Python 后端，共 21 个模块
├── *.html                       # 官网，共 13 页
├── favicon.* / apple-touch-icon.png / 站点验证.txt
├── requirements.txt / schema.mysql.sql / .gitignore
├── README.md / 网站完整使用文档.md / 启动网站.bat
├── admin/                       # 正式后台产物，保留
├── admin-vben/                  # 正式维护源码、workspace、CI、工具，保留
├── admin-vben-build/             # 构建中转，人工确认
├── assets/                      # 官网资源、默认媒体、品牌许可，保留
├── data/                        # 汇率缓存、导出数据，保留/人工确认
├── deploy/                      # 部署脚本、环境模板、Nginx、runbook，保留
├── scripts/                     # 4 个运维脚本，保留
│   └── __pycache__/             # A
├── uploads/                     # 用户文件，全部保留
├── logs/                        # 日志保留期需确认
├── output/                      # 历史发布包、截图、辅助脚本，人工确认
├── tmp/
│   ├── backups/                 # 空目录，A
│   └── vue-vben-admin/          # 有 Git、未提交修改、环境与依赖，保留
├── .playwright-cli/             # A
├── __pycache__/                 # A
└── docs/cleanup-audit-2026-10-05/ # 本次报告与清单
```

执行 A 后仅移除三个缓存/临时输出目录和两个空目录；其余结构保持。第二阶段“只留一个开发目录、移出历史产物”的目标要先完成依赖环境和归档确认，当前没有生成一个已清理完成的虚假目录树。

## 交付清单

- `REPORT.md`：本报告，含 A/B/C/D、风险、基线与后续顺序。
- `candidates.json`：A 的精确路径、哈希、大小和目录名单，尚未执行。
- `findings.json`：目录统计、引用结果、源码/产物差异和分析边界；没有密钥/客户记录。
- `duplicates.json`：2,178 组 SHA-256 相同文件路径；不是删除白名单。
- `validation.json`：320 项 HTTP 结果与 1,786 项模块/预加载路径检查的汇总。

**最终状态：报告已完成；删除 0 文件、0 文件夹；释放 0 字节。第一阶段安全候选 175 文件、5 目录、约 3.18 MiB；其余保留或待人工确认。**
