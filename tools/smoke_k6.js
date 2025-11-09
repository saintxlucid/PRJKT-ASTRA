import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = { vus: 50, duration: '1m' };

export default function () {
  const base = __ENV.BASE || 'http://localhost:8080';
  check(http.get(`${base}/live`), { 'live 200': r => r.status===200 });
  check(http.get(`${base}/ready`), { 'ready 200': r => r.status===200 });
  const r = http.get(`${base}/answer?q=Ping`);
  check(r, { 'answer ok': x => x.status===200 && x.json('citations') });
  sleep(0.2);
}