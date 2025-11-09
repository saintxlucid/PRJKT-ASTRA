# scripts/docs_validate.ps1
# Validates markdown files for broken relative links

param([string]$Root = (Resolve-Path ".").Path)

$mds = Get-ChildItem $Root -Recurse -Filter *.md |
  Where-Object {
    $_.FullName -notmatch '\\(node_modules|\.git|\.venv|venv|__pycache__|htmlcov|dist|build|site|_site|third_party|astra-local|hf_cache|\.hf_cache|\.cache)\\'
  }

$errors = @()
$checkedCount = 0

foreach ($md in $mds) {
  try {
    $content = Get-Content $md.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    
    $checkedCount++
    $linkPattern = '\[([^\]]+)\]\(([^)]+)\)'
    $matches = [regex]::Matches($content, $linkPattern)
    
    foreach ($m in $matches) {
      $link = $m.Groups[2].Value
      if ($link -match '^https?://') { continue }
      if ($link -match '^mailto:') { continue }
      if ($link -match '^#') { continue }
      
      $parts = $link -split '#'
      $targetPath = $parts[0]
      if ($targetPath) {
        $resolved = Join-Path (Split-Path $md.FullName) $targetPath
        if (-not (Test-Path $resolved)) {
          $relPath = $md.FullName.Replace("$Root\", "")
          $errors += "${relPath}: broken link -> $link"
        }
      }
    }
  }
  catch {
    Write-Host "  [WARN] Could not process $($md.Name)" -ForegroundColor Yellow
  }
}

if ($errors) {
  Write-Host "[ERROR] Found $($errors.Count) documentation issues:" -ForegroundColor Red
  $errors | Sort-Object | ForEach-Object { Write-Host "  * $_" -ForegroundColor Red }
  exit 1
}

Write-Host "[OK] All relative links validated - $checkedCount files checked" -ForegroundColor Green
exit 0