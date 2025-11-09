import transport
import threading
import time

def test_handler(msg):
    print(f"Server received message: {msg.get('act')} from {msg.get('from')}")
    
    # If it's an inform message, send an ack back
    if msg.get("act") == "inform":
        from core import new_msg
        response = new_msg(
            frm="server",
            to=msg.get("from", "unknown"),
            act="ack",
            payload={"ok": True}
        )
        print("Server sending ACK response")
        return [response]
    
    return []

def test_server():
    print("Starting test server on port 5558...")
    transport.run_server("127.0.0.1", 5558, test_handler)

def test_client():
    time.sleep(1)  # Wait for server to start
    print("Sending test message...")
    
    # Import core inside function to avoid linter issues
    from core import new_msg
    
    msg = new_msg(
        frm="client", 
        to="server", 
        act="inform", 
        payload={"test": "Hello, server!"}
    )
    
    try:
        responses = list(transport.run_client("127.0.0.1", 5558, [msg]))
        print(f"Client received {len(responses)} responses")
        for response in responses:
            print(f"Client received response: {response}")
    except Exception as e:
        print(f"Client error: {e}")

if __name__ == "__main__":
    # Start server in background thread
    server_thread = threading.Thread(target=test_server, daemon=True)
    server_thread.start()
    
    # Run client test
    test_client()