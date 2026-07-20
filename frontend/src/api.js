const BASE = "/api";

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
