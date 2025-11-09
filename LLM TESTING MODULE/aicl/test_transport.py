import transport
import threading
import time

def test_handler(msg):
    print(f"Received message: {msg}")
    return []

def test_server():
    print("Starting test server on port 5557...")
    transport.run_server("127.0.0.1", 5557, test_handler)

def test_client():
    # Import core inside function to avoid linter issues
    from core import new_msg
    
    time.sleep(1)  # Wait for server to start
    print("Sending test message...")
    msg = new_msg("client", "server", "test", {"content": "Hello, server!"})
    try:
        responses = list(transport.run_client("127.0.0.1", 5557, [msg]))
        print(f"Received {len(responses)} responses")
    except Exception as e:
        print(f"Client error: {e}")

if __name__ == "__main__":
    # Start server in background thread
    server_thread = threading.Thread(target=test_server, daemon=True)
    server_thread.start()
    
    # Run client test
    test_client()