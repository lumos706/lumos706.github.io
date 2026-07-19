# Lumos Blog visual direction

The homepage concept is intentionally editorial rather than template-like: warm paper, near-black ink, and a sharp citron accent express the “Lumos” idea without depending on generated artwork. The layout alternates between open whitespace, one strong poster frame, list-based article discovery, and a dark topic band.

## Design system

- Background: `#f5f2e9` warm paper; intentional, not a white substitute.
- Text: `#171714`; secondary text `#6d695f`.
- Accent: `#ddff57` citron light; supporting violet `#6657d8`.
- Display type: Georgia plus Chinese Song-style system fallbacks.
- UI type: native sans-serif stack for dependable rendering in China and abroad.
- Geometry: square editorial frames, thin rules, very limited rounding.
- Motion: restrained reveal-on-scroll and row/arrow movement; all disabled for reduced motion.

## Visible-copy lock for the first viewport

- Brand: `LUMOS`
- Navigation: `首页`, `文章`, `归档`, `关于`, `夜间模式`
- Heading: `在代码与生活之间，留下一束光。`
- Supporting copy: `这里记录技术实践、设计观察，也收藏那些让日常变得清晰的微小发现。慢一点写，诚实一点想。`
- Actions: `开始阅读`, `关于这个博客`
- Poster text: `FIELD NOTES`, `NO. 001`, `lumos`, `MAKE THOUGHTS VISIBLE`, `2026`

This code-native concept is the fallback design reference because the built-in Image Gen tool was unavailable in the session. It remains a durable project artifact rather than a production dependency.

## Visual QA artifacts

- `lumos-blog-concept.png`: accepted 1280 × 720 first-viewport reference.
- `lumos-blog-implementation.png`: final 1280 × 720 browser render after implementation.

The two images intentionally remain in the repository as the design/fidelity record. Temporary responsive and article-page screenshots are not retained.
