Write-Host "--- 🛡️ Starting Security Scan ---"

Write-Host "`n[1] Checking for Vulnerable Dependencies (Safety)..."
venv\Scripts\safety check --full-report
if ($LASTEXITCODE -ne 0) { Write-Host "⚠️ Safety found issues!" -ForegroundColor Yellow }

Write-Host "`n[2] Static Code Analysis (Bandit)..."
venv\Scripts\bandit -r backend -ll
if ($LASTEXITCODE -ne 0) { Write-Host "⚠️ Bandit found issues!" -ForegroundColor Yellow }

Write-Host "`n--- Scan Complete ---"
