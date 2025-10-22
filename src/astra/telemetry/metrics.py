"""
Prometheus-compatible metrics collection and exposition.
"""
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()

# Global metric storage
COUNTERS: Dict[str, float] = {}
HISTOGRAMS: Dict[str, List[float]] = {}
GAUGES: Dict[str, float] = {}

def inc(name: str, val: float = 1.0) -> None:
    """Increment a counter."""
    COUNTERS[name] = COUNTERS.get(name, 0) + val
    logger.debug("counter_incremented", 
                counter=name,
                value=val,
                total=COUNTERS[name])

def observe(name: str, val: float) -> None:
    """Record a histogram observation."""
    HISTOGRAMS.setdefault(name, []).append(val)
    logger.debug("histogram_observation",
                histogram=name,
                value=val)

def set_gauge(name: str, val: float) -> None:
    """Set a gauge value."""
    GAUGES[name] = val
    logger.debug("gauge_set",
                gauge=name,
                value=val)

class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics."""
    
    def do_GET(self):
        """Handle GET request."""
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
            
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.end_headers()
        
        # Build response
        out = []
        
        # Counters
        for k, v in COUNTERS.items():
            out.extend([
                f"# TYPE {k} counter\n",
                f"# HELP {k} Counter metric\n",
                f"{k} {v}\n"
            ])
        
        # Histograms
        for k, vals in HISTOGRAMS.items():
            if not vals:
                continue
            out.extend([
                f"# TYPE {k} histogram\n",
                f"# HELP {k} Histogram metric\n",
                f"{k}_count {len(vals)}\n",
                f"{k}_sum {sum(vals)}\n"
            ])
            
            # Calculate quantiles
            sorted_vals = sorted(vals)
            quantiles = [0.5, 0.9, 0.95, 0.99]
            for q in quantiles:
                idx = int(q * len(sorted_vals))
                if idx < len(sorted_vals):
                    out.append(f'{k}_quantile{{quantile="{q}"}} {sorted_vals[idx]}\n')
        
        # Gauges
        for k, v in GAUGES.items():
            out.extend([
                f"# TYPE {k} gauge\n",
                f"# HELP {k} Gauge metric\n",
                f"{k} {v}\n"
            ])
        
        self.wfile.write("".join(out).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def serve_metrics(port: int = 9108, host: str = "0.0.0.0") -> None:
    """Start metrics server in background thread."""
    server = HTTPServer((host, port), MetricsHandler)
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
        name="metrics-server"
    )
    thread.start()
    logger.info("metrics_server_started",
                host=host,
                port=port)