// Directory data for all posts in content/: shared layout + clean permalink. Drafts get no output file
// (permalink:false) unless DRAFTS=1; the `posts` collection (eleventy.config.js) also skips them.
export default {
  layout: 'base.njk',
  eleventyComputed: {
    permalink: (data) =>
      data.draft && process.env.DRAFTS !== '1' ? false : `/${data.slug || data.page.fileSlug}/`,
  },
}
