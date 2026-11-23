import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { parse } from 'parse5';

const root = new URL('../dist/', import.meta.url);
const origin = 'https://logifos.github.io';
const text = (node) => node.nodeName === '#text'
  ? node.value
  : (node.childNodes ?? []).map(text).join(' ');
const visible = (node) => text(node).replace(/\s+/g, ' ').trim();
const attributes = (node) => Object.fromEntries((node.attrs ?? []).map(({ name, value }) => [name, value]));

function descendants(node) {
  return [node, ...(node.childNodes ?? []).flatMap(descendants)];
}

const pages = new Map();
const expectedPages = ['api.html', 'architecture.html', 'index.html', 'install.html', 'migration.html', 'status.html'];
const filenames = (await readdir(root)).filter((name) => name.endsWith('.html')).sort();
assert.deepEqual(filenames, expectedPages, 'expected documentation pages');
for (const filename of filenames) {
  const errors = [];
  const document = parse(await readFile(new URL(filename, root), 'utf8'), {
    onParseError: (error) => errors.push(error.code),
  });
  assert.deepEqual(errors, [], `${filename}: HTML parse errors`);
  const nodes = descendants(document);
  const ids = nodes.flatMap((node) => attributes(node).id ? [attributes(node).id] : []);
  assert.equal(new Set(ids).size, ids.length, `${filename}: duplicate IDs`);
  for (const tag of ['h1', 'main', 'title']) {
    assert.equal(nodes.filter((node) => node.tagName === tag).length, 1, `${filename}: expected one ${tag}`);
  }
  const notice = nodes.find((node) => attributes(node).id === 'bootstrap-notice');
  assert.ok(notice, `${filename}: missing status notice`);
  assert.match(visible(notice), /Scaffold stage\./, `${filename}: missing scaffold limitation`);
  assert.match(visible(notice), /Rendering is unavailable/, `${filename}: missing rendering limitation`);
  assert.match(visible(notice), /Nothing is released/, `${filename}: missing release limitation`);
  const nav = nodes.find((node) => node.tagName === 'nav');
  for (const target of expectedPages.filter((name) => name !== 'index.html')) {
    assert.ok(descendants(nav).some((node) => attributes(node).href === `/${target}`), `${filename}: missing navigation to ${target}`);
  }
  const footer = nodes.find((node) => node.tagName === 'footer');
  assert.ok(footer, `${filename}: missing footer`);
  assert.match(visible(footer), /© 2026 Ribose Inc\./);
  assert.ok(descendants(footer).some((node) => node.tagName === 'a'
    && attributes(node).href === '/LICENSE.txt' && visible(node) === 'MIT license'), `${filename}: MIT link`);
  pages.set(filename, { nodes, ids });
}

for (const filename of ['index.html', 'status.html']) {
  const components = pages.get(filename).nodes.filter((node) => attributes(node)['data-component']);
  assert.deepEqual(components.map((node) => attributes(node)['data-component']).sort(), ['python', 'ruby', 'rust', 'typescript']);
  for (const node of components) {
    assert.equal(attributes(node)['data-status'], 'scaffold');
    assert.match(visible(node), /Scaffold/);
    assert.match(visible(node), /rendering is unavailable/);
  }
}
assert.match(visible({ childNodes: pages.get('architecture.html').nodes.filter((node) => node.tagName === 'main') }), /No phase completion is claimed/);
for (const [filename, marker] of [
  ['status.html', 'runtime-matrix'], ['api.html', 'operations'],
  ['install.html', 'runtimes'], ['migration.html', 'compatibility'],
]) {
  assert.ok(pages.get(filename).ids.includes(marker), `${filename}: missing ${marker}`);
}
const installText = visible({ childNodes: pages.get('install.html').nodes });
assert.match(installText, /development checkouts only/);
assert.match(installText, /npm ci/);
assert.match(installText, /npm run check:contracts/);
assert.doesNotMatch(installText, /(?:gem|pip|npm) install|cargo add/, 'registry install instructions are premature');
const matrix = pages.get('status.html').nodes.find((node) => node.tagName === 'table');
for (const label of ['Released renderer', 'Development requirement', 'Planned transport', 'Planned output']) {
  assert.ok(descendants(matrix).some((node) => node.tagName === 'th' && visible(node) === label), `runtime matrix: missing ${label}`);
}

const license = await readFile(new URL('../LICENSE.txt', import.meta.url), 'utf8');
assert.match(license, /^MIT License\s+Copyright \(c\) 2026 Ribose Inc\./);
assert.equal(await readFile(new URL('LICENSE.txt', root), 'utf8'), license, 'built MIT notice differs from root notice');

let localLinks = 0;
for (const [filename, page] of pages) {
  for (const node of page.nodes) {
    const attrs = attributes(node);
    for (const href of [attrs.href, attrs.src].filter((value) => value !== undefined)) {
      assert.ok(href, `${filename}: empty URL`);
      const url = new URL(href, `${origin}/${filename}`);
      if (url.origin !== origin) {
        assert.ok(node.tagName === 'a' && url.protocol === 'https:' && !url.username && !url.password, `${filename}: invalid external link`);
        continue;
      }
      const path = decodeURIComponent(url.pathname).slice(1) || 'index.html';
      const target = new URL(path, root);
      assert.ok(target.href.startsWith(root.href), `${filename}: local URL escapes dist`);
      assert.ok((await stat(fileURLToPath(target))).isFile(), `${filename}: missing ${href}`);
      if (url.hash) {
        assert.ok(pages.get(path)?.ids.includes(decodeURIComponent(url.hash.slice(1))), `${filename}: missing fragment ${href}`);
      }
      localLinks += 1;
    }
  }
}
console.log(`PASS: ${pages.size} built pages, 4 scaffold runtimes on home/status, ${localLinks} local links, matching MIT notice`);
