# docs_validate.ps1
# Validates all markdown files for broken relative links and missing anchors
# Usage: .\scripts\docs_validate.ps1

$ErrorActionPreference = "Stop"
$root = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$mds  = Get-ChildItem $root -Recurse -Filter *.md | Where-Object { $_.FullName -notmatch '\\node_modules\\|\\venv\\|\\__pycache__\\|\\.git\\' }
$errors = @()

Write-Host "ðŸ” Validating documentation links and anchors..." -ForegroundColor Cyan
Write-Host "Found $($mds.Count) markdown files to check`n" -ForegroundColor Gray

foreach ($md in $mds) {
  $relativePath = $md.FullName.Replace($root, "").TrimStart('\')
  Write-Host "  Checking: $relativePath" -ForegroundColor Gray
  
  $content = Get-Content $md.FullName -Raw
  $links = Select-String -InputObject $content -Pattern '\]\((?<url>(?!http)(?!mailto:)[^)#]+)(?<hash>#.*?)?\)' -AllMatches
  
  foreach ($m in $links.Matches) {
    $rel = $m.Groups['url'].Value.Trim()
    $hash = $m.Groups['hash'].Value
    $target = Join-Path $md.DirectoryName $rel
    
    # Check if file exists
    if (-not (Test-Path $target)) { 
      $errors += "Missing file: $($md.Name) -> $rel"
      continue 
    }
    
    # Check if anchor exists (if specified)
    if ($hash) {
      $slug = ($hash.TrimStart('#') -replace '\s','-').ToLower()
      $t = Get-Content $target -Raw
      
      # Try exact heading match first
      $exactMatch = $t -match "(?im)^#+\s+$($hash.TrimStart('#').Replace('[','\[').Replace(']','\]'))$"
      
      # Fall back to slug-based search (GitHub-style anchors)
      if (-not $exactMatch -and $t.ToLower() -notmatch [regex]::Escape($slug)) { 
        $errors += "Missing anchor: $($md.Name) -> $rel$hash" 
      }
    }
  }
}

Write-Host ""

if ($errors) {
  Write-Host "[ERROR] Found $($errors.Count) documentation issue(s):" -ForegroundColor Red
  $errors | Sort-Object | ForEach-Object { Write-Host "  * $_" -ForegroundColor Red }
  exit 1 
}

$fileCount = $mds.Count
$message = "[OK] All relative links and anchors OK (" + $fileCount + " files checked)"
Write-Host $message -ForegroundColor Green
exit 0

