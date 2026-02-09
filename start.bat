@echo off
title BI PGE-MS
echo ============================================
echo    BI PGE-MS - Iniciando servicos...
echo ============================================
echo.

:: Mata processos anteriores nas portas 8001 e 5173
echo [0/2] Limpando processos anteriores...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8001.*LISTENING"') do taskkill /F /PID %%p >nul 2>nul
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":5173.*LISTENING"') do taskkill /F /PID %%p >nul 2>nul

:: Limpa cache do frontend (Vite/node_modules/.vite)
echo    Limpando cache frontend...
if exist "E:\Projetos\BI\frontend\node_modules\.vite" rd /s /q "E:\Projetos\BI\frontend\node_modules\.vite"

:: Limpa cache Python (__pycache__)
echo    Limpando cache backend...
for /d /r "E:\Projetos\BI\backend" %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d"

timeout /t 2 /nobreak >nul

:: Backend (porta 8001)
echo [1/2] Iniciando backend na porta 8001...
start "BI-Backend" cmd /k "cd /d E:\Projetos\BI\backend && python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload"

:: Aguarda backend subir
timeout /t 5 /nobreak >nul

:: Frontend (porta 5173)
echo [2/2] Iniciando frontend na porta 5173...
start "BI-Frontend" cmd /k "cd /d E:\Projetos\BI\frontend && npm run dev"

:: Aguarda frontend subir
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo    Servicos iniciados!
echo    Frontend: http://localhost:5173
echo    Backend:  http://localhost:8001
echo    Swagger:  http://localhost:8001/docs
echo ============================================
echo.
echo Feche as janelas do terminal para parar.
pause
