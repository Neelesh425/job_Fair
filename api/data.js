const data = require('../data/data.json');
module.exports = (req, res) => {
  const pw = process.env.SITE_PASSWORD;
  if (!pw && process.env.PUBLIC_ACCESS !== 'true') return res.status(503).json({ error: 'not configured' });
  if (pw && req.headers['x-password'] !== pw) return res.status(401).json({ error: 'password required' });
  res.setHeader('Cache-Control', 'no-store');
  res.status(200).json(data);
};
