// services/sigil_gate/index.ts - Express API server
import express from "express";
import cors from "cors";
import { seal, verifyPlan, logFsDelete, rollbackLast } from "./api.js";

const app = express();
app.use(cors());
app.use(express.json());

app.post("/seal", (req, res) => {
  try {
    const { operator = "Saint Lucid", plan, ttl_secs = 600 } = req.body || {};
    const id = seal(operator, plan, ttl_secs);
    res.json({ ok: true, seal_id: id });
  } catch (err) {
    res.status(500).json({ ok: false, error: String(err) });
  }
});

app.post("/verify", (req, res) => {
  try {
    const { plan } = req.body || {};
    const v = verifyPlan(plan);
    res.json(v);
  } catch (err) {
    res.status(500).json({ ok: false, reason: "error", error: String(err) });
  }
});

app.post("/journal/fs/delete", (req, res) => {
  try {
    const { seal_id, path } = req.body || {};
    logFsDelete(seal_id, path);
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ ok: false, error: String(err) });
  }
});

app.post("/rollback/last", (_req, res) => {
  try {
    const result = rollbackLast();
    res.json({ ok: result });
  } catch (err) {
    res.status(500).json({ ok: false, error: String(err) });
  }
});

app.get("/health", (_req, res) => {
  res.json({ status: "healthy", service: "Sigil Gate" });
});

const PORT = 7701;
app.listen(PORT, () => console.log(`✠ Sigil Gate API running on http://127.0.0.1:${PORT}`));
