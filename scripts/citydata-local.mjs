import { createServer } from 'node:http';
import { citydata } from '../worker/citydata.mjs';

const origin = 'http://127.0.0.1:8787';

createServer(async (incoming, outgoing) => {
  const url = new URL(incoming.url, origin);
  const response = url.pathname === '/api/citydata'
    ? await citydata(new Request(url, { method: incoming.method }), process.env)
    : new Response('Not found', { status: 404 });

  outgoing.writeHead(response.status, Object.fromEntries(response.headers));
  outgoing.end(Buffer.from(await response.arrayBuffer()));
}).listen(8787, '127.0.0.1', () => {
  console.log(`${origin}/api/citydata`);
});
