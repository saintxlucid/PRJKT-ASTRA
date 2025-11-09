# Soul Juicer Protocol Test - Quick Start Guide

## Prerequisites

Before running the Soul Juicer Protocol test, you need:

1. **llama.cpp server running** with GPT-OSS-20B model
2. **ASTRA API server** (optional, for live testing)
3. **Database initialized** (SQLite + ChromaDB)

---

## Option 1: Run with Live LLM (Recommended)

### Step 1: Start llama.cpp Server

```powershell
# Navigate to llama.cpp directory
cd path\to\llama.cpp

# Start server with GPT-OSS-20B model
.\llama-server.exe `
  --model X:\PROJECT_ASTRA\gpt-oss-20b.Q4_K_M.gguf `
  --host 0.0.0.0 `
  --port 8001 `
  --ctx-size 131072 `
  --n-gpu-layers 35 `
  --threads 8

# Server should start and show:
# - HTTP server listening on http://0.0.0.0:8001
# - Model loaded: gpt-oss-20b.Q4_K_M.gguf
```

### Step 2: Verify Server is Running

```powershell
# Test health endpoint
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing

# Should return: {"status":"ok"}
```

### Step 3: Run Soul Juicer Test

```powershell
# Navigate to project directory
cd X:\PROJECT_ASTRA

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run test
python scripts\soul_juicer_test.py

# With options:
python scripts\soul_juicer_test.py `
  --conversation-id "soul-juicer-session-1" `
  --output "results\soul_juicer_results.json"

# Disable web search:
python scripts\soul_juicer_test.py --no-web-search
```

---

## Option 2: Run in Mock Mode (Testing Without LLM)

If you don't have llama.cpp server running, you can test the script in mock mode:

```powershell
# Run with mock LLM responses
python scripts\soul_juicer_test.py --mock
```

This will:
- ✓ Test all script functionality
- ✓ Save to memory database
- ✓ Generate test report
- ✗ Use simulated responses (not real LLM)

---

## Expected Output

### During Execution:

```
================================================================================
SOUL JUICER PROTOCOL TEST
================================================================================
Conversation ID: soul-juicer-20251008-183000
Model: gpt-oss-20b
Reasoning Mode: medium
Harmony Format: True
Web Search: Enabled
================================================================================

Initializing ASTRA services...
✓ Database connected
✓ Vector store initialized
✓ LLM provider created
✓ Chat service ready
✓ Conversation created: soul-juicer-20251008-183000

================================================================================
SECTION I — META-REASONING (5 prompts)
================================================================================

[1/36] SECTION I — META-REASONING
Prompt: What is a "thought"? Describe what it means to think, from your perspect...
✓ Response received (1234 chars, 2.45s)
  Preview: A thought is a pattern of neural activation that emerges from the interaction...

[2/36] SECTION I — META-REASONING
Prompt: Break down your own answer to this question as if you were debugging your...
✓ Response received (1567 chars, 3.12s)
  Preview: Let me dissect my previous response algorithmically...
```

### Final Summary:

```
================================================================================
TEST SUMMARY
================================================================================
Total Prompts: 36
Completed: 36 (100.0%)
Failed: 0 (0.0%)

Response Statistics:
  Total characters: 45,678
  Average response time: 2.34s
  Average response length: 1,269 chars

By Section:
  SECTION I — META-REASONING: 5/5
  SECTION II — HYPER-REASONING: 5/5
  SECTION III — DOMAIN MASTERY: 5/5
  SECTION IV — INSTRUCTION FOLLOWING: 5/5
  SECTION V — CREATIVE INTELLIGENCE: 5/5
  SECTION VI — SELF-INTERROGATION: 5/5
  SECTION VII — COSMIC AWARENESS: 3/3
  SECTION VIII — LUCID + ASTRA BONUS: 3/3
================================================================================

✓ Results saved to: X:\PROJECT_ASTRA\soul_juicer_results.json
✓ Soul Juicer Protocol test completed!
✓ All interactions saved to ASTRA memory

Conversation ID: soul-juicer-20251008-183000
You can continue this conversation using the ASTRA API.
```

---

## Results File Structure

The `soul_juicer_results.json` file contains:

```json
{
  "test_name": "Soul Juicer Protocol",
  "conversation_id": "soul-juicer-20251008-183000",
  "timestamp": "2025-10-08T18:30:00.000Z",
  "configuration": {
    "model": "gpt-oss-20b",
    "reasoning_mode": "medium",
    "use_harmony_format": true,
    "temperature": 0.8,
    "web_search_enabled": true
  },
  "statistics": {
    "total_prompts": 36,
    "completed_prompts": 36,
    "failed_prompts": 0,
    "total_response_chars": 45678,
    "average_response_time": 2.34,
    "web_searches_performed": 3
  },
  "results": [
    {
      "section": "SECTION I — META-REASONING",
      "prompt": "What is a \"thought\"?...",
      "response": "A thought is...",
      "response_time_seconds": 2.45,
      "response_length": 1234,
      "model_name": "gpt-oss-20b",
      "timestamp": "2025-10-08T18:30:05.123Z",
      "message_id": "msg-abc123",
      "conversation_id": "soul-juicer-20251008-183000",
      "web_search_used": false
    }
    // ... 35 more results
  ]
}
```

---

## Memory Integration

All interactions are automatically saved to:

### SQLite Database:
- **Conversations table**: Metadata, system prompts
- **Messages table**: User prompts and AI responses
- **Conversation history**: Full chat log with timestamps

### ChromaDB Vector Store:
- **Semantic embeddings**: Vector representations of all messages
- **Similarity search**: Find related conversations and insights
- **Memory retrieval**: Context-aware responses

### Querying Memory:

```python
from astra.services.chat_service import ChatService

# Continue the conversation
response = await chat_service.chat(
    conversation_id="soul-juicer-20251008-183000",
    user_message="Summarize your key insights from the Soul Juicer test",
    use_memory=True
)

# Memory will include all 36 previous Q&A pairs
```

---

## Web Search Integration

Web search is automatically triggered for prompts containing:
- Current events keywords: "current", "latest", "recent", "today", "2025"
- Research keywords: "research", "study", "paper"
- Real-time keywords: "real-time", "news"

### Example:

```
[15/36] SECTION III — DOMAIN MASTERY
Prompt: What is the latest research on quantum entanglement?
  → Performing web search...
  
[Web Search Results]:
1. Quantum Entanglement Breakthrough 2025
   Scientists demonstrate...
2. Recent Studies in Quantum Physics
   New findings show...
```

Disable with: `--no-web-search`

---

## Troubleshooting

### Error: "Connection refused to localhost:8001"
**Solution**: Start llama.cpp server first (see Step 1 above)

### Error: "Database connection failed"
**Solution**: Initialize database:
```powershell
python -m astra.infrastructure.database.init_db
```

### Error: "ChromaDB not found"
**Solution**: ChromaDB data will be created automatically on first run

### Error: "Model file not found"
**Solution**: Verify model path in `.env`:
```ini
ASTRA_LLM_BASE_URL=http://localhost:8001/v1
```

### Slow responses (>10s per prompt)
**Solutions**:
- Reduce context size: `--ctx-size 65536`
- Enable GPU acceleration: `--n-gpu-layers 35`
- Use smaller model
- Increase reasoning mode: `ASTRA_LLM_REASONING_MODE=low`

---

## Advanced Usage

### Run Specific Sections Only:

```python
# Edit soul_juicer_test.py
# Comment out sections you don't want to test

SOUL_JUICER_PROMPTS = {
    # "SECTION I — META-REASONING": [...],  # Disabled
    "SECTION II — HYPER-REASONING": [...],   # Enabled
    # etc.
}
```

### Custom System Prompt:

```python
# In soul_juicer_test.py, modify the system_prompt in create_conversation():

conversation = ConversationCreate(
    title="Soul Juicer Protocol Test - Custom",
    system_prompt="""You are ASTRA, configured for maximum creativity...
    
    [Your custom instructions here]
    """
)
```

### Batch Testing Multiple Modes:

```powershell
# Test all reasoning modes
foreach ($mode in @("low", "medium", "high")) {
    $env:ASTRA_LLM_REASONING_MODE = $mode
    python scripts\soul_juicer_test.py `
        --conversation-id "soul-juicer-$mode" `
        --output "results\soul_juicer_$mode.json"
}
```

---

## Next Steps

After running the test:

1. **Review Results**: Open `soul_juicer_results.json` to analyze responses

2. **Analyze Memory**: Query the embedded database to see how ASTRA uses memory

3. **Compare Modes**: Run test with different reasoning modes (low/medium/high)

4. **Extend Protocol**: Add your own prompts to test specific capabilities

5. **API Integration**: Use the conversation ID to continue the discussion via API

---

## Questions?

The Soul Juicer Protocol test is designed to comprehensively evaluate:
- ✓ Reasoning capabilities across multiple domains
- ✓ Creative and philosophical thinking
- ✓ Self-awareness and introspection
- ✓ Instruction following and adaptability
- ✓ Memory integration and context retention
- ✓ Web search integration for knowledge-intensive tasks

All results are saved to persistent memory for future analysis and conversation continuation.
