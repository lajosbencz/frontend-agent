# blog

Standalone [Eleventy](https://www.11ty.dev/) blog - `content/*.md` -> `dist/`. Deployed to GitHub Pages under **`/frontend-agent/blog`** by the `Deploy demo to GitHub Pages` workflow (it builds this and copies `dist/` into the Pages artifact at `/blog`).
Deliberately separate from `demo/` - its own package, not an npm workspace member.

## Build / preview

```bash
cd blog
npm install
npm run build            # -> dist/  (drafts excluded)
npm run serve            # live preview at http://localhost:8080/frontend-agent/blog/
npm run drafts           # same, but includes draft: true posts
```

Note: Eleventy overwrites but doesn't purge `dist/`; `rm -rf dist` before a build if you renamed/removed a post locally.
CI always builds from a clean checkout, so deploys are never stale.
