# AICL - AI Interchange Chat Language

AICL is a lightweight, efficient communication protocol designed for LLM-to-LLM interactions. It provides both a human-readable JSON format (AICL-Core) and a compact ASCII format (AICL-Glyph) for token-efficient communication.

## Features

- **Token-efficient**: Compact glyph format for tight token budgets
- **Extensible**: Versioned with capability negotiation
- **Deterministic**: Easy to parse with predictable structure
- **Safe**: Comprehensive security features including message signing, rate limiting, and governance policies
- **Rich payload**: Supports text, embeddings, logits, and tool calls
- **Reliable**: Robust error handling and connection management
- **Observable**: Comprehensive logging and metrics tracking
- **Configurable**: Centralized configuration management
- **Streaming**: Support for large payload streaming
- **Routing**: Message routing and pub/sub capabilities
- **Async**: Asynchronous operations support
- **Benchmarking**: Performance measurement tools

## Module Structure

- `aicl.core`: Core message handling (serialization, parsing, signing)
- `aicl.transport`: Network transport layer (TCP, sockets) with TLS support
- `aicl.logging`: Conversation logging, replay, and metrics tracking
- `aicl.guardrails`: Security and policy enforcement
- `aicl.config`: Configuration management
- `aicl.streaming`: Streaming support for large payloads
- `aicl.routing`: Message routing and broker system
- `aicl.compression`: Payload compression utilities
- `aicl.benchmark`: Performance benchmarking tools
- `aicl.async_transport`: Async version of transport layer
- `scripts/`: Utility scripts (replayer, etc.)
- `examples.py`: Basic usage examples
- `comprehensive_example.py`: Advanced features demonstration
- `teacher_demo.py`/`student_demo.py`: Simple demo implementations

## Message Structure

### AICL-Core (JSON Lines)
```json
{
  "v": "aicl/1.0",
  "id": "3b2f7f64-3a6b-42a4-9a3f-22f6",
  "ts": "2025-10-12T12:00:00Z",
  "from": "model://neox20b",
  "to": "model://gpt2l",
  "caps": ["text","emb","tool:math","logits:topk"],
  "act": "ask",
  "topic": "distillation",
  "ctx": {"turn": 1, "thread": "abcd"},
  "limits": {"tokens": 1024, "latency_ms": 800},
  "payload": {
    "text": {"lang":"en","fmt":"md","content":"Summarize this chunk → …"},
    "emb": null,
    "logits": null,
    "tool": null
  },
  "sig": null
}
```

### AICL-Glyph (Compact ASCII)
```
A1|id=3b2f...|f=neox20b|t=gpt2l|a=ask|tp=distill|trn=1|tk=1024|
TXT:en:md|Summarize→ …
```

## Usage

### Basic Message Handling
```python
from aicl import new_msg, aicl_core, to_glyph, from_glyph, sign, verify

# Create a message
msg = new_msg(
    frm="model://neox20b",
    to="model://gpt2l",
    act="ask",
    payload={
        "text": {
            "lang": "en",
            "fmt": "md",
            "content": "Summarize: Large language models are powerful."
        }
    }
)

# Serialize to JSON
json_msg = aicl_core(msg)

# Convert to compact glyph format
glyph_msg = to_glyph(msg)

# Parse glyph back to dict
parsed_msg = from_glyph(glyph_msg)

# Sign and verify messages
key = b"secret_key"
signed_msg = sign(msg, key)
is_valid = verify(signed_msg, key)
```

### Network Transport with Enhanced Features
```python
from aicl import run_server, run_client

# Server with TLS and error handling
def handler(msg):
    # Process incoming message
    response = process_message(msg)
    return [response] if response else []

run_server(
    "127.0.0.1", 
    5555, 
    handler,
    use_tls=True,
    certfile="server.crt",
    keyfile="server.key"
)

# Client
messages = [msg1, msg2, msg3]
for response in run_client("127.0.0.1", 5555, messages):
    print(f"Received: {response}")
```

### Advanced Logging and Metrics
```python
from aicl import AICLLogger

# Create logger with compression
logger = AICLLogger("artifacts/conversations", compress=True)

# Log messages with latency tracking
start_time = time.time()
# ... process message ...
latency_ms = (time.time() - start_time) * 1000
logger.log_message(msg, latency_ms)

# Get metrics
metrics = logger.get_metrics()
print(f"Total messages: {metrics['total_messages']}")
print(f"Average latency: {metrics['avg_latency_ms']}ms")
```

### Configuration Management
```python
from aicl import config

# Access configuration values
host = config.get("host", "127.0.0.1")
port = config.get("port", 5555)

# Set configuration values
config.set("max_tokens", 2048)

# Save configuration
config.save_config("config.json")
```

### Streaming Large Payloads
```python
from aicl import split_large_content, create_stream_message, sign

# Split large content into chunks
content = "Very large content..." * 1000
chunks = split_large_content(content, chunk_size=512)

# Create streaming message
stream_msg = create_stream_message(
    frm="sender",
    to="receiver",
    topic="large_content",
    chunks=chunks
)

# Sign the message
signed_stream_msg = sign(stream_msg, b"secret_key")
```

