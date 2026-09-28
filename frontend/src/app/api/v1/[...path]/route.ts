import { NextRequest, NextResponse } from 'next/server';
import { createHmac } from 'node:crypto';
import { isIP } from 'node:net';

const upstream = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
function proxyError(status: number, code: string, message: string) {
  return NextResponse.json({ error: { code, message } }, { status });
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const method = request.method;
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const origin = request.headers.get('origin');
    const fetchSite = request.headers.get('sec-fetch-site');
    const host = request.headers.get('host');
    const forwardedScheme = request.headers.get('x-forwarded-proto')?.split(',')[0]?.trim();
    const scheme = forwardedScheme === 'https' || forwardedScheme === 'http' ? forwardedScheme : request.nextUrl.protocol.slice(0, -1);
    const expectedOrigin = host ? `${scheme}://${host}` : request.nextUrl.origin;
    if ((origin && origin !== expectedOrigin) || (!origin && fetchSite !== 'same-origin')) {
      return proxyError(403, 'FORBIDDEN', 'Cross-origin request refused');
    }
  }
  const target = new URL(`/api/v1/${path.join('/')}${request.nextUrl.search}`, upstream);
  const token = request.cookies.get('sahaya_session')?.value;
  const contentType = request.headers.get('content-type') || 'application/json';
  const headers = new Headers({ 'content-type': contentType });
  if (token) headers.set('authorization', `Bearer ${token}`);
  const proxySecret = process.env.BFF_SHARED_SECRET;
  if (proxySecret) {
    const forwarded = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim();
    if (forwarded && isIP(forwarded)) {
      const stamp = String(Math.floor(Date.now() / 1000));
      headers.set('x-sahaya-client-address', forwarded);
      headers.set('x-sahaya-client-time', stamp);
      headers.set('x-sahaya-client-signature', createHmac('sha256', proxySecret).update(`${stamp}:${forwarded}`).digest('hex'));
    }
  }
  try {
    let body: ArrayBuffer | undefined;
    if (!['GET', 'HEAD'].includes(method)) {
      const limit = contentType.startsWith('multipart/form-data') ? 11 * 1024 * 1024 : 100 * 1024;
      const reader = request.body?.getReader();
      const parts: Uint8Array[] = [];
      let size = 0;
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          size += value.byteLength;
          if (size > limit) { await reader.cancel(); return proxyError(413, 'PAYLOAD_TOO_LARGE', 'Request body is too large'); }
          parts.push(value);
        }
      }
      body = new ArrayBuffer(size);
      const bytes = new Uint8Array(body);
      let offset = 0;
      for (const part of parts) { bytes.set(part, offset); offset += part.byteLength; }
    }
    const result = await fetch(target, { method, headers, body, cache: 'no-store' });
    if (path.includes('evidence') && method === 'GET' && result.ok) {
      const binaryHeaders = new Headers();
      binaryHeaders.set('content-type', result.headers.get('content-type') || 'application/octet-stream');
      binaryHeaders.set('content-disposition', result.headers.get('content-disposition') || 'attachment');
      return new NextResponse(result.body, { status: result.status, headers: binaryHeaders });
    }
    const responseBody = await result.text();
    const parsed = responseBody ? JSON.parse(responseBody) : {};
    const response = NextResponse.json(path[0] === 'auth' && ['login', 'register'].includes(path[1]) && result.ok ? { user: parsed.user } : parsed, { status: result.status });
    const retryAfter = result.headers.get('retry-after');
    if (retryAfter) response.headers.set('retry-after', retryAfter);
    if (path[0] === 'auth' && ['login', 'register'].includes(path[1]) && result.ok && parsed.token) {
      response.cookies.set('sahaya_session', parsed.token, { httpOnly: true, secure: process.env.NODE_ENV === 'production', sameSite: 'strict', path: '/', maxAge: 60 * 60 * 12 });
    }
    if (path[0] === 'auth' && path[1] === 'logout') response.cookies.delete('sahaya_session');
    return response;
  } catch {
    const response = proxyError(503, 'SERVICE_UNAVAILABLE', 'Service unavailable. Please try again.');
    if (path[0] === 'auth' && path[1] === 'logout') response.cookies.delete('sahaya_session');
    return response;
  }
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as DELETE };
