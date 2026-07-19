import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import { sortPosts } from '@/lib/blog';

export async function GET(context: { site: URL }) {
  const posts = sortPosts(await getCollection('blog', ({ data }) => !data.draft));
  return rss({
    title: 'Lumos',
    description: '在代码与生活之间，留下一束光。',
    site: context.site,
    items: posts.map((post) => ({
      title: post.data.title,
      description: post.data.description,
      pubDate: post.data.pubDate,
      link: `/posts/${post.id}/`,
      categories: [post.data.category, ...post.data.tags],
    })),
    customData: '<language>zh-CN</language>',
  });
}
