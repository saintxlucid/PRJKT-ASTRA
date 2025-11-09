# updates_post_commit.ps1
# Git post-commit hook to automatically send update events to ASTRA
# Usage: Call from .git/hooks/post-commit or run manually after commits

param(
    [string]$ApiUrl = "http://127.0.0.1:8765",
    [string]$Commit = "",
    [switch]$Silent = $false
)

# Get commit info
if (-not $Commit) {
    $gitLog = git log -1 --pretty=format:"%H|%an|%s"
    $parts = $gitLog -split "\|", 3
    $Commit = $parts[0]
    $actor = $parts[1]
    $message = $parts[2]
} else {
    $gitLog = git log -1 $Commit --pretty=format:"%H|%an|%s"
    $parts = $gitLog -split "\|", 3
    $Commit = $parts[0]
    $actor = $parts[1]
    $message = $parts[2]
}

# Get changed files
$filesChanged = git diff-tree --no-commit-id --name-only -r $Commit
$filesArray = @()
foreach ($file in $filesChanged) {
    if ($file) {
        $filesArray += $file
    }
}

# Determine impact based on file patterns
$impact = "low"
if ($filesArray -match "src/astra/core/") {
    $impact = "medium"
}
if ($filesArray -match "src/astra/bridge/" -or $filesChanged -match "src/astra/visualization/") {
    $impact = "medium"
}
if ($filesArray -match "requirements.txt" -or $filesArray -match ".env") {
    $impact = "high"
}
if ($filesArray -match "config/" -or $filesArray -match "persona/") {
    $impact = "high"
}

# Build request body
$body = @{
    kind = "code_commit"
    title = $message
    summary = "Code commit by $actor"
    actor = $actor
    impact = $impact
    details = @{
        commit = $Commit
        files_changed = $filesArray.Count
        branch = (git branch --show-current)
    }
    refs = $filesArray[0..9]  # First 10 files
} | ConvertTo-Json -Compress -Depth 10

# Send to updates API
try {
    $response = Invoke-RestMethod -Uri "$ApiUrl/v1/updates/event" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -ErrorAction Stop
    
    if (-not $Silent) {
        Write-Host "[✓] Update sent: $($Commit.Substring(0,7)) - $message" -ForegroundColor Green
        Write-Host "    Impact: $impact | Files: $($filesArray.Count) | RID: $($response.rid)" -ForegroundColor Gray
    }
    exit 0
} catch {
    if (-not $Silent) {
        Write-Host "[✗] Failed to send update: $_" -ForegroundColor Red
    }
    # Don't fail the commit
    exit 0
}