### Message Routing
```python
from aicl import router, broker

# Add route for specific topic
def handle_distillation(msg):
    # Process distillation message
    return [response_msg]

router.add_route("distillation", handle_distillation)

# Subscribe to topic
broker.subscribe("distillation", connection)

# Route message
responses = router.route_message(msg)
```

### Security Features
```python
from aicl import validate_message, rate_limit_check

# Validate incoming messages
is_valid, error = validate_message(msg, policy={
    "max_tokens": 1024,
    "max_latency_ms": 5000,
    "max_payload_size": 50000
})

if not is_valid:
    print(f"Message validation failed: {error}")

# Rate limiting
if not rate_limit_check(sender_id, max_requests_per_minute=60):
    print("Rate limit exceeded")
```

## Message Types

- `ask`: Request information or action
- `answer`: Response to an ask
- `inform`: Share information
- `plan`: Share execution plan
- `tool_call`: Request tool execution
- `tool_result`: Return tool execution result
- `ping`/`pong`: Liveness check
- `error`: Report an error
- `ack`: Acknowledge receipt
- `stream`: Streaming response (for large payloads)

## Payload Types

1. **Text**: `{lang, fmt, content}`
2. **Embeddings**: `{model, dtype, shape, b64}`
3. **Logits**: `{topk: [{"tok":"...", "p":0.12}, ...], "temperature":2.0}`
4. **Tools**: `{name, args}` for calls; `{name, ok, result|error}` for results
5. **Stream Chunks**: `{sequence, data, final}`

## Safety Features

- **Quota enforcement**: `limits.tokens`, `limits.latency_ms`
- **Policy headers**: Configurable limits and constraints
- **Message signing**: HMAC-SHA256 signatures for integrity
- **Replay protection**: Message ID tracking (placeholder)
- **Rate limiting**: Sliding window rate limiting per sender
- **Validation**: Comprehensive message structure and content validation
- **Sanitization**: Removal of sensitive fields from messages
- **TLS support**: Encrypted communication channels

## Running Demos

```bash
# Run the basic AICL demo (teacher and student processes)
python teacher_demo.py &
python student_demo.py

# Run the comprehensive example with all features
python comprehensive_example.py

# Replay a conversation log
python scripts/aicl_replay.py --log artifacts/conversations/last.jsonl
```

## Integration with LLM Distillation

AICL is designed to work seamlessly with knowledge distillation workflows:

1. Teacher models can send logits with `logits:topk` payloads
2. Student models can compute live KD losses using received logits
3. Conversations can be logged for analysis and replay
4. Security features protect against malformed or malicious messages
5. Metrics tracking provides insights into distillation performance
6. Rate limiting prevents resource exhaustion during training
7. Streaming support handles large model outputs
8. Configuration management enables flexible deployment

## API Reference

### Core Functions
- `new_msg(frm, to, act, payload, ...)`: Create a new AICL message
- `new_stream_msg(frm, to, topic, chunks, ...)`: Create a streaming message
- `new_error_msg(frm, to, error, ...)`: Create an error message
- `aicl_core(msg)`: Serialize message to JSON
- `to_glyph(msg)`: Convert message to compact glyph format
- `from_glyph(glyph_str)`: Parse glyph format back to message
- `sign(msg, key)`: Sign message with HMAC
- `verify(msg, key)`: Verify message signature

### Transport Functions
- `run_server(host, port, handler, ...)`: Start AICL server
- `run_client(host, port, msgs_iter, ...)`: Send messages to server
- `AICLConnection`: Persistent bidirectional connection class

### Logging and Metrics
- `AICLLogger`: Conversation logging with metrics tracking
- `AICLReplayer`: Conversation log replay utility

### Configuration
- `config`: Global configuration instance
- `AICLConfig`: Configuration management class

### Streaming
- `split_large_content(content, chunk_size)`: Split content into chunks
- `create_stream_message(frm, to, topic, chunks, ...)`: Create streaming message
- `StreamChunk`: Stream chunk representation

### Routing
- `router`: Global message router
- `broker`: Global message broker
- `MessageRouter`: Message routing class
- `MessageBroker`: Message broker class

### Security Functions
- `validate_message(msg, policy)`: Validate message structure and policy
- `rate_limit_check(sender_id, ...)`: Check rate limits
- `verify_signature(msg, key)`: Verify message signature
- `sanitize_message(msg)`: Remove sensitive fields

### Benchmarking
- `AICLBenchmark`: Synchronous benchmarking utilities
- `AsyncAICLBenchmark`: Asynchronous benchmarking utilities

## Error Handling

AICL provides comprehensive error handling through exception classes:
- `TransportError`: Base transport errors
- `ConnectionError`: Connection-related issues
- `MessageError`: Message parsing or validation errors
- `AsyncTransportError`: Async transport errors

All functions properly handle timeouts, network errors, and malformed data.