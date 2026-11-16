Write-Host "🚀 Starting SketchAI Collaborative Drawing Game..." -ForegroundColor Cyan
Set-Location "D:\Gradious"

$pythonExe = "D:\env\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "C:\Users\jayas\AppData\Local\Programs\Python\Python313\python.exe"
}

& $pythonExe Backend\main.py
