// Chat-bubble Markdown rendering via `marked` (inline-only - no block wrapping, fits a compact
// bubble). marked passes raw HTML through verbatim by default, so escaping `<` first neutralizes
// that (no literal `<` left for its tokenizer to recognize a tag); marked's own entity-aware text
// escaper already treats `&lt;` as a pre-existing entity and won't double-escape the `&`. The href
// scheme filter afterward is defense in depth against anything smuggled through as a link target.

import { marked } from 'marked'

marked.use({ breaks: true })

const SAFE_HREF = /^(https?:|mailto:)/i

export function renderMarkdown(text: string): string {
  const html = marked.parseInline(text.replace(/</g, '&lt;')) as string
  return html.replace(/href="([^"]*)"/gi, (m, href) => (SAFE_HREF.test(href) ? `href="${href}" target="_blank" rel="noopener noreferrer"` : 'href="#"'))
}
