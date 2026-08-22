const TOKEN_KEY = 'pashusafe_token';

export class ApiError extends Error {
  status: number;
  body: any;
  constructor(status: number, body: any) {
    super(
      typeof body?.detail === 'string'
        ? body.detail
        : body?.detail
          ? JSON.stringify(body.detail)
          : status >= 500 || status === 0
            ? `Server unreachable (HTTP ${status}) — is the backend running on :8000?`
            : `Request failed (HTTP ${status})`
    );
    this.status = status;
    this.body = body;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (!(options.body instanceof FormData) && options.body) {
    headers['Content-Type'] = 'application/json';
  }
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`/api/v1${path}`, { ...options, headers });

  if (res.status === 401 && !path.startsWith('/auth/login')) {
    setToken(null);
    window.location.href = '/login';
    throw new ApiError(401, { detail: 'Session expired' });
  }

  if (res.status === 204) return undefined as T;

  let body: any = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON */
  }

  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

export async function loginForm(email: string, password: string) {
  const form = new URLSearchParams({ username: email, password });
  const res = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  });
  if (!res.ok) throw new ApiError(res.status, await res.json().catch(() => ({})));
  return res.json();
}
