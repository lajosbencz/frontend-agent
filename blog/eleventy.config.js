// Eleventy config. Output -> dist/ (picked up by the Pages workflow and copied to /blog).
// pathPrefix makes every `| url` link resolve under the GitHub Pages project path.
export default function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy({ css: 'css' })
  eleventyConfig.addPassthroughCopy({ assets: 'assets' }) // images referenced from posts
  eleventyConfig.ignores.add('README.md')

  eleventyConfig.addFilter('isodate', (d) => new Date(d).toISOString().slice(0, 10))

  // Posts collection by glob (frees front-matter `tags` for dev.to). Drafts excluded unless DRAFTS=1.
  // Sort by `postDate` (a custom key): dev.to reads front-matter `date` as published_at and rejects
  // past values, so the display date lives under a name dev.to ignores.
  const showDrafts = process.env.DRAFTS === '1'
  eleventyConfig.addCollection('posts', (api) =>
    api.getFilteredByGlob('content/*.md')
      .filter((p) => showDrafts || !p.data.draft)
      .sort((a, b) => new Date(b.data.postDate) - new Date(a.data.postDate)))

  return {
    dir: { input: '.', includes: '_includes', data: '_data', output: 'dist' },
    pathPrefix: '/frontend-agent/blog/',
    markdownTemplateEngine: 'njk',
    htmlTemplateEngine: 'njk',
  }
}
