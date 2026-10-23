const http = require('http');
const fs = require('fs');
const path = require('path');

const MIME = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml'
};

const server = http.createServer((req, res) => {
  if (req.url === '/api/data' || req.url.startsWith('/api/data?')) {
    // Reload data from disk each time so changes take effect without restart
    try {
      const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'data/data.json'), 'utf8'));
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Cache-Control', 'no-store');
      return res.end(JSON.stringify(data));
    } catch(e) {
      res.writeHead(500); return res.end('Error loading data');
    }
  }
  let filePath = path.join(__dirname, 'public', req.url === '/' ? 'index.html' : req.url);
  const ext = path.extname(filePath);
  fs.readFile(filePath, (err, content) => {
    if (err) { res.writeHead(404); return res.end('Not found'); }
    res.setHeader('Content-Type', MIME[ext] || 'text/plain');
    // No caching for HTML files so changes always take effect
    if (ext === '.html' || !ext) res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');
    res.end(content);
  });
});

server.listen(3000, () => console.log('Dev server at http://localhost:3000'));
