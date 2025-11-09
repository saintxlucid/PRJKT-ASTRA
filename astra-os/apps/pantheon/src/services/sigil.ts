// apps/pantheon/src/services/sigil.ts - Sigil Gate API helpers
const SIGIL_URL = import.meta.env.VITE_SIGIL_API || "http://127.0.0.1:7701";

async function post(path: string, body?: unknown) {
  const res = await fetch(`${SIGIL_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json?.error || `Sigil error: ${res.status}`);
  return json;
}

export async function sealPlan(operator: string, plan: unknown, ttl_secs = 600) {
  return post("/seal", { operator, plan, ttl_secs });
}

export async function verifyPlan(plan: unknown) {
  return post("/verify", { plan });
}

// journal delete expects { seal_id, path }
export async function journalDelete(seal_id: number, path: string) {
  return post("/journal/fs/delete", { seal_id, path });
}

export async function rollbackLast() {
  return post("/rollback/last");
}
