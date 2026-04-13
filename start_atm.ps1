# start_atm.ps1
Write-Host "🚀 Forced Launch of ATM Stack..." -ForegroundColor Cyan

# 1. Start FastAPI (Manual Mode)
Write-Host "-> Starting Gateway..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn app.main:app --reload --port 8000"
Start-Sleep -Seconds 2

# 2. Start Streamlit (Manual Mode)
Write-Host "-> Starting Dashboard..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "streamlit run dashboard/ui.py"
Start-Sleep -Seconds 2

# 3. Start Ollama (Background)
Write-Host "-> Starting Ollama..."
Start-Process ollama -ArgumentList "serve"

Write-Host "✅ Scripts triggered. Check your taskbar for new windows." -ForegroundColor Green