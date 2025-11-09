// services/sigil_gate/verify.ts
import { digest, latestSeal } from "./journal.js";

export function verifyPlan(plan: unknown): { ok: boolean; reason?: string } {
  const last = latestSeal() as any;
  if (!last) return { ok: false, reason: "no_seal" };
  
  const now = Date.now() / 1000;
  const issued = Date.parse(last.ts) / 1000;
  if (now - issued > last.ttl_secs) return { ok: false, reason: "ttl_expired" };
  
  const d = digest(plan);
  if (d !== last.plan_digest) return { ok: false, reason: "plan_mismatch" };
  
  return { ok: true };
}
