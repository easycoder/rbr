// docs-reader-check.js — end-to-end check for the documentation reader at /docs.
//
//   node tests/docs-reader-check.js
//
// The reader is two halves that talk through the DOM, and its pages come from a
// public repository, so nothing here can be checked by reading the source. This
// drives the real page in a DOM with the real runtime and the real documentation:
// it builds the page list from docs/README.md, clicks links the markdown renderer
// produced, works the toolbar, opens a page by address, and follows a link that
// climbs out of the documentation tree.
//
// It needs jsdom (a devDependency) and network access to raw.githubusercontent.com
// — the reader fetches its Markdown from there at runtime, which is the whole
// point of it. A failure to reach the repository shows up as a failed check
// rather than as a silent pass.
//
// **It tests the published documentation, not the working tree.** The reader reads
// `main`, so a document written here is invisible to this check — and to the site —
// until it is committed and pushed. That is why the page list is checked for its
// order and for a floor rather than for an exact count.
//
// What it does NOT check is anything visual: fonts, spacing, how a table looks on
// a phone. That needs a real browser, which is what the Playwright specs in this
// directory are for.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { JSDOM, VirtualConsole } = require('jsdom');

const ROOT = path.join(__dirname, '..');
const PAGE = 'docs-reader/index.html';
const TYPES = {
  '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json',
  '.css': 'text/css', '.ico': 'image/x-icon', '.png': 'image/png', '.svg': 'image/svg+xml'
};

let pass = 0;
let fail = 0;
const failures = [];

