# Lumos Blog

一个面向 GitHub Pages 的个人博客，使用 Astro 静态生成。视觉方向来自 Halo 主题生态里成熟的内容层级与主题系统，但没有直接使用 Halo 运行时：Halo 需要 Java 服务和数据库，而 GitHub Pages 只能托管静态文件。

线上地址：<https://lumos706.github.io>

## 技术栈

- Astro 7：静态页面与 Markdown 内容集合
- 原生 CSS / JavaScript：响应式布局、深浅主题、移动导航、阅读进度与复制链接
- GitHub Actions：推送到 `main` 后自动构建并部署 Pages
- VS Code：仓库内置推荐扩展、格式化设置与任务
- Miniconda Python 3.11：用于可选的静态产物预览；Astro 本身由 Node.js 构建

## 本地运行

要求 Node.js 22.12 或更高版本。

```powershell
npm install
npm run dev
```

生产检查与构建：

```powershell
npm run build
npm run preview
```

如果希望用 Miniconda 验证纯静态产物：

```powershell
conda env create -f environment.yml
npm run build
conda run -n lumos-blog python -m http.server 4173 --directory dist
```

## 在 VS Code 中写文章

1. 用 VS Code 打开仓库目录。
2. 安装工作区推荐的 Astro 与 Markdown 扩展。
3. 在 `src/content/blog/` 新建 `.md` 文件。
4. 复制现有文章的 frontmatter，填写标题、摘要、日期、分类、标签、阅读时间和封面配色。
5. 运行 `npm run dev` 实时预览。
6. 按 `Ctrl + Shift + B` 执行提交前的生产构建。

文章封面 `cover` 支持 `light`、`violet`、`ink`、`paper` 四种视觉变体。将 `draft` 设为 `true` 可让文章暂不进入构建结果。

## 目录

```text
.github/workflows/deploy.yml  GitHub Pages 自动部署
.vscode/                      VS Code 工作区设置与任务
design/                       视觉基准与设计说明
public/                       图标、社交分享图和公开静态文件
src/components/               可复用界面组件
src/content/blog/             Markdown 文章
src/layouts/                  全站与文章布局
src/pages/                    首页、文章、归档、关于、RSS、404
src/styles/                   全局设计变量和基础样式
```

## 可拆卸的旅游攻略系统

旅游模块位于 `/travel/`，面向 4 位成人、2 间双床房的青海甘肃行程。它提供 3 / 4 / 7 日路线、¥2,500 / ¥3,000 / ¥3,500 三档落地预算，以及“自驾（租车）/ 公共交通”两种当地出游方式；路线、逐日安排、交通费用与景点到达方式会联动切换。

所有公开攻略、预约与当地交通线索都由官方 [`Jesseovo/last30days-skill-cn`](https://github.com/Jesseovo/last30days-skill-cn) 采集；机票和酒店报价由官方 [`alibaba-flyai/flyai-skill`](https://github.com/alibaba-flyai/flyai-skill) 提供。仓库脚本只负责编排 skill、过滤无关结果和生成 Astro 所需 JSON，不实现站点爬虫或飞猪接口。

### 本地安装（Miniconda）

```powershell
npx --yes skills add Jesseovo/last30days-skill-cn -g -y
npx --yes skills add alibaba-flyai/flyai-skill -g -y
conda env create -f scripts/travel/environment.yml
conda run -n lumos-travel python -m playwright install chromium
conda run -n lumos-travel python "$env:USERPROFILE\.agents\skills\last30days-cn\scripts\last30days.py" --diagnose
```

`jieba` 和 Playwright 均按仓库配置指南安装。没有 API Key 时，Playwright 仍可尝试微博、小红书、抖音、B 站和知乎；平台可能要求登录或验证码。小红书在 skill v2.1 之后不再使用 ScrapeCreators 端点，因此 `SCRAPECREATORS_API_KEY` 只作为官方配置兼容项保留，不应被当作小红书采集成功的前提。

无 API 刷新：

```powershell
conda run -n lumos-travel python scripts/travel/update_travel_data.py --pause 10
```

允许读取官方用户级配置 `~/.config/last30days-cn/.env` 中的可选凭据：

```powershell
conda run -n lumos-travel python scripts/travel/update_travel_data.py --allow-credentials --pause 10
conda run -n lumos-travel python scripts/travel/update_transport_guides.py --allow-credentials --pause 8
conda run -n lumos-travel python scripts/travel/update_reservation_rules.py --allow-credentials --quick --pause 8
node scripts/travel/update_flyai_prices.mjs
```

凭据、Cookie 和浏览器登录态不得提交到仓库。GitHub Actions 使用仓库 Secrets：`ZHIHU_COOKIE`、`SCRAPECREATORS_API_KEY`、`LAST30DAYS_XHS_COOKIES_B64` 和 `FLYAI_API_KEY`。缺少攻略平台凭据时，采集脚本仍会回退到无 API 浏览器与公开搜索路径；FlyAI 查询失败时保留上一份有效机酒报价并标记状态。

`.github/workflows/travel-data.yml` 将所有旅行数据统一放在每日晚间刷新：首选 `13:17 UTC`（北京时间 21:17），并在 22:17、23:17 设置两个受守卫的补跑检查。只要当晚已经成功生成过快照，后续检查会在安装依赖和采集数据前直接跳过；若前一次定时事件被 GitHub 延迟、丢弃或执行失败，下一检查点才会运行完整任务。完整任务会安装官方 skill、FlyAI skill、Miniconda、`jieba` 与 Playwright Chromium，一次性更新攻略、餐馆、当地交通、出发准备、景区预约、机票和酒店，通过生产构建后再提交数据并触发 Pages 部署。预约证据不足时保留上一份有效规则；交通证据不足时保留人工核对过的稳妥基线，不根据单条帖子擅自改写公交线路号。

正式刷新前，工作流会先通过官方 skill 对小红书和知乎执行最多两次低频真实查询，并检查小红书核心登录 Cookie 的本地到期字段。主采集路径降级、Cookie 缺失或临近 7 天到期时，仓库会自动创建名为“旅游数据登录态需要更新”的 Issue 并指派给仓库所有者；定时检查仍未恢复时每天提醒一次，恢复后自动关闭。预检异常不会阻断当晚刷新，脚本会继续使用公开搜索兜底并保留上一轮有效内容。

Cookie 没有统一、可保证的有效期：小红书 Cookie 文件包含浏览器声明的到期时间，但平台仍可能因退出登录、密码变更、验证码或风控提前作废；从浏览器复制的知乎 `Cookie` 请求头通常不包含 `Expires` / `Max-Age`，因此无法仅靠字符串推算到期日，必须以真实查询结果为准。可以在 Actions 手动运行 `Refresh travel data` 随时复检。更新凭据时只修改 GitHub Secrets 和本机 `~/.config/last30days-cn/.env`，不得把值写入 Issue、聊天或仓库文件。

需要排查单项时，可在 Actions 手动运行任务并填写 `only`，例如 `tickets` 或 `dunhuang,zhangye`；定时任务不填写该参数，会完整刷新全部类别。

### 移除模块

删除以下内容即可完整卸载，不影响博客文章：

- `src/pages/travel/`
- `src/components/travel/`
- `src/data/travel/`
- `src/styles/travel.css`
- `scripts/travel/`
- `.github/workflows/travel-data.yml`
- `src/components/Header.astro` 中的“旅行”导航项

## 发布

仓库名必须是 `lumos706.github.io`，默认分支为 `main`。首次推送后，工作流会使用 GitHub Pages 的官方 artifact 部署方式。若 Pages 尚未启用，请在仓库 `Settings → Pages` 中把 Source 设为 **GitHub Actions**。

## 从 Halo 迁移或升级

当前方案优先满足 `lumos706.github.io` 的纯静态部署约束。如果未来需要网页管理后台、多人编辑、动态评论审核或 Halo 插件，可以把 Halo 部署到云服务器，再迁移 Markdown 内容并切换域名；本仓库中的文章不会被专有数据库格式锁定。
