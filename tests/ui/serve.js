// serve.js — static server for the UI suite.
//
//   node tests/ui/serve.js [port]
//
// Serves the repository root, which is enough for new-ui/ to boot: it fetches
// its scripts and Webson layouts by relative URL and needs nothing else from a
// server. Two responses are synthetic:
//
//   /new-ui/credentials.json  a fake broker, so the shell leaves demo mode and
//                             opens its MQTT path. It is served from memory
//                             rather than written into new-ui/, where a real
//                             file would sit beside real credentials and is not
//                             covered by .gitignore.
//   /credentials.php          not used while credentials.json answers, but
//                             answered explicitly so a fallback cannot escape
//                             to the network.
//
// No controller, broker or PHP is involved. See tests/ui/README.md.

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const PORT = Number(process.argv[2] || process.env.PORT || 4173);
const HOST = '127.0.0.1';

// The values only have to be present and non-empty: the MQTT client is stubbed
// before the page runs, so nothing ever dials this broker.
const CREDENTIALS = {
  broker: 'broker.invalid',
  port: 443,
  username: 'ui-test',
  password: 'ui-test',
};

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json',
  '.allspeak': 'text/plain; charset=utf-8',
};

function send(res, status, type, body) {
  res.writeHead(status, {
    'Content-Type': type,
    'Cache-Control': 'no-store',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${HOST}`);
  const pathname = decodeURIComponent(url.pathname);

  if (pathname === '/' || pathname === '') {
    res.writeHead(302, { Location: '/new-ui/index.html' });
    return res.end();
  }

  if (pathname === '/new-ui/credentials.json') {
    return send(res, 200, TYPES['.json'], JSON.stringify(CREDENTIALS));
  }

  // An empty object makes the shell fall through to demo mode if the fake
  // credentials above are ever removed, instead of reaching the real site.
  if (pathname === '/credentials.php') {
    return send(res, 200, TYPES['.json'], '{}');
  }

  const file = path.resolve(ROOT, '.' + pathname);
  if (file !== ROOT && !file.startsWith(ROOT + path.sep)) {
    return send(res, 403, 'text/plain', 'outside the repository');
  }

  fs.readFile(file, (err, body) => {
    if (err) return send(res, 404, 'text/plain', 'not found');
    const type = TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream';
    send(res, 200, type, body);
  });
});

server.listen(PORT, HOST, () => {
  console.log(`UI suite server on http://${HOST}:${PORT}`);
});
