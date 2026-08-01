import { defineConfig } from 'astro/config';
import { satteri } from '@astrojs/markdown-satteri';
import sitemap from '@astrojs/sitemap';
import katex from 'katex';

function renderMath(source, displayMode) {
  return katex.renderToString(source, {
    displayMode,
    output: 'htmlAndMathml',
    throwOnError: true,
  });
}

const katexMathPlugin = {
  name: 'katex-math',
  math(node, context) {
    context.replaceNode(node, { type: 'html', value: renderMath(node.value, true) });
  },
  inlineMath(node, context) {
    context.replaceNode(node, { type: 'html', value: renderMath(node.value, false) });
  },
};

export default defineConfig({
  site: 'https://lumos706.github.io',
  output: 'static',
  integrations: [sitemap()],
  markdown: {
    processor: satteri({
      features: { math: true },
      mdastPlugins: [katexMathPlugin],
    }),
    shikiConfig: {
      theme: 'github-dark',
      wrap: true,
    },
  },
});
