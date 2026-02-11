@echo off
title Oracle SAJ via VPN + Tunel SSH
chcp 65001 >nul 2>nul
echo ============================================
echo    Oracle SAJ - Conectando via VPN + SSH
echo ============================================
echo.

:: ── Configurações ────────────────────────────
set VPN_NAME=VPN-PGE
set SSH_EXE="C:\Program Files\Git\usr\bin\ssh.exe"
set SSH_HOST=10.21.9.206
set SSH_USER=rcosta@PGE.ms
set ORACLE_HOST=10.2.12.215
set ORACLE_PORT=1521
set DBEAVER_EXE="C:\Users\kaoye\AppData\Local\DBeaver\dbeaver.exe"

:: ── 1. Verifica VPN ─────────────────────────
echo [1/3] Verificando VPN "%VPN_NAME%"...
rasdial | findstr /i "%VPN_NAME%" >nul 2>nul
if %errorlevel%==0 (
    echo       VPN ja esta conectada.
) else (
    echo       Conectando VPN...
    rasdial %VPN_NAME%
    if %errorlevel% neq 0 (
        echo.
        echo [ERRO] Falha ao conectar VPN. Verifique suas credenciais.
        echo        Tente conectar manualmente: rasdial %VPN_NAME%
        pause
        exit /b 1
    )
    echo       VPN conectada.
)
echo.

:: ── 2. Abre túnel SSH ────────────────────────
echo [2/3] Verificando tunel SSH (localhost:%ORACLE_PORT%)...

:: Verifica se a porta já está aberta
powershell -Command "try { $c = New-Object Net.Sockets.TcpClient('localhost', %ORACLE_PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel%==0 (
    echo       Porta %ORACLE_PORT% ja esta aberta (tunel existente).
) else (
    echo       Abrindo tunel SSH %ORACLE_HOST%:%ORACLE_PORT% via %SSH_USER%@%SSH_HOST%...
    start "SSH-Tunnel-Oracle" /min %SSH_EXE% -L %ORACLE_PORT%:%ORACLE_HOST%:%ORACLE_PORT% %SSH_USER%@%SSH_HOST% -N -o StrictHostKeyChecking=no -o ServerAliveInterval=60

    :: Aguarda túnel ficar disponível (até 30s)
    set /a TENTATIVAS=0
    :AGUARDA_TUNEL
    timeout /t 1 /nobreak >nul
    set /a TENTATIVAS+=1
    powershell -Command "try { $c = New-Object Net.Sockets.TcpClient('localhost', %ORACLE_PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>nul
    if %errorlevel%==0 (
        echo       Tunel SSH ativo em localhost:%ORACLE_PORT%.
        goto TUNEL_OK
    )
    if %TENTATIVAS% lss 30 goto AGUARDA_TUNEL

    echo.
    echo [ERRO] Tunel SSH nao ficou disponivel em 30s.
    echo        Verifique a VPN e a chave SSH.
    pause
    exit /b 1
)
:TUNEL_OK
echo.

:: ── 3. Abre DBeaver ─────────────────────────
echo [3/3] Abrindo DBeaver...
if exist %DBEAVER_EXE% (
    start "" %DBEAVER_EXE%
    echo       DBeaver aberto.
) else (
    echo       [AVISO] DBeaver nao encontrado em %DBEAVER_EXE%
    echo       Abra manualmente e conecte em localhost:%ORACLE_PORT%
)

echo.
echo ============================================
echo    Conexao Oracle disponivel!
echo.
echo    Host:  localhost
echo    Porta: %ORACLE_PORT%
echo    SID:   SPJMS
echo.
echo    NAO FECHE esta janela enquanto usar o
echo    DBeaver - o tunel SSH ficara ativo aqui.
echo ============================================
echo.
echo Pressione qualquer tecla para ENCERRAR o tunel SSH...
pause >nul

:: Encerra túnel SSH
echo.
echo Encerrando tunel SSH...
taskkill /fi "WINDOWTITLE eq SSH-Tunnel-Oracle" /f >nul 2>nul
echo Pronto.
