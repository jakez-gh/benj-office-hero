#!/usr/bin/env pwsh
# record-demo.ps1 — Record an automated demo of the Office Hero mobile app
# Usage: .\scripts\record-demo.ps1 [-Device RZCY41VRANE] [-Output demo.mp4]

param(
    [string]$Device = "RZCY41VRANE",
    [string]$Output = "$PSScriptRoot\..\demo\office-hero-demo.mp4",
    [int]$Duration = 40
)

$adb = "$env:ANDROID_HOME\platform-tools\adb.exe"
if (-not (Test-Path $adb)) {
    $adb = "C:\Users\jake\AppData\Local\Android\Sdk\platform-tools\adb.exe"
}

$RemotePath = "/sdcard/office-hero-demo.mp4"

# Ensure output directory exists
$outputDir = Split-Path $Output -Parent
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

function Adb {
    param([string[]]$Args)
    & $adb -s $Device @Args
}

function Tap {
    param([int]$X, [int]$Y, [string]$Label = "")
    if ($Label) { Write-Host "  → Tap: $Label ($X, $Y)" -ForegroundColor Gray }
    Adb "shell", "input", "tap", "$X", "$Y"
    Start-Sleep -Milliseconds 600
}

function TypeText {
    param([string]$Text, [string]$Label = "")
    if ($Label) { Write-Host "  → Type: $Label" -ForegroundColor Gray }
    # Escape special chars for shell
    $escaped = $Text -replace ' ', '%s'
    Adb "shell", "input", "text", $escaped
    Start-Sleep -Milliseconds 500
}

function Key {
    param([string]$KeyCode)
    Adb "shell", "input", "keyevent", $KeyCode
    Start-Sleep -Milliseconds 300
}

function Wait {
    param([int]$Ms = 1000, [string]$Label = "")
    if ($Label) { Write-Host "  ⏳ $Label" -ForegroundColor DarkGray }
    Start-Sleep -Milliseconds $Ms
}

Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Office Hero Mobile — Demo Recording " -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 0: Verify device connected
Write-Host "0. Checking device $Device..." -ForegroundColor Yellow
$devices = & $adb devices
if ($devices -notmatch $Device) {
    Write-Host "   ❌ Device $Device not connected!" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ Device connected" -ForegroundColor Green

$screenSize = Adb "shell", "wm", "size"
Write-Host "   Screen: $screenSize" -ForegroundColor Gray
# Parse dimensions
if ($screenSize -match "(\d+)x(\d+)") {
    $W = [int]$Matches[1]
    $H = [int]$Matches[2]
} else {
    $W = 1080; $H = 2340
}
$CX = [int]($W / 2)

# Step 1: Clean up old recording
Write-Host "1. Cleaning up old recording..." -ForegroundColor Yellow
Adb "shell", "rm", "-f", $RemotePath | Out-Null

# Step 2: Wake and unlock screen
Write-Host "2. Waking device..." -ForegroundColor Yellow
Key "KEYCODE_WAKEUP"
Wait 800
Key "KEYCODE_MENU"
Wait 500
# Swipe up to dismiss lock screen if needed
Adb "shell", "input", "swipe", "$CX", ([int]($H * 0.8)).ToString(), "$CX", ([int]($H * 0.3)).ToString(), "300"
Wait 1000

# Step 3: Launch Expo Go with the app
Write-Host "3. Launching Office Hero in Expo Go..." -ForegroundColor Yellow
Adb "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "exp://10.194.12.170:8081", "host.exp.exponent" | Out-Null
Wait 3000 "Waiting for app to load..."

# Step 4: Start recording AFTER app is visible
Write-Host ("4. Starting screen recording " + $Duration + " sec...") -ForegroundColor Yellow
$recordJob = Start-Job -ScriptBlock {
    param($adbPath, $device, $remotePath, $duration)
    & $adbPath -s $device shell "screenrecord --time-limit $duration $remotePath"
} -ArgumentList $adb, $Device, $RemotePath, $Duration
Wait 1500 "Letting recorder initialize..."
Write-Host "   ✅ Recording active" -ForegroundColor Green

# Step 5: Demo sequence — Login Screen
Write-Host "5. Demonstrating Login Screen..." -ForegroundColor Yellow

# Calculate field positions based on screen height
$emailY    = [int]($H * 0.38)
$passwordY = [int]($H * 0.47)
$loginBtnY = [int]($H * 0.57)

# Clear any existing text and type email
Tap $CX $emailY "Email field"
Key "KEYCODE_CTRL_A"
Adb "shell", "input", "text", "tech@officehero.app"
Wait 800

# Password field
Tap $CX $passwordY "Password field"
Key "KEYCODE_CTRL_A"
Adb "shell", "input", "text", "Password123!"
Wait 800

# Pause to show filled form (2 seconds)
Wait 2000 "Showing filled form..."

# Tap Login button
Tap $CX $loginBtnY "Login button"
Wait 3000 "Waiting for login response..."

# Step 6: Navigate Route Screen (if it loads)
Write-Host "6. Exploring Route Screen..." -ForegroundColor Yellow
Wait 2000
# Scroll down to see route list
Adb "shell", "input", "swipe", "$CX", ([int]($H * 0.6)).ToString(), "$CX", ([int]($H * 0.3)).ToString(), "500"
Wait 1500

# Step 7: Navigate to Job Entry
Write-Host "7. Navigating to Job Entry Screen..." -ForegroundColor Yellow
# Tap on the first route item (approximate position)
$routeItemY = [int]($H * 0.4)
Tap $CX $routeItemY "First route item"
Wait 2000

# Scroll to show job entry form
Adb "shell", "input", "swipe", "$CX", ([int]($H * 0.7)).ToString(), "$CX", ([int]($H * 0.3)).ToString(), "500"
Wait 1500

# Step 8: Show app info and exit gracefully
Write-Host "8. Final pause for review..." -ForegroundColor Yellow
Wait 3000 "Holding final screen..."

# Press back to return
Key "KEYCODE_BACK"
Wait 1000
Key "KEYCODE_BACK"
Wait 1000

# Step 9: Stop recording
Write-Host "9. Stopping recording..." -ForegroundColor Yellow
# Signal the recording to stop (it will auto-stop at time limit too)
Adb "shell", "pkill", "-l", "2", "screenrecord" | Out-Null
Wait 2000

# Wait for job to finish
$recordJob | Wait-Job -Timeout 10 | Out-Null
Remove-Job $recordJob -Force -ErrorAction SilentlyContinue

# Step 10: Pull video from device
Write-Host "10. Pulling recording from device..." -ForegroundColor Yellow
$pullResult = Adb "pull", $RemotePath, $Output
if (Test-Path $Output) {
    $size = (Get-Item $Output).Length / 1MB
    Write-Host "   ✅ Recording saved: $Output ($([math]::Round($size, 1)) MB)" -ForegroundColor Green
} else {
    Write-Host "   ❌ Pull failed — check $RemotePath on device" -ForegroundColor Red
}

Write-Host ""
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Demo recording complete!" -ForegroundColor Green
Write-Host " Output: $Output" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
