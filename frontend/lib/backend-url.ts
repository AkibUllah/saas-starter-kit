/**
 * Where server-side code (route handlers, middleware, Server Components) reaches the API.
 *
 * BACKEND_URL wins. Otherwise BACKEND_HOSTPORT ("host:port", as Render's blueprint
 * `fromService.property: hostport` provides it) is turned into an http URL on the
 * private network. Falls back to the local dev API.
 */
export const DEFAULT_BACKEND_URL = "http://localhost:8000";

export function resolveBackendUrl(backendUrl?: string, backendHostPort?: string): string {
  const explicit = backendUrl?.trim();
  if (explicit) return explicit.replace(/\/+$/, "");
  const hostPort = backendHostPort?.trim();
  if (hostPort) return /^https?:\/\//.test(hostPort) ? hostPort.replace(/\/+$/, "") : `http://${hostPort}`;
  return DEFAULT_BACKEND_URL;
}
