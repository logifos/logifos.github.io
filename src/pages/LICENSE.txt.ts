import notice from '../../LICENSE.txt?raw';

export function GET() {
  return new Response(notice, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
