from locust import HttpUser, task, between, events
import time

FIRST_TOKEN_TIMEOUT_S = 5.0  # fail fast if stream doesn't start

def read_first_sse_chunk(resp):
    start = time.time()
    for line in resp.iter_lines():
        if line:
            return time.time() - start
        if time.time() - start > FIRST_TOKEN_TIMEOUT_S:
            raise RuntimeError("First token timeout")
    raise RuntimeError("No SSE data")

class AstraUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(1)
    def health(self):
        with self.client.get("/health/full", name="health_full", timeout=5, catch_response=True) as r:
            ok = r.status_code == 200 and r.json().get("status") in ("ok", "degraded")
            r.success() if ok else r.failure("bad health")

    @task(2)
    def answer(self):
        with self.client.get("/answer", params={"q":"Ping Cairo memory"}, name="answer", timeout=15, catch_response=True) as r:
            j = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and "citations" in j and "text" in j
            r.success() if ok else r.failure("bad /answer schema")

    @task(2)
    def stream(self):
        with self.client.get("/stream", params={"query":"Tell me a short story"}, name="stream", stream=True, timeout=25, catch_response=True) as r:
            try:
                ttfb = read_first_sse_chunk(r)
                events.request.fire(
                    request_type="CUSTOM", name="stream_first_token",
                    response_time=ttfb*1000, response_length=0, exception=None
                )
                r.success()
            except Exception as e:
                r.failure(str(e))