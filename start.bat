@echo off
title BI PGE-MS
echo ============================================
echo    BI PGE-MS - Iniciando servicos...
echo ============================================
echo.

:: Backend (porta 8001)
echo [1/2] Iniciando backend na porta 8001...
start "BI-Backend" cmd /k "cd /d E:\Projetos\BI\backend && python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload"

:: Aguarda backend subir
timeout /t 3 /nobreak >nul

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
