// scripts/loadtest_baseline.js
// k6 load test to baseline p95 latency for ASTRA API
//
// Install k6: https://k6.io/docs/getting-started/installation/
// Run: k6 run scripts/loadtest_baseline.js
//
// Scenarios:
//   1. Warmup: 5 VUs for 30s (warm cache, JIT)
//   2. Baseline: 10 VUs for 2 min (measure p95, p99)
//   3. Spike: 20 VUs for 30s (check circuit breaker)

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const llmLatency = new Trend('llm_latency', true);
const cacheHitRate = new Rate('cache_hit_rate');
const errorRate = new Rate('error_rate');

// Configuration
export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Warmup: 5 VUs
    { duration: '2m', target: 10 },   // Baseline: 10 VUs
    { duration: '30s', target: 20 },  // Spike: 20 VUs
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1200', 'p(99)<2000'], // p95 < 1.2s, p99 < 2s
    'http_req_failed': ['rate<0.05'],                   // <5% error rate
    'error_rate': ['rate<0.05'],
    'llm_latency': ['p(95)<1500'],                      // LLM p95 < 1.5s
  },
};

const BASE_URL = 'http://localhost:8080';
const API_KEY = 'your-api-key-here';  // Replace with actual key or use env var

// Test prompts (varying complexity)
const prompts = [
  'What is 2+2?',
  'Explain the concept of recursion in one sentence.',
  'Write a haiku about programming.',
  'What are the benefits of using a circuit breaker pattern?',
  'Describe semantic caching and when to use it.',
];

export default function () {
  const prompt = prompts[Math.floor(Math.random() * prompts.length)];
  
  const payload = JSON.stringify({
    model: 'gpt-oss-20b',
    messages: [
      { role: 'user', content: prompt }
    ],
    max_tokens: 100,
    temperature: 0.7,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
    },
    timeout: '30s',
  };

  const startTime = new Date().getTime();
  const response = http.post(`${BASE_URL}/v1/chat/completions`, payload, params);
  const endTime = new Date().getTime();
  
  const duration = endTime - startTime;
  llmLatency.add(duration);

  // Check response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'has choices': (r) => JSON.parse(r.body).choices !== undefined,
    'response time < 3s': (r) => r.timings.duration < 3000,
  });

  errorRate.add(!success);

  // Check for cache headers (if you add them)
  if (response.headers['X-Cache-Hit']) {
    cacheHitRate.add(response.headers['X-Cache-Hit'] === 'true');
  }

  // Random think time (1-3 seconds)
  sleep(Math.random() * 2 + 1);
}

export function handleSummary(data) {
  console.log('==== LOAD TEST SUMMARY ====');
  console.log(`Requests:        ${data.metrics.http_reqs.values.count}`);
  console.log(`Failed:          ${data.metrics.http_req_failed.values.rate * 100}%`);
  console.log(`Duration p95:    ${data.metrics.http_req_duration.values['p(95)']} ms`);
  console.log(`Duration p99:    ${data.metrics.http_req_duration.values['p(99)']} ms`);
  console.log(`LLM Latency p95: ${data.metrics.llm_latency.values['p(95)']} ms`);
  console.log(`Error Rate:      ${data.metrics.error_rate.values.rate * 100}%`);
  
  if (data.metrics.cache_hit_rate) {
    console.log(`Cache Hit Rate:  ${data.metrics.cache_hit_rate.values.rate * 100}%`);
  }
  
  return {
    'summary.txt': JSON.stringify(data, null, 2),
  };
}
