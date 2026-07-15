// Inline-only chat-bubble Markdown via `marked`. Escape `<` first so marked's default raw-HTML
// passthrough has no tag to recognize (its entity-aware escaper won't double-escape `&lt;`); the
// href scheme filter afterward is defense-in-depth against smuggled link targets.

import { marked } from 'marked'

marked.use({ breaks: true })

const SAFE_HREF = /^(https?:|mailto:)/i

export function renderMarkdown(text: string): string {
  const html = marked.parseInline(text.replace(/</g, '&lt;')) as string
  return html.replace(/href="([^"]*)"/gi, (m, href) => (SAFE_HREF.test(href) ? `href="${href}" target="_blank" rel="noopener noreferrer"` : 'href="#"'))
}
