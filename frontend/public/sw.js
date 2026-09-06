const SHELL = "keprix-chat-shell-v1";
const SHELL_ASSETS = ["/chat-only", "/logo-opaque.png", "/favicon.ico"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(SHELL_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== SHELL).map((key) => caches.delete(key)))),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname.includes("/messages")) {
    event.respondWith(fetch(request).catch(() => new Response(JSON.stringify({ error: "offline" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    })));
    return;
  }
  event.respondWith(fetch(request).catch(() => caches.match(request).then((cached) => cached || caches.match("/chat-only"))));
});
