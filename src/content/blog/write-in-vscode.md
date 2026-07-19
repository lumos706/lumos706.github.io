---
title: 如何在 VS Code 里写下一篇新文章
description: 从创建 Markdown 文件到本地预览、检查和发布，一份适合这个博客的最短写作流程。
pubDate: 2026-07-17
category: 指南
tags: [VS Code, Markdown, 写作流程]
readingTime: 5
cover: paper
---

这个博客不依赖网页后台。文章就是仓库里的 Markdown 文件，因此可以直接在 VS Code 中完成写作、预览和版本管理。

## 准备开发环境

第一次打开项目后，在 VS Code 的终端中运行：

```powershell
npm install
npm run dev
```

浏览器访问终端显示的本地地址。开发服务器会监听文件变化，保存文章后页面会自动更新。

项目也提供了 VS Code 任务。按 `Ctrl + Shift + B` 可以执行生产构建；命令面板里运行 `Tasks: Run Task`，则可以选择启动开发服务器。

## 创建文章文件

在 `src/content/blog/` 中新建一个以英文短横线命名的文件，例如：

```text
src/content/blog/my-new-note.md
```

文件开头需要一段 frontmatter：

```yaml
---
title: 我的新文章
description: 用一两句话说明文章解决什么问题。
pubDate: 2026-07-20
category: 技术
tags: [Astro, 笔记]
readingTime: 6
cover: light
---
```

`cover` 可以选择 `light`、`violet`、`ink` 或 `paper`。它只决定文章封面的视觉配色，不会改变正文内容。

## 写作时保持结构清楚

正文从普通段落开始，一级标题已经由文章标题占用，所以主要章节使用二级标题：

```markdown
## 问题是什么

先给出上下文，再解释问题。

## 如何解决

写清步骤、代码和取舍。
```

代码块请标注语言，这样构建时能获得正确的语法高亮。图片放在 `public/images/` 后，可以使用 `/images/example.webp` 这样的绝对路径引用。

## 发布前检查

运行下面的命令：

```powershell
npm run build
```

它会先检查 Astro 与 TypeScript，再生成生产页面。确认没有错误后提交并推送到 `main` 分支，GitHub Actions 会自动部署。

建议每次发布前至少检查：

- 标题和摘要是否准确；
- 手机宽度下是否有横向溢出；
- 文中的链接与代码是否可用；
- 日期、分类和阅读时间是否正确；
- 草稿是否误设为可发布状态。

把写作流程保持简单，更新才更容易成为一件长期做下去的事。
