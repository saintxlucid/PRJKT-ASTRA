import socket
import json
import threading
import time
import ssl
from typing import Dict, List, Callable, Optional, Any

# Use absolute imports instead of relative imports
from . import guardrails

class TransportError(Exception):
    """Base exception for transport errors"""
    pass

class ConnectionError(TransportError):
    """Connection related errors"""
    pass

class MessageError(TransportError):
    """Message related errors"""
    pass

def _send(sock, obj: dict, timeout: Optional[float] = None):
    """Send a message over socket"""
    if timeout:
        sock.settimeout(timeout)
    
    try:
        data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        sock.sendall(data)
    except socket.timeout:
        raise ConnectionError("Send timeout")
    except socket.error as e:
        raise ConnectionError(f"Send failed: {e}")
    except Exception as e:
        raise TransportError(f"Unexpected send error: {e}")

def _recv(sock, timeout: Optional[float] = None):
    """Receive a message from socket"""
    if timeout:
        sock.settimeout(timeout)
    
    buf = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk: 
                return None
            buf += chunk
            if b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try: 
                    return json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as e:
                    raise MessageError(f"Invalid JSON: {e}")
    except socket.timeout:
        raise ConnectionError("Receive timeout")
    except socket.error as e:
        raise ConnectionError(f"Receive failed: {e}")
    except Exception as e:
        raise TransportError(f"Unexpected receive error: {e}")

def run_server(
    host: str, 
    port: int, 
    handler: Callable[[Dict], List[Dict]], 
    use_tls: bool = False,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
    max_connections: int = 8,
    message_timeout: float = 30.0
):
    """
    Run an AICL server
    
    Args:
        host: Host to bind to
        port: Port to listen on
        handler: Function to process incoming messages
        use_tls: Whether to use TLS encryption
        certfile: Path to certificate file (required if use_tls=True)
        keyfile: Path to private key file (required if use_tls=True)
        max_connections: Maximum concurrent connections
        message_timeout: Timeout for message operations
    """
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Configure TLS if requested
        if use_tls:
            if not certfile or not keyfile:
                raise TransportError("TLS requires certfile and keyfile")
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile, keyfile)
            srv = context.wrap_socket(srv, server_side=True)
        
        srv.bind((host, port))
        srv.listen(max_connections)
        print(f"[AICL] server on {host}:{port} (TLS: {use_tls})")
        
        def worker(conn, addr):
            print(f"[AICL] connection from {addr}")
            try:
                with conn:
                    while True:
                        msg = _recv(conn, message_timeout)
                        if msg is None: 
                            break
                        
                        # Validate message
                        is_valid, error = guardrails.validate_message(msg)
                        if not is_valid:
                            print(f"[AICL] invalid message from {addr}: {error}")
                            error_msg = {
                                "v": "aicl/1.0",
                                "id": "error",
                                "from": "server",
                                "to": msg.get("from", "unknown"),
                                "act": "error",
                                "payload": {"error": error}
                            }
                            _send(conn, error_msg, message_timeout)
                            continue
                        
                        # Process message
                        try:
                            responses = handler(msg) or []
                            for out in responses: 
                                _send(conn, out, message_timeout)
                        except Exception as e:
                            print(f"[AICL] handler error: {e}")
                            error_msg = {
                                "v": "aicl/1.0",
                                "id": "handler_error",
                                "from": "server",
                                "to": msg.get("from", "unknown"),
                                "act": "error",
                                "payload": {"error": str(e)}
                            }
                            _send(conn, error_msg, message_timeout)
            except ConnectionError as e:
                print(f"[AICL] connection error with {addr}: {e}")
            except Exception as e:
                print(f"[AICL] unexpected error with {addr}: {e}")
            finally:
                print(f"[AICL] disconnected from {addr}")
                    
        while True:
            c, a = srv.accept()
            threading.Thread(target=worker, args=(c, a), daemon=True).start()
            
    except Exception as e:
        raise TransportError(f"Server error: {e}")

def run_client(
    host: str, 
    port: int, 
    msgs_iter: List[Dict],
    use_tls: bool = False,
    message_timeout: float = 30.0
):
    """
    Run an AICL client
    
    Args:
        host: Host to connect to
        port: Port to connect to
        msgs_iter: Messages to send
        use_tls: Whether to use TLS encryption
        message_timeout: Timeout for message operations
    """
    try:
        # Create connection
        sock = socket.create_connection((host, port))
        
        # Configure TLS if requested
        if use_tls:
            context = ssl.create_default_context()
            sock = context.wrap_socket(sock, server_hostname=host)
        
        with sock:
            for m in msgs_iter: 
                _send(sock, m, message_timeout)
                response = _recv(sock, message_timeout)
                if response:
                    yield response
                    
    except Exception as e:
        raise TransportError(f"Client error: {e}")

class AICLConnection:
    """
    A persistent AICL connection for bidirectional communication
    """
    
    def __init__(
        self, 
        host: str, 
        port: int, 
        use_tls: bool = False,
        message_timeout: float = 30.0
    ):
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.message_timeout = message_timeout
        self.sock = None
        self.connected = False
    
    def connect(self):
        """Establish connection"""
        try:
            self.sock = socket.create_connection((self.host, self.port))
            
            if self.use_tls:
                context = ssl.create_default_context()
                self.sock = context.wrap_socket(self.sock, server_hostname=self.host)
            
            self.connected = True
            return True
        except Exception as e:
            print(f"[AICL] connection failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close connection"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.connected = False
        self.sock = None
    
    def send(self, msg: Dict) -> bool:
        """Send a message"""
        if not self.connected or not self.sock:
            return False
        try:
            _send(self.sock, msg, self.message_timeout)
            return True
        except Exception as e:
            print(f"[AICL] send failed: {e}")
            self.connected = False
            return False
    
    def recv(self) -> Optional[Dict]:
        """Receive a message"""
        if not self.connected or not self.sock:
            return None
        try:
            return _recv(self.sock, self.message_timeout)
        except Exception as e:
            print(f"[AICL] receive failed: {e}")
            self.connected = False
            return None