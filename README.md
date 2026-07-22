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

旅游模块位于 `/travel/`，面向 4 位成人、2 间双床房的青海甘肃行程。它提供 3 / 4 / 7 日路线、¥2,500 / ¥3,000 / ¥3,500 三档落地预算、具体景点避坑、沿途店家证据和每日公开价格快照。

所有公开网页数据都由官方 [`Jesseovo/last30days-skill-cn`](https://github.com/Jesseovo/last30days-skill-cn) 采集；`scripts/travel/update_travel_data.py` 只负责编排 skill、过滤无关结果和生成 Astro 所需 JSON，不实现站点爬虫。

### 本地安装（Miniconda）

```powershell
npx --yes skills add Jesseovo/last30days-skill-cn -g -y
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
```

凭据、Cookie 和浏览器登录态不得提交到仓库。GitHub Actions 使用仓库 Secrets：`ZHIHU_COOKIE`、`SCRAPECREATORS_API_KEY` 和 `LAST30DAYS_XHS_COOKIES_B64`。缺少这些 Secrets 时，采集脚本仍会回退到无 API 浏览器与公开搜索路径。

`.github/workflows/travel-data.yml` 每天 `13:00 UTC`（北京时间 21:00）自动安装官方 skill、Miniconda、`jieba` 与 Playwright Chromium，刷新 `src/data/travel/snapshot.json`，通过生产构建后再提交数据。采集成功完成后，Pages 工作流通过 `workflow_run` 重新构建并上线最新快照。价格样本不足时页面显示“暂无可靠公开报价”，不会补造数字。

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
