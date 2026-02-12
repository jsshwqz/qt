param(
  [Parameter(Mandatory = $false)]
  [string]$PackageDir = "release/QtScrcpy-win-x64",

  [Parameter(Mandatory = $false)]
  [string]$ZipPath = "release/QtScrcpy-win-x64.zip",

  [Parameter(Mandatory = $false)]
  [int]$MinZipSizeMB = 50,

  [Parameter(Mandatory = $false)]
  [switch]$SkipAdbExecution
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-PathExists {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Path,
    [Parameter(Mandatory = $true)]
    [string]$Label
  )
  if (!(Test-Path $Path)) {
    throw "[MISSING] $Label -> $Path"
  }
}

function Assert-FilesExist {
  param(
    [Parameter(Mandatory = $true)]
    [string]$BaseDir,
    [Parameter(Mandatory = $true)]
    [string[]]$RelativePaths,
    [Parameter(Mandatory = $true)]
    [string]$GroupName
  )
  foreach ($item in $RelativePaths) {
    $full = Join-Path $BaseDir $item
    if (!(Test-Path $full)) {
      throw "[MISSING] $GroupName -> $item"
    }
  }
}

Write-Host "== QtScrcpy Windows Preflight =="
Write-Host "PackageDir: $PackageDir"
Write-Host "ZipPath:    $ZipPath"
Write-Host "MinZipMB:   $MinZipSizeMB"

Assert-PathExists -Path $PackageDir -Label "Package directory"
Assert-PathExists -Path $ZipPath -Label "Release zip"

$pkg = Resolve-Path $PackageDir
$zip = Get-Item $ZipPath

Assert-FilesExist -BaseDir $pkg -GroupName "Core runtime" -RelativePaths @(
  "QtScrcpy.exe",
  "scrcpy-server",
  "platforms\qwindows.dll",
  "run_debug.bat",
  "BUILD_INFO.txt"
)

Assert-FilesExist -BaseDir $pkg -GroupName "ADB runtime folder" -RelativePaths @(
  "adb\adb.exe",
  "adb\AdbWinApi.dll",
  "adb\AdbWinUsbApi.dll"
)

Assert-FilesExist -BaseDir $pkg -GroupName "ADB runtime root fallback" -RelativePaths @(
  "adb.exe",
  "AdbWinApi.dll",
  "AdbWinUsbApi.dll"
)

$ffmpeg62 = @(
  "avcodec-62.dll",
  "avdevice-62.dll",
  "avfilter-11.dll",
  "avformat-62.dll",
  "avutil-60.dll",
  "swresample-6.dll",
  "swscale-9.dll"
)

$ffmpeg58 = @(
  "avcodec-58.dll",
  "avformat-58.dll",
  "avutil-56.dll",
  "swscale-5.dll",
  "swresample-3.dll"
)

$has62 = Test-Path (Join-Path $pkg "avcodec-62.dll")
$has58 = Test-Path (Join-Path $pkg "avcodec-58.dll")

if ($has62) {
  Assert-FilesExist -BaseDir $pkg -GroupName "FFmpeg runtime (62.x)" -RelativePaths $ffmpeg62
  Write-Host "FFmpeg profile: 62.x"
}
elseif ($has58) {
  Assert-FilesExist -BaseDir $pkg -GroupName "FFmpeg runtime (58.x)" -RelativePaths $ffmpeg58
  Write-Host "FFmpeg profile: 58.x"
}
else {
  throw "[MISSING] FFmpeg runtime -> no supported profile found (62.x or 58.x)."
}

$zipSizeMB = [Math]::Round($zip.Length / 1MB, 2)
if ($zipSizeMB -lt $MinZipSizeMB) {
  throw "[SMALL_ZIP] Zip file is too small: ${zipSizeMB}MB, expected >= ${MinZipSizeMB}MB"
}
Write-Host "Zip size check: ${zipSizeMB}MB"

if (-not $SkipAdbExecution) {
  $adbExe = Join-Path $pkg "adb\adb.exe"
  $adbText = (& $adbExe version 2>&1 | Out-String)
  if ($LASTEXITCODE -ne 0) {
    throw "[ADB_BROKEN] adb.exe failed with exit code $LASTEXITCODE. Output: $adbText"
  }
  if ($adbText -notmatch "Android Debug Bridge") {
    throw "[ADB_BROKEN] adb.exe output does not contain expected marker. Output: $adbText"
  }
  Write-Host "ADB execute check: OK"
}
else {
  Write-Host "ADB execute check: SKIPPED"
}

Write-Host "Preflight result: PASS"