function check(name, ok, detail) {
  if (ok) {
    pass++;
    console.log('  ok   ' + name);
  } else {
    fail++;
    failures.push(name);
    console.log('  FAIL ' + name + (detail === undefined ? '' : '   -> ' + detail));
  }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// A static server for the repository, so the page is loaded over HTTP as it is
// in production (a file:// origin has no fetch and no history). A directory is
// served as its index.html, as Apache would.
function serve() {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      const rel = decodeURIComponent(req.url.split('?')[0]).split('#')[0].replace(/^\/+/, '');
      let file = path.resolve(ROOT, rel);
      if (file !== ROOT && !file.startsWith(ROOT + path.sep)) {
        return res.writeHead(403).end('outside the repository');
      }
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
        file = path.join(file, 'index.html');
      }
      fs.readFile(file, (err, body) => {
        if (err) return res.writeHead(404).end('not found');
        res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' });
        res.end(body);
      });
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

// Open the reader, optionally at a page, and wait until it has put something on
// the screen. The AllSpeak script builds the page and fetches its first document
// after load, so the page list appearing is what says the reader has started.
async function open(base, hash, runtimeErrors) {
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.sendTo(console, { omitJSDOMErrors: true });
  const dom = await JSDOM.fromURL(base + 'docs-reader/' + (hash || ''), {
    runScripts: 'dangerously',
    resources: 'usable',
    pretendToBeVisual: true,
    virtualConsole,
    beforeParse(window) {
      // jsdom has no fetch, and no innerText — and the AllSpeak loader reads its
      // own bootstrap <pre> with innerText.
      window.fetch = (url, opts) => globalThis.fetch(new URL(url, window.location.href).href, opts);
      Object.defineProperty(window.HTMLElement.prototype, 'innerText', {
        get() { return this.textContent; },
        set(v) { this.textContent = v; },
        configurable: true
      });
      window.scrollTo = () => {};
      // The runtime's own progress chatter ("Compiled …") is not a finding; its
      // warnings and anything the page reports as an error are.
      window.console.log = (...a) => {
        const line = a.join(' ');
        if (/has not been used/.test(line)) errors.push('console.log: ' + line);
      };
      window.console.error = (...a) => errors.push('console.error: ' + a.join(' '));
      window.addEventListener('error', e => errors.push('error: ' + (e.message || e.error)));
    }
  });
  const w = dom.window, d = w.document;
  const text = sel => (d.querySelector(sel) || {}).textContent || '';
  const html = sel => (d.querySelector(sel) || {}).innerHTML || '';
  for (let i = 0; i < 120; i++) {
    if (text('#known-slugs').trim() && (html('#content').length > 500 || text('#notice-text'))) break;
    await sleep(500);
  }
  return {
    w, d, errors,
    text, html,
    title: () => (/<h1[^>]*>(.*?)<\/h1>/.exec(html('#content')) || [])[1],
    click: el => el.dispatchEvent(new w.MouseEvent('click', { bubbles: true, cancelable: true })),
    route: href => { d.querySelector('#nav-target').textContent = href; d.querySelector('#nav-trigger').click(); }
  };
}

async function settled(page, want, ms = 25000) {
  for (let i = 0; i < ms / 250; i++) {
    if (want()) return true;
    await sleep(250);
  }
  return false;
}

async function main() {
  const server = await serve();
  const base = `http://127.0.0.1:${server.address().port}/`;

  console.log('\n== contents page ==');
  {
    const p = await open(base);
    const slugs = p.text('#known-slugs').trim().split('\n');
    // The reader reads `main`, so this list is what the site would show, not what
    // the working tree holds: a document written here appears only once it is
    // pushed. It only ever grows, so the count is a floor and the order is the
    // assertion — the first document, the last, and nothing lost along the way.
    check('the page list is built from the README (at least 29 documents)', slugs.length >= 29, slugs.length);
    check('the reading order starts at concept/00', slugs[0] === 'concept/00-the-experience-is-the-product', slugs[0]);
    check('the reading order ends at the glossary', slugs[slugs.length - 1] === 'appendix/glossary', slugs[slugs.length - 1]);
    check('every slug in the list is unique', new Set(slugs).size === slugs.length);
    check('the contents page renders the README', p.title() === 'Room By Room — product documentation', p.title());
    check('tables are rendered', /<table/.test(p.html('#content')));
    check('the status band is lifted out of the body',
      p.text('#meta-bar').includes('Audience: all') && !p.html('#content').includes('Audience: all'));
    check('contents is disabled on the contents page', p.d.querySelector('#contents-button').disabled);
    check('previous is disabled on the contents page', p.d.querySelector('#prev-button').disabled);
    check('next is enabled on the contents page', !p.d.querySelector('#next-button').disabled);
    check('the source link points at the README on GitHub',
      p.d.querySelector('#source-link').getAttribute('href') === 'https://github.com/easycoder/rbr/blob/main/docs/README.md',
      p.d.querySelector('#source-link').getAttribute('href'));
    check('the notice is not shown', p.d.querySelector('#notice').style.display === 'none');
    check('the page logged no errors or warnings', p.errors.length === 0, p.errors.join(' | '));

    console.log('\n== clicking a link in the rendered page ==');
    const link = [...p.d.querySelectorAll('#content a')]
      .find(a => a.getAttribute('href') === 'concept/00-the-experience-is-the-product.md');
    check('a page link is present in the content', !!link);
    p.click(link);
    await settled(p, () => p.text('#route-out') === 'concept/00-the-experience-is-the-product');
    check('the clicked page is shown', p.title() === 'The experience is the product', p.title());
    check('the address bar follows', p.w.location.hash === '#concept/00-the-experience-is-the-product', p.w.location.hash);
    check('the source link follows the page',
      p.d.querySelector('#source-link').getAttribute('href') ===
      'https://github.com/easycoder/rbr/blob/main/docs/concept/00-the-experience-is-the-product.md',
      p.d.querySelector('#source-link').getAttribute('href'));
    check('the status band shows this document\'s audience', p.text('#meta-bar').includes('industry'), p.text('#meta-bar'));

    console.log('\n== the toolbar ==');
    p.click(p.d.querySelector('#next-button'));
    await settled(p, () => p.text('#route-out') === 'concept/01-why-room-by-room');
    check('next opens the following document', p.title() === 'Why room by room', p.title());
    p.click(p.d.querySelector('#next-button'));
    await settled(p, () => p.text('#route-out') === 'concept/02-what-rbr-is');
    check('next again', p.title() === 'What RBR is', p.title());
    check('previous is enabled mid-list', !p.d.querySelector('#prev-button').disabled);
    p.click(p.d.querySelector('#prev-button'));
    await settled(p, () => p.text('#route-out') === 'concept/01-why-room-by-room');
    check('previous goes back', p.title() === 'Why room by room', p.title());
    p.click(p.d.querySelector('#contents-button'));
    await settled(p, () => p.text('#route-out') === '' && p.title() === 'Room By Room — product documentation');
    check('contents returns to the README', p.title() === 'Room By Room — product documentation', p.title());
    check('the address is cleared on the contents page', p.w.location.hash === '', p.w.location.hash);

    console.log('\n== a link in the status band ==');
    p.click([...p.d.querySelectorAll('#content a')]
      .find(a => a.getAttribute('href') === 'concept/00-the-experience-is-the-product.md'));
    await settled(p, () => p.text('#route-out') === 'concept/00-the-experience-is-the-product');
    const band = p.d.querySelector('#meta-bar a');
    check('the band carries the document\'s "see also" links', !!band, band && band.getAttribute('href'));
    p.click(band);
    await settled(p, () => p.text('#route-out') === 'concept/01-why-room-by-room');
    check('a band link is followed by the reader', p.text('#route-out') === 'concept/01-why-room-by-room', p.text('#route-out'));

    console.log('\n== a relative link inside a document ==');
    const rel = [...p.d.querySelectorAll('#content a')].find(a => a.getAttribute('href') === '../appendix/glossary.md');
    check('a ../ link is present in the document', !!rel);
    p.click(rel);
    await settled(p, () => p.w.location.hash === '#appendix/glossary');
    check('../appendix/glossary.md resolves from concept/', p.text('#route-out') === 'appendix/glossary', p.text('#route-out'));
    check('the glossary is rendered', /glossary/i.test(p.title() || ''), p.title());

    console.log('\n== the end of the list ==');
    check('the last document disables next', p.d.querySelector('#next-button').disabled);
    check('the page logged no errors or warnings', p.errors.length === 0, p.errors.join(' | '));
    p.w.close();
  }

  console.log('\n== a document opened by address ==');
  {
    const p = await open(base, '#preparation/04-controller-computer');
    check('the addressed document is shown', p.title() === 'Preparing the controller computer', p.title());
    check('the address is kept', p.w.location.hash === '#preparation/04-controller-computer', p.w.location.hash);
    check('the reader agrees which page it is on', p.text('#route-out') === 'preparation/04-controller-computer', p.text('#route-out'));
    check('both directions are enabled mid-list',
      !p.d.querySelector('#prev-button').disabled && !p.d.querySelector('#next-button').disabled);
    check('the page logged no errors or warnings', p.errors.length === 0, p.errors.join(' | '));
    p.w.close();
  }

  console.log('\n== a document the README names but that is not written ==');
  {
    const p = await open(base, '#installation/01-installing-the-controller');
    await settled(p, () => !!p.text('#notice-text'));
    check('it is reported as unwritten, not as an error',
      /has not been written yet/.test(p.text('#notice-text')), JSON.stringify(p.text('#notice-text')));
    check('the notice links to the file on GitHub',
      p.d.querySelector('#notice-link').getAttribute('href') ===
      'https://github.com/easycoder/rbr/blob/main/docs/installation/01-installing-the-controller.md',
      p.d.querySelector('#notice-link').getAttribute('href'));
    check('the address keeps the slug', p.w.location.hash === '#installation/01-installing-the-controller', p.w.location.hash);
    check('the notice is shown', p.d.querySelector('#notice').style.display === 'block');
    check('the reading pane is out of the way', p.d.querySelector('#content').style.display === 'none');
    check('the page logged no errors or warnings', p.errors.length === 0, p.errors.join(' | '));
    p.w.close();
  }

  console.log('\n== a link out of the documentation tree ==');
  {
    const p = await open(base, '#concept/00-the-experience-is-the-product');
    await settled(p, () => p.text('#route-out') === 'concept/00-the-experience-is-the-product');
    // From docs/concept/, the engineering notes at the repository root are two levels up.
    p.route('../../doc/UPDATE-MECHANISM.md');
    await settled(p, () => !!p.text('#notice-text'));
    check('it is not fetched and dressed up as documentation',
      /not one of these documents/.test(p.text('#notice-text')), JSON.stringify(p.text('#notice-text')));
    check('the repository is offered instead',
      p.d.querySelector('#notice-link').getAttribute('href') === 'https://github.com/easycoder/rbr');
    check('the document on screen is unchanged',
      p.text('#route-out') === 'concept/00-the-experience-is-the-product', p.text('#route-out'));
    check('the page logged no errors or warnings', p.errors.length === 0, p.errors.join(' | '));
    p.w.close();
  }

  console.log('\n== a link that is not a Markdown document ==');
  {
    // No documentation page carries an external link today, so one is added:
    // what is under test is the reader's decision, not the document's content.
    const p = await open(base, '#concept/02-what-rbr-is');
    await settled(p, () => p.text('#route-out') === 'concept/02-what-rbr-is');
    const external = p.d.createElement('a');
    external.setAttribute('href', 'https://example.com/elsewhere');
    external.textContent = 'elsewhere';
    p.d.querySelector('#content').appendChild(external);
    let defaultPrevented = null;
    p.d.addEventListener('click', e => { defaultPrevented = e.defaultPrevented; });
    p.click(external);
    await sleep(500);
    check('the reader leaves it to the browser', defaultPrevented === false, defaultPrevented);
    check('the page logged no errors or warnings', p.errors.length === 0, p.errors.join(' | '));
    p.w.close();
  }

  console.log('\n== summary ==');
  console.log(`  ${pass} passed, ${fail} failed`);
  if (fail) console.log('  failed: ' + failures.join(', '));
  server.close();
  process.exit(fail ? 1 : 0);
}

main().catch(e => { console.error('CHECK FAILED TO RUN:', e); process.exit(2); });
