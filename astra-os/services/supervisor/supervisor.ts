// services/supervisor/supervisor.ts - Job orchestration with heartbeat
import express from "express";
import cors from "cors";
import crypto from "crypto";

type State = "pending"|"running"|"paused"|"complete"|"failed";
interface Job {
  id: string;
  title: string;
  state: State;
  plan_digest: string;
  created_at: number;
  updated_at: number;
  heartbeat_at?: number;
  mode: "simulate"|"live";
  budget: { files: number; bytes: number; req_per_min: number };
  counters: { files: number; bytes: number; req: number };
}

const app = express();
app.use(cors()); 
app.use(express.json());

const jobs = new Map<string, Job>();

app.post("/jobs", (req: any, res: any) => {
  const { title, plan } = req.body || {};
  const id = crypto.randomUUID();
  const j: Job = {
    id, 
    title: title ?? "Untitled",
    state: "pending",
    plan_digest: crypto.createHash("sha256").update(JSON.stringify(plan||{})).digest("hex"),
    created_at: Date.now(), 
    updated_at: Date.now(),
    mode: "simulate",
    budget: { files: 1000, bytes: 10*1024*1024*1024, req_per_min: 100 },
    counters: { files: 0, bytes: 0, req: 0 }
  };
  jobs.set(id, j);
  res.json({ ok: true, id });
});

app.post("/jobs/:id/start", (req: any, res: any) => {
  const job = jobs.get(req.params.id); 
  if (!job) return res.status(404).end();
  job.state = "running"; 
  job.updated_at = Date.now(); 
  job.mode = req.body?.mode ?? job.mode;
  res.json({ ok: true, job });
});

app.post("/jobs/:id/heartbeat", (req: any, res: any) => {
  const job = jobs.get(req.params.id); 
  if (!job) return res.status(404).end();
  job.heartbeat_at = Date.now(); 
  res.json({ ok: true });
});

app.post("/jobs/:id/kill", (req: any, res: any) => {
  const job = jobs.get(req.params.id); 
  if (!job) return res.status(404).end();
  job.state = "failed"; 
  job.updated_at = Date.now(); 
  res.json({ ok: true });
});

app.get("/jobs", (_req: any, res: any) => {
  res.json({ jobs: Array.from(jobs.values()) });
});

app.get("/health", (_req: any, res: any) => {
  res.json({ status: "healthy", service: "Weaver", jobs: jobs.size });
});

const PORT = 7703;
app.listen(PORT, () => console.log(`☍ Weaver Supervisor running on http://127.0.0.1:${PORT}`));
