// Build-time RAG indexes for the static (GitHub Pages) demo. Parses each domain's source content
// into a flat JSON index the browser retrieves against client-side - no server, no DB. A site that
// brings its own vector DB points RAG_ENDPOINT at it instead (see ragClient.ts); this index is only
// the zero-infra default. Run before `nuxi generate`.

import { readFileSync, writeFileSync, readdirSync, mkdirSync } from 'node:fs'
import { join, dirname, basename } from 'node:path'
import { fileURLToPath } from 'node:url'
import matter from 'gray-matter'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const CONTENT = join(ROOT, 'content')
const RAG_DIR = join(ROOT, 'public', 'rag')

function slugify(s) {
  return s
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

// Strip markdown to plain text for retrieval/snippets.
function strip(md) {
  return md
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[#>*_`|-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function loadDir(sub) {
  const dir = join(CONTENT, sub)
  return readdirSync(dir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => {
      const { data, content } = matter(readFileSync(join(dir, f), 'utf8'))
      return { file: basename(f, '.md'), data, body: content }
    })
}

function writeIndex(name, catalog, knowledge) {
  const out = join(RAG_DIR, name)
  mkdirSync(dirname(out), { recursive: true })
  writeFileSync(out, JSON.stringify({ catalog, knowledge }))
  console.log(`rag-index: ${catalog.length} catalog + ${knowledge.length} knowledge -> ${out}`)
}

// BrewCraft: markdown collections (products/docs).
const brewcraftCatalog = loadDir('products').map((p) => ({
  id: p.data.slug || p.file,
  title: p.data.title || p.file,
  group: p.data.category || 'products',
  price: typeof p.data.price === 'number' ? p.data.price : null,
  in_stock: p.data.inStock !== false,
  summary: p.data.summary || strip(p.body).slice(0, 160),
  text: `${p.data.summary || ''} ${strip(p.body)}`.trim(),
}))
const brewcraftKnowledge = loadDir('docs').map((d) => {
  const body = strip(d.body)
  return { id: d.file, title: d.data.title || d.file, text: `${d.data.description || ''} ${body}`.trim() }
})
writeIndex('index.json', brewcraftCatalog, brewcraftKnowledge)

// Emporium: flat JSON product list, plus a markdown news collection as its knowledge base.
const emporiumRaw = JSON.parse(readFileSync(join(ROOT, 'app', 'data', 'emporium-products.json'), 'utf8'))
const emporiumCatalog = emporiumRaw.map((p) => ({
  id: slugify(p.name),
  title: p.name,
  group: p.category,
  price: p.price,
  in_stock: p.inStock !== false,
  summary: p.description,
  text: `${p.name} ${p.description}`,
}))
const emporiumKnowledge = loadDir('news').map((n) => {
  const body = strip(n.body)
  return { id: n.data.slug || n.file, title: n.data.title || n.file, text: `${n.data.description || ''} ${body}`.trim() }
})
writeIndex('emporium-index.json', emporiumCatalog, emporiumKnowledge)

// Vendor: flat JSON grocery list, plus a markdown knowledge base (haggling rules, recipes).
const vendorRaw = JSON.parse(readFileSync(join(ROOT, 'app', 'data', 'vendor-groceries.json'), 'utf8'))
const vendorCatalog = vendorRaw.map((g) => ({
  id: g.id,
  title: g.title,
  group: `shelf-${g.shelf}`,
  price: g.price,
  in_stock: true,
  summary: g.description,
  text: `${g.title} ${g.description}`,
}))
const vendorKnowledge = loadDir('vendor-kb').map((k) => {
  const body = strip(k.body)
  return { id: k.file, title: k.data.title || k.file, text: `${k.data.description || ''} ${body}`.trim() }
})
writeIndex('vendor-index.json', vendorCatalog, vendorKnowledge)
