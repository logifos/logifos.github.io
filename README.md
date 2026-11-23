# Logifos project status site

Logifos is unreleased. The Rust engine and Ruby, TypeScript and Python runtimes
do not provide working rendering. This Astro site describes the planned
architecture and API, development setup, runtime status and migration policy.
It includes no demo, external assets or deployment workflow.

## Local build and checks

From this development checkout, use Node.js 22.23.4 or later and npm 9.6.5 or
later. CI uses Node.js 24. Python 3.9 or later runs the offline contract-link
check using only the standard library.

```sh
npm ci
npm run build
npm run check:site
npm run check:contracts
npm run test:contracts
npm run preview -- --host 127.0.0.1
```

Open the preview URL printed by Astro. The navigation links to architecture,
API, install, status and migration pages. Stop the server with Ctrl-C. To edit
with live reload, use `npm run dev`.

The committed `package-lock.json` fixes the dependency tree. The PR build check
runs the same install, build, built-page and contract-link checks. It does not deploy.
`dist/`, `node_modules/`, and `.astro/` are generated and ignored by Git.

The built-site check reads all six HTML pages and verifies scaffold and release
notices, all four runtimes, navigation, local files and fragments, and the MIT
notice. It also rejects registry installation commands on the install page.
External links are checked for HTTPS syntax; no check makes network calls.

## Contract references

The wire contract belongs to `logifos-rs`, not this site. The metadata in
`src/data/contract.json` records an immutable unreleased revision, target wire
versions and reference paths. It is not a release ledger or a schema copy.
The API and status pages generate their contract links from that metadata.
Formula and MathML syntax payload pins are still unresolved.

`npm run check:contracts` checks built links, version labels and the target
negotiation example for consistency. It rejects mutable revisions and schema
copies under source/public/contract paths. To inspect the actual pinned files
in an existing core checkout, also run:

```sh
npm run check:contracts -- --core-checkout /path/to/logifos-rs
```

That mode uses read-only `git show` at the recorded revision, checks request and
response version constants, resolves internal schema references and confirms the
documented unresolved external pins. It never fetches, checks out or modifies
the supplied repository. The pinned commit must already exist locally.

`npm run test:contracts` exercises rejection of mutable revisions and links,
unqualified release labels, missing references, stale versions/examples and
absent build output. It uses temporary copies of the built pages, not schemas.

Neither mode verifies remote link availability, engine execution, installed
runtime packages or release support. No release has been qualified; a future
release-backed documentation update must use its pinned core compatibility data.

## Contents

- `src/pages/`: home, architecture, API, install, status, migration and the MIT notice.
- `src/components/`: shared unreleased notice and pinned contract references.
- `src/data/`: contract reference metadata and development runtime descriptions.
- `src/layouts/Site.astro`: shared document, navigation, and footer.
- `src/styles/site.css`: local styles using system fonts.
- `tools/check-built-site.mjs`: focused built-output assertions.
- `tools/check-contract-links.py`: offline contract/version/schema-reference checks.
- `.github/workflows/check.yml`: PR install and build check.

## License

MIT, copyright 2026 Ribose Inc.; see [LICENSE.txt](LICENSE.txt).
