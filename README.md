# Logifos project status site

Logifos is at the scaffold stage. The Rust engine and Ruby, TypeScript, and
Python runtimes do not provide working rendering. This Astro site reports that
limit and describes the planned architecture. It includes no demo, external
assets, or deployment workflow.

## Local build and checks

Use Node.js 22.23.4 or later and npm 9.6.5 or later. CI uses Node.js 24.

```sh
npm ci
npm run build
npm run check:site
npm run preview -- --host 127.0.0.1
```

Open the preview URL printed by Astro, then `/architecture.html`. Stop the
server with Ctrl-C. To edit with live reload, use `npm run dev`.

The committed `package-lock.json` fixes the dependency tree. The PR build check
runs the same install, build, and built-page assertions. It does not deploy.
`dist/`, `node_modules/`, and `.astro/` are generated and ignored by Git.

The focused check reads the generated HTML and verifies the scaffold notices,
all four runtime rows, planned architecture, local files and fragment links,
and the MIT notice. External source links are checked for HTTPS syntax only;
the check makes no network calls. This validates the status site, not rendering
capabilities or phase completion.

## Contents

- `src/pages/`: status, architecture, and the static MIT notice endpoint.
- `src/layouts/Site.astro`: shared document, navigation, and footer.
- `src/styles/site.css`: local styles using system fonts.
- `tools/check-built-site.mjs`: focused built-output assertions.
- `.github/workflows/check.yml`: PR install and build check.

## License

MIT, copyright 2026 Ribose Inc.; see [LICENSE.txt](LICENSE.txt).
