import asyncio
import json
import ssl
from typing import Dict, List, Callable, Optional
from .guardrails import validate_message

class AsyncTransportError(Exception):
    """Base exception for async transport errors"""
    pass

class AsyncConnectionError(AsyncTransportError):
    """Connection related errors"""
    pass

class AsyncMessageError(AsyncTransportError):
    """Message related errors"""
    pass

async def _async_send(writer, obj: dict, timeout: Optional[float] = None):
    """Send a message over async writer"""
    try:
        data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        writer.write(data)
        await asyncio.wait_for(writer.drain(), timeout)
    except asyncio.TimeoutError:
        raise AsyncConnectionError("Send timeout")
    except Exception as e:
        raise AsyncTransportError(f"Send failed: {e}")

async def _async_recv(reader, timeout: Optional[float] = None):
    """Receive a message from async reader"""
    try:
        line = await asyncio.wait_for(reader.readline(), timeout)
        if not line:
            return None
        try:
            return json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise AsyncMessageError(f"Invalid JSON: {e}")
    except asyncio.TimeoutError:
        raise AsyncConnectionError("Receive timeout")
    except Exception as e:
        raise AsyncTransportError(f"Receive failed: {e}")

async def run_async_server(
    host: str,
    port: int,
    handler: Callable[[Dict], List[Dict]],
    use_tls: bool = False,
    certfile: Optional[str] = None,
    keyfile: Optional[str] = None,
    max_connections: int = 8
):
    """
    Run an async AICL server
    """
    async def handle_client(reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[AICL] async connection from {addr}")
        
        try:
            while True:
                msg = await _async_recv(reader)
                if msg is None:
                    break
                
                # Validate message
                is_valid, error = validate_message(msg)
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
                    await _async_send(writer, error_msg)
                    continue
                
                # Process message
                try:
                    responses = handler(msg) or []
                    for out in responses:
                        await _async_send(writer, out)
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
                    await _async_send(writer, error_msg)
        except AsyncConnectionError as e:
            print(f"[AICL] connection error with {addr}: {e}")
        except Exception as e:
            print(f"[AICL] unexpected error with {addr}: {e}")
        finally:
            print(f"[AICL] disconnected from {addr}")
            writer.close()
            await writer.wait_closed()
    
    # Configure TLS if requested
    ssl_context = None
    if use_tls:
        if not certfile or not keyfile:
            raise AsyncTransportError("TLS requires certfile and keyfile")
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile, keyfile)
    
    server = await asyncio.start_server(
        handle_client, host, port, ssl=ssl_context
    )
    
    addr = server.sockets[0].getsockname()
    print(f"[AICL] async server on {addr[0]}:{addr[1]} (TLS: {use_tls})")
    
    async with server:
        await server.serve_forever()

async def run_async_client(
    host: str,
    port: int,
    msgs: List[Dict],
    use_tls: bool = False,
    timeout: float = 30.0
):
    """
    Run an async AICL client
    """
    # Configure TLS if requested
    ssl_context = None
    if use_tls:
        ssl_context = ssl.create_default_context()
    
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port, ssl=ssl_context),
        timeout
    )
    
    try:
        for msg in msgs:
            await _async_send(writer, msg, timeout)
            response = await _async_recv(reader, timeout)
            if response:
                yield response
    finally:
        writer.close()
        await writer.wait_closed()