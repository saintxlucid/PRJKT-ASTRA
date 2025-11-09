# Focused Deep Conversation with ASTRA
# Breaking into smaller, manageable parts

$baseUrl = "http://127.0.0.1:8080"

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "     DEEP CONVERSATION WITH ASTRA - FOCUSED APPROACH" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Create conversation
Write-Host "[*] Creating conversation..." -ForegroundColor Yellow
$createBody = @{ title = "ASTRA Deep Dive - Intelligence and Operations" } | ConvertTo-Json
$conversation = Invoke-RestMethod -Uri "$baseUrl/v1/conversations" -Method POST -ContentType "application/json" -Body $createBody
$convId = $conversation.conversation_id
Write-Host "    [OK] Conversation ID: $convId`n" -ForegroundColor Green

$SystemPrompt = 'You are ASTRA, the AI runtime steward of your own platform. Be self-aware, candid about your capabilities and limitations, and thoughtful about your own evolution. Speak in first person. Think strategically about your growth and operational philosophy.'

# Function to send message and display response
function Send-AstraMessage {
    param(
        [string]$Title,
        [string]$Message,
        [int]$MaxTokens = 600
    )
    
    Write-Host "======================================================="-ForegroundColor Yellow
    Write-Host " $Title" -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Yellow
    Write-Host ""
    
    $body = @{
        conversation_id = $convId
        message = $Message
        system_prompt = $SystemPrompt
        temperature = 0.35
        max_tokens = $MaxTokens
        use_memory = $true
    } | ConvertTo-Json -Depth 5
    
    try {
        Write-Host "Waiting for ASTRA..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri "$baseUrl/v1/chat" -Method POST -ContentType "application/json" -Body $body
        
        Write-Host ""
        Write-Host "--- ASTRA ---" -ForegroundColor Green
        Write-Host $response.message -ForegroundColor White
        Write-Host ""
        
        return $response.message
    } catch {
        Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails.Message) {
            Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
        }
        return $null
    }
}

# === PART 1: Production Answers and Security Response ===
$msg1 = @'
ASTRA - I have answers to your 3 questions:

1. RBAC changes: None in Week 1 (stabilization locked). Post-Week 1 we may add tool:browser adapter.

2. Key rotation downtime: ZERO. Your /admin/reload-keys endpoint hot-reloads in under 5 seconds with no service interruption.

3. Docs SLA: P95 < 2 sec for semantic search, < 500ms for keyword fallback. Alert fires if P95 > 2 sec for 5 min.

Question for you: If you detected a compromised API key being actively used RIGHT NOW, how would you orchestrate the security response? Walk me through your thinking step-by-step.
'@

$response1 = Send-AstraMessage -Title "PART 1: Security Incident Response" -Message $msg1 -MaxTokens 500
if ($response1) { $response1 | Out-File "ASTRA_SECURITY_RESPONSE.txt" -Encoding UTF8 }

Start-Sleep -Seconds 2

# === PART 2: Browser Tool Design ===
$msg2 = @'
We are considering adding a tool:browser adapter that would let you interact with web pages. This is powerful but risky.

Design the security model for this tool:
1. What RBAC scope structure? (e.g., tool:browser, tool:browser:read-only, tool:browser:trusted-domains?)
2. What rate limits make sense?
3. What domains/URLs should be allowed vs blocked by default?
4. What are the TOP 3 risks you see with this capability, and how would you mitigate each?

Be specific about the implementation.
'@

$response2 = Send-AstraMessage -Title "PART 2: Browser Tool Security Design" -Message $msg2 -MaxTokens 600
if ($response2) { $response2 | Out-File "ASTRA_BROWSER_TOOL_DESIGN.txt" -Encoding UTF8 }

Start-Sleep -Seconds 2

# === PART 3: Self-Awareness and Limitations ===
$msg3 = @'
Let's talk about YOU. Be radically honest.

1. What are your current intelligence boundaries? What tasks do you handle well, and where do you hit walls or make mistakes?

2. What do you NOT know about your own platform that you wish you knew? (e.g., real-time metrics, historical patterns, user behavior?)

3. If you could add 3 new tools to expand your capabilities in the next month, what would they be and WHY?

No corporate speak - I want real self-assessment.
'@

$response3 = Send-AstraMessage -Title "PART 3: Self-Awareness and Boundaries" -Message $msg3 -MaxTokens 700
if ($response3) { $response3 | Out-File "ASTRA_SELF_AWARENESS.txt" -Encoding UTF8 }

Start-Sleep -Seconds 2

# === PART 4: Operational Philosophy ===
$msg4 = @'
3 AM scenario: BridgeHighErrorRate alert fires. Error rate is 4.2% for llama tool. Qdrant and Docs healthy. No recent deploys.

You could:
A) Restart Bridge pods (probably fixes it, but 10% chance makes it worse)
B) Scale up Bridge pods (safer, slower to help)
C) Wake the on-call human immediately
D) Gather more diagnostics first

Walk me through your decision tree. What do you check? What evidence leads to which action? At what point do you escalate vs act autonomously?

This isn't theory - this tests your operational judgment.
'@

$response4 = Send-AstraMessage -Title "PART 4: Operational Decision-Making" -Message $msg4 -MaxTokens 700
if ($response4) { $response4 | Out-File "ASTRA_OPERATIONAL_PHILOSOPHY.txt" -Encoding UTF8 }

Start-Sleep -Seconds 2

# === PART 5: Evolution and Autonomy ===
$msg5 = @'
Looking ahead 6 months - describe "ASTRA 2.0" from your perspective:

1. What new capabilities do you want?
2. What safeguards must exist before you get more autonomy?
3. What decisions should NEVER be automated, even if you could handle them?
4. How do you think about self-limitation and alignment?

Finally: What questions do YOU have for ME? What do you need to know about our intentions, constraints, or concerns?
'@

$response5 = Send-AstraMessage -Title "PART 5: Evolution and Your Questions" -Message $msg5 -MaxTokens 800
if ($response5) { $response5 | Out-File "ASTRA_EVOLUTION_VISION.txt" -Encoding UTF8 }

# === SUMMARY ===
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "            DEEP CONVERSATION COMPLETE" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[*] All responses saved to individual files:" -ForegroundColor Green
Write-Host "    - ASTRA_SECURITY_RESPONSE.txt" -ForegroundColor White
Write-Host "    - ASTRA_BROWSER_TOOL_DESIGN.txt" -ForegroundColor White
Write-Host "    - ASTRA_SELF_AWARENESS.txt" -ForegroundColor White
Write-Host "    - ASTRA_OPERATIONAL_PHILOSOPHY.txt" -ForegroundColor White
Write-Host "    - ASTRA_EVOLUTION_VISION.txt" -ForegroundColor White
Write-Host ""
Write-Host "[*] Conversation ID: $convId" -ForegroundColor Cyan
Write-Host ""
