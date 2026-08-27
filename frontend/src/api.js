// In dev, Vite proxies /api -> localhost:8000 (see vite.config.js). In prod
// (Vercel static build), there's no dev-server proxy, so we need the deployed
// backend's absolute URL, set via VITE_API_URL at build time.
const API_ROOT = import.meta.env.VITE_API_URL || "";
const BASE = `${API_ROOT}/api`;

export async function getStatus() {
  const res = await fetch(`${BASE}/status`);
  if (!res.ok) throw new Error("status fetch failed");
  return res.json();
}

export async function getChunks() {
  const res = await fetch(`${BASE}/chunks`);
  if (!res.ok) throw new Error("chunks fetch failed");
  return res.json();
}

export async function runQuery(question) {
  const res = await fetch(`${BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error("query failed");
  return res.json();
}

export async function reingest() {
  const res = await fetch(`${BASE}/reingest`, { method: "POST" });
  if (!res.ok) throw new Error("reingest failed");
  return res.json();
}

export async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "upload failed");
  }
  return res.json();
}

export async function deleteSource(name) {
  const res = await fetch(`${BASE}/source/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || "delete failed");
  }
  return res.json();
}
