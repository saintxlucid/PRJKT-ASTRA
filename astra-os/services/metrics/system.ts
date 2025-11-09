// services/metrics/system.ts - System metrics snapshot
import os from "os";

export function snapshot() {
  const cpus = os.loadavg()[0];
  const memUsed = (os.totalmem() - os.freemem()) / os.totalmem();
  const net = Object.values(os.networkInterfaces() || {}).flat().filter(Boolean).length;
  return { cpu_load: cpus, mem_used_ratio: memUsed, net_ifaces: net };
}
