Param(
    [switch]$Cloud = $true
)

$ErrorActionPreference = "Stop"

Write-Host "[autopilot] Running validation..."
python project_validator.py

if ($Cloud) {
    Write-Host "[autopilot] Running cloud-preferred build preparation..."
    python build_enhanced.py --cloud
} else {
    Write-Host "[autopilot] Running local build path..."
    python build_enhanced.py
}

Write-Host "[autopilot] Done."
