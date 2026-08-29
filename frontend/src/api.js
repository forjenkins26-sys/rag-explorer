// In dev, Vite proxies /api -> localhost:8000 (see vite.config.js). In prod
// (Vercel static build), there's no dev-server proxy, so we need the deployed
// backend's absolute URL, set via VITE_API_URL at build time.
const API_ROOT = import.meta.env.VITE_API_URL || "";
const BASE = `${API_ROOT}/api`;

// --- per-visitor isolation -------------------------------------------------
//
// The backend scopes every document to an owner and refuses any request that
// arrives without one, so a public URL never shows one visitor another's
// uploads. The id is generated here, kept in localStorage, and sent on every
// call as X-Visitor-Id.
//
// This is isolation, not authentication: the id is effectively a bearer token,
// so anyone who learns it can read that workspace. It keeps strangers apart on
// a shared demo — it is not somewhere to put anything sensitive.
//
// Clearing site data loses the id, and with it access to those documents.

const VISITOR_KEY = "rag-explorer:visitor-id";

function newVisitorId() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function visitorId() {
  // Private windows and blocked site data make localStorage throw on access,
  // not just return null — so every read and write is guarded. Falling back to
  // a per-session id keeps the app usable there; the workspace simply does not
  // outlive the tab.
  try {
    const stored = localStorage.getItem(VISITOR_KEY);
    if (stored) return stored;
    const fresh = newVisitorId();
    localStorage.setItem(VISITOR_KEY, fresh);
    return fresh;
  } catch {
    if (!window.__ragVisitorFallback) window.__ragVisitorFallback = newVisitorId();
    return window.__ragVisitorFallback;
  }
}

function headers(extra = {}) {
  return { "X-Visitor-Id": visitorId(), ...extra };
}

async function detail(res, fallback) {
  const body = await res.json().catch(() => null);
  return new Error(body?.detail || fallback);
}

export async function getStatus() {
  const res = await fetch(`${BASE}/status`, { headers: headers() });
  if (!res.ok) throw await detail(res, "status fetch failed");
  return res.json();
}

export async function getChunks() {
  const res = await fetch(`${BASE}/chunks`, { headers: headers() });
  if (!res.ok) throw await detail(res, "chunks fetch failed");
  return res.json();
}

export async function runQuery(question) {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json" }),
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw await detail(res, "query failed");
  return res.json();
}

export async function reingest() {
  const res = await fetch(`${BASE}/reingest`, {
    method: "POST",
    headers: headers(),
  });
  if (!res.ok) throw await detail(res, "reingest failed");
  return res.json();
}

export async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);
  // No Content-Type here on purpose — the browser sets the multipart boundary.
  const res = await fetch(`${BASE}/upload`, {
    method: "POST",
    headers: headers(),
    body: form,
  });
  if (!res.ok) throw await detail(res, "upload failed");
  return res.json();
}

export async function deleteSource(name) {
  const res = await fetch(`${BASE}/source/${encodeURIComponent(name)}`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw await detail(res, "delete failed");
  return res.json();
}

export async function clearAllSources() {
  const res = await fetch(`${BASE}/sources`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw await detail(res, "clear failed");
  return res.json();
}
