import time
from aicl_logging import AICLLogger
from core import new_msg

def test_logging_and_metrics():
    print("=== Testing Logging and Metrics ===")
    
    # Create logger with compression
    logger = AICLLogger("test_logs", compress=False)
    print(f"Logger created with run ID: {logger.get_run_id()}")
    
    # Create test messages
    messages = [
        new_msg(
            frm="teacher",
            to="student",
            act="inform",
            payload={"caps": ["text", "logits:topk"], "max_ctx": 4096},
            limits={"tokens": 1024}
        ),
        new_msg(
            frm="student",
            to="teacher",
            act="ack",
            payload={"ok": True},
            limits={"tokens": 64}
        ),
        new_msg(
            frm="teacher",
            to="student",
            act="ask",
            payload={
                "text": {
                    "lang": "en",
                    "fmt": "md",
                    "content": "Explain knowledge distillation"
                }
            },
            limits={"tokens": 128}
        ),
        new_msg(
            frm="student",
            to="teacher",
            act="answer",
            payload={
                "text": {
                    "lang": "en",
                    "fmt": "md",
                    "content": "Knowledge distillation is a technique where a smaller model learns from a larger teacher model."
                },
                "logits": {
                    "temperature": 2.0,
                    "topk": [
                        {"tok": "distillation", "p": 0.35},
                        {"tok": "compression", "p": 0.25},
                        {"tok": "transfer", "p": 0.15}
                    ]
                }
            },
            limits={"tokens": 256}
        )
    ]
    
    # Log messages with simulated latencies
    start_time = time.time()
    for i, msg in enumerate(messages):
        latency = (i + 1) * 10.5  # Simulate increasing latency
        logger.log_message(msg, latency_ms=latency)
        print(f"Logged message {i+1}: {msg['act']} (latency: {latency}ms)")
    
    # Get and display metrics
    metrics = logger.get_metrics()
    print("\n=== Conversation Metrics ===")
    print(f"Total messages: {metrics['total_messages']}")
    print(f"Total tokens: {metrics['total_tokens']}")
    print(f"Average latency: {metrics['avg_latency_ms']:.2f}ms")
    print(f"Message types: {metrics['message_types']}")
    print(f"Participants: {metrics['participants']}")
    
    # Save metrics
    logger.save_metrics()
    print(f"\nMetrics saved to: metrics_{logger.get_run_id()}.json")
    
    # Calculate log hash
    log_hash = logger.calculate_log_hash()
    print(f"Log file hash: {log_hash}")
    
    print("\n=== Logging and Metrics Test Complete ===")

if __name__ == "__main__":
    test_logging_and_metrics()