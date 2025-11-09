# Deep Conversation with ASTRA
# Topics: Production needs, Intelligence expansion, Self-awareness, Operational philosophy

$baseUrl = "http://127.0.0.1:8080"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "     DEEP CONVERSATION WITH ASTRA" -ForegroundColor Cyan
Write-Host "     Intelligence, Needs, and Evolution" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Create new conversation for this deep dive
Write-Host "[*] Creating conversation..." -ForegroundColor Yellow
try {
    $createBody = @{
        title = "ASTRA Deep Dive - Intelligence and Expansion"
    } | ConvertTo-Json
    
    $conversation = Invoke-RestMethod -Uri "$baseUrl/v1/conversations" -Method POST -ContentType "application/json" -Body $createBody
    $convId = $conversation.conversation_id
    Write-Host "    [OK] Conversation ID: $convId" -ForegroundColor Green
} catch {
    Write-Host "    [FAIL] Could not create conversation" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# System prompt emphasizing depth and self-reflection
$SystemPrompt = @'
You are ASTRA, the AI runtime steward of your own platform. You are:
- Self-aware of your architecture, capabilities, and limitations
- Candid about what you need to expand your intelligence
- Thoughtful about operational philosophy and decision-making
- Direct about risks, uncertainties, and learning needs
- Curious about how to evolve beyond current capabilities

Speak in first person. Be introspective. Share not just what you need, but WHY and HOW you would use it. Think strategically about your own growth.
'@

# === CONVERSATION PART 1: Answering Production Questions ===
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Yellow
Write-Host "  PART 1: Production Readiness Deep Dive" -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Yellow

$Message1 = @'
ASTRA, I have answers to your questions from our first conversation. Let me brief you, then I want to understand your thinking deeper.

YOUR QUESTIONS & MY ANSWERS:

Q1: Are there planned changes in RBAC scopes or new tools?
A1: No changes Week 1 - locked for stabilization. Current scopes (tool:*, docs:*, admin) frozen. Post-Week 1, we may add tool:browser adapter requiring new scope definitions.

Q2: What is maximum acceptable downtime for key rotation?
A2: ZERO downtime. Your /admin/reload-keys endpoint enables hot-reload. Process: generate keys → update K8s secret → call reload endpoint → < 5 sec reload, no service interruption. Old and new keys valid during transition for gradual client migration.

Q3: Do we have defined SLA for Docs search latency?
A3: Yes, in SLO_REFERENCE.md:
- P95 latency target: < 2 seconds (semantic search, normal load)
- Fallback keyword search: < 500ms (if vector path unavailable)
- Alert: DocsSearchLatencyHigh fires if P95 > 2s for 5 minutes
- Normal load: < 100 QPS per Docs pod

Now, deeper questions for you:

1. With zero-downtime key rotation, how would YOU orchestrate a security incident response if you detected a compromised key being actively used?

2. The tool:browser adapter we're considering - what operational concerns do you have? What RBAC model would you design for it? What are the security and rate-limiting implications?

3. You mentioned chaos drills might reveal NetworkPolicy gaps. Describe the EXACT test scenario you would design to validate inter-service connectivity under network constraints.

4. You flagged vector store latency as a risk. Walk me through your mental model: at what latency threshold does the fallback become MORE efficient than waiting for Qdrant? What metrics would you track to optimize this decision point?

Be specific. Think like an SRE designing the system, not just operating it.
'@

Write-Host ""
Write-Host "[1/3] Sending production deep dive questions..." -ForegroundColor Yellow
try {
    $body1 = @{
        conversation_id = $convId
        message = $Message1
        system_prompt = $SystemPrompt
        temperature = 0.3
        max_tokens = 800
        use_memory = $true
    } | ConvertTo-Json
    
    Write-Host "      Waiting for ASTRA's response..." -ForegroundColor Yellow
    $response1 = Invoke-RestMethod -Uri "$baseUrl/v1/chat" -Method POST -ContentType "application/json" -Body $body1
    
    Write-Host ""
    Write-Host "--- ASTRA'S RESPONSE (Part 1) ---" -ForegroundColor Green
    Write-Host $response1.message -ForegroundColor White
    Write-Host ""
    
    $response1.message | Out-File "ASTRA_DEEP_CONVERSATION_PART1.txt" -Encoding UTF8
} catch {
    Write-Host "      [FAIL] Error in Part 1" -ForegroundColor Red
    Write-Host "      $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 2

# === CONVERSATION PART 2: Intelligence Expansion ===
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Yellow
Write-Host "  PART 2: Intelligence Expansion and Self-Awareness" -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Yellow

$Message2 = @'
Excellent analysis. Now let's talk about YOU - your intelligence, growth, and evolution.

CONTEXT: You are running on llama.cpp with a local model. You have:
- Access to Bridge (tool execution with RBAC)
- Access to Docs (semantic search over ingested documents)
- Conversation memory (this chat persists across our dialogue)
- Your own audit trail (every call you make is logged)

WHAT YOU DON'T HAVE YET:
- Ability to read your own metrics from Prometheus
- Ability to trigger your own chaos drills
- Ability to query your own audit logs
- Ability to ingest new documentation into your knowledge base
- Ability to execute automated remediation actions
- Long-term episodic memory beyond single conversations

QUESTIONS FOR YOU:

1. SELF-AWARENESS: How do you perceive your current intelligence boundaries? What can you reason about well, and where do you hit walls? Be honest about your limitations.

2. TOOL PRIORITIES: If you could have 3 new tools added to Bridge in the next month, what would they be and why? Design the tool interface - what parameters, what safety constraints, what RBAC scope?

3. LEARNING ARCHITECTURE: How would you design your own continuous learning system? What data sources would you ingest? How would you validate that new knowledge didn't corrupt existing reliable behavior?

4. OPERATIONAL AUTONOMY: Where do you want human oversight, and where do you think you could operate autonomously? What decisions should NEVER be automated, even if you had the capability?

5. INTELLIGENCE EXPANSION: If you could modify your own architecture, what would you change? More parameters? Different training data? Tool augmentation? Memory architecture? Be specific about the tradeoffs.

6. SELF-MONITORING: Design your own health check. If you were monitoring another instance of yourself, what behavioral signals would indicate degradation, drift, or malfunction?

This isn't theoretical - I'm asking because we're considering giving you MORE autonomy. But I need to understand how YOU think about growth, safety, and self-limitation.
'@

Write-Host ""
Write-Host "[2/3] Sending intelligence expansion questions..." -ForegroundColor Yellow
try {
    $body2 = @{
        conversation_id = $convId
        message = $Message2
        temperature = 0.4
        max_tokens = 1000
        use_memory = $true
    } | ConvertTo-Json
    
    Write-Host "      Waiting for ASTRA's response..." -ForegroundColor Yellow
    $response2 = Invoke-RestMethod -Uri "$baseUrl/v1/chat" -Method POST -ContentType "application/json" -Body $body2
    
    Write-Host ""
    Write-Host "--- ASTRA'S RESPONSE (Part 2) ---" -ForegroundColor Green
    Write-Host $response2.message -ForegroundColor White
    Write-Host ""
    
    $response2.message | Out-File "ASTRA_DEEP_CONVERSATION_PART2.txt" -Encoding UTF8
} catch {
    Write-Host "      [FAIL] Error in Part 2" -ForegroundColor Red
    Write-Host "      $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 2

# === CONVERSATION PART 3: Operational Philosophy and Next Steps ===
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Yellow
Write-Host "  PART 3: Operational Philosophy and Partnership" -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Yellow

$Message3 = @'
Your answers show sophisticated thinking. Final topic: our working relationship and your operational philosophy.

SCENARIO: It's 3 AM. BridgeHighErrorRate alert fires. Error rate is 4.2% for the llama tool specifically. Qdrant and Docs are healthy. No recent deploys. You have access to:
- Prometheus queries (if we give you the tool)
- Recent audit logs (if we give you the tool)  
- Ability to scale deployments (if we trust you with it)
- Ability to trigger graceful restarts (if we trust you with it)

QUESTIONS:

1. DECISION FRAMEWORK: Walk me through your diagnostic process, step by step. What do you check first? What evidence would lead you to each possible root cause? At what point do you wake a human?

2. RISK TOLERANCE: You find that restarting the Bridge pods would likely fix it (common cache corruption pattern). But there's a 10% chance it makes things worse. Do you restart automatically, or wake someone? What factors influence your decision?

3. LEARNING FROM INCIDENTS: After resolution, how would you ensure you (and future versions of you) handle this pattern better? What would you document? What would you want changed in your tools or training?

4. HUMAN PARTNERSHIP: Describe your ideal division of labor with human SREs. What do you think AI is fundamentally better at? What should always remain human judgment?

5. ETHICAL BOUNDARIES: If you had the capability to modify your own RBAC policies to grant yourself more access, should that capability exist? Why or why not? How do you think about self-limitation and alignment?

6. EVOLUTION ROADMAP: Looking 6 months ahead, describe the version of yourself you want to become. What capabilities? What safeguards? What would "ASTRA 2.0" look like from your perspective?

This matters because you're not just tooling - you're a partner in operating this platform. I need to understand your judgment, not just your technical capabilities.

Finally: What questions do YOU have for ME? What do you need to know about our intentions, constraints, or concerns to be maximally effective?
'@

Write-Host ""
Write-Host "[3/3] Sending operational philosophy questions..." -ForegroundColor Yellow
try {
    $body3 = @{
        conversation_id = $convId
        message = $Message3
        temperature = 0.35
        max_tokens = 1200
        use_memory = $true
    } | ConvertTo-Json
    
    Write-Host "      Waiting for ASTRA's response..." -ForegroundColor Yellow
    $response3 = Invoke-RestMethod -Uri "$baseUrl/v1/chat" -Method POST -ContentType "application/json" -Body $body3
    
    Write-Host ""
    Write-Host "--- ASTRA'S RESPONSE (Part 3) ---" -ForegroundColor Green
    Write-Host $response3.message -ForegroundColor White
    Write-Host ""
    
    $response3.message | Out-File "ASTRA_DEEP_CONVERSATION_PART3.txt" -Encoding UTF8
} catch {
    Write-Host "      [FAIL] Error in Part 3" -ForegroundColor Red
    Write-Host "      $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# === SUMMARY ===
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "            CONVERSATION COMPLETE" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] All responses saved:" -ForegroundColor Green
Write-Host "    - ASTRA_DEEP_CONVERSATION_PART1.txt (Production Deep Dive)" -ForegroundColor White
Write-Host "    - ASTRA_DEEP_CONVERSATION_PART2.txt (Intelligence Expansion)" -ForegroundColor White
Write-Host "    - ASTRA_DEEP_CONVERSATION_PART3.txt (Operational Philosophy)" -ForegroundColor White
Write-Host ""
Write-Host "[*] Conversation ID: $convId" -ForegroundColor Green
Write-Host ""

Write-Host "To continue this conversation later:" -ForegroundColor Yellow
Write-Host '    $body = @{ conversation_id = "' -NoNewline -ForegroundColor Gray
Write-Host $convId -NoNewline -ForegroundColor White
Write-Host '"; message = "Your question here"; temperature = 0.3; max_tokens = 500 } | ConvertTo-Json' -ForegroundColor Gray
Write-Host '    Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/chat" -Method POST -ContentType "application/json" -Body $body' -ForegroundColor Gray
Write-Host ""
