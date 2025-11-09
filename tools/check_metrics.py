#!/usr/bin/env python3
"""Simple metrics checker and visualizer for ASTRA Core"""
import requests
import sys
from datetime import datetime

def parse_metrics(text):
    """Parse Prometheus metrics text format"""
    metrics = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Simple parsing: metric_name{labels} value
        if '{' in line:
            metric_name = line.split('{')[0]
            rest = line.split('{')[1]
            labels_str = rest.split('}')[0]
            value = rest.split('}')[1].strip()
            
            # Parse labels
            labels = {}
            for label in labels_str.split(','):
                if '=' in label:
                    k, v = label.split('=', 1)
                    labels[k.strip()] = v.strip(' "')
            
            key = f"{metric_name}_{','.join(f'{k}={v}' for k, v in labels.items())}"
            metrics[key] = float(value)
        else:
            parts = line.split()
            if len(parts) == 2:
                metrics[parts[0]] = float(parts[1])
    
    return metrics

def display_metrics(url):
    """Fetch and display metrics"""
    try:
        response = requests.get(f"{url}/metrics", timeout=5)
        response.raise_for_status()
        
        metrics = parse_metrics(response.text)
        
        print(f"\n🔍 ASTRA Core Metrics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # System info
        uptime = metrics.get('astra_uptime_seconds', 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        print(f"\n📊 System Status")
        print(f"  Uptime: {hours}h {minutes}m {seconds}s")
        
        # Request metrics
        print(f"\n📈 Request Metrics")
        total_requests = sum(v for k, v in metrics.items() if k.startswith('astra_requests_total'))
        print(f"  Total Requests: {int(total_requests)}")
        
        for key, value in sorted(metrics.items()):
            if key.startswith('astra_requests_total'):
                endpoint = key.split('endpoint=')[1] if 'endpoint=' in key else 'unknown'
                print(f"    {endpoint}: {int(value)}")
        
        # Latency metrics
        print(f"\n⏱️  Latency (P95)")
        for key, value in sorted(metrics.items()):
            if 'quantile=0.95' in key:
                endpoint = key.split('endpoint=')[1].split(',')[0] if 'endpoint=' in key else 'unknown'
                print(f"    {endpoint}: {value*1000:.0f}ms")
        
        # Queue depth
        avg_queue = metrics.get('astra_queue_depth_avg', 0)
        max_queue = metrics.get('astra_queue_depth_max', 0)
        print(f"\n🚦 Queue Depth")
        print(f"    Average: {avg_queue:.1f}")
        print(f"    Maximum: {int(max_queue)}")
        
        # Errors
        errors = {k: v for k, v in metrics.items() if k.startswith('astra_errors_total')}
        if errors:
            print(f"\n❌ Errors")
            for key, value in errors.items():
                error_type = key.split('error=')[1] if 'error=' in key else 'unknown'
                print(f"    {error_type}: {int(value)}")
        else:
            print(f"\n✅ No Errors Recorded")
        
        # Circuit breakers
        breakers = {k: v for k, v in metrics.items() if k.startswith('astra_circuit_breaker_trips')}
        if breakers:
            print(f"\n⚡ Circuit Breaker Trips")
            for key, value in breakers.items():
                component = key.split('component=')[1] if 'component=' in key else 'unknown'
                print(f"    {component}: {int(value)}")
        else:
            print(f"\n✅ No Circuit Breaker Trips")
        
        print("\n" + "=" * 70)
        
    except requests.RequestException as e:
        print(f"❌ Error fetching metrics: {e}")
        sys.exit(1)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
    display_metrics(url)
