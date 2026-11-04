@echo off
title Vector-Prod-Maxxing (Desktop HUD)
cd /d "%~dp0"

echo ========================================================
echo   Vector-Prod-Maxxing - Desktop HUD ^& Antigravity 2.0
echo ========================================================
echo.

:: 1. Verificar Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Python nao foi encontrado no PATH do Windows!
    echo Instale o Python 3.10+ marcando a opcao "Add Python to PATH".
    pause
    exit /b 1
)

:: 2. Instalar dependencias necessarias (PyQt6, pyserial, psutil)
echo [1/3] Verificando dependencias (PyQt6, pyserial, psutil)...
python -m pip install -q --disable-pip-version-check -r requirements.txt

:: 3. Iniciar Servidor Web em background (sem janela de console)
echo [2/3] Iniciando Servidor Web Local (http://localhost:8090)...
start "" pythonw web\server.py

:: 4. Iniciar Desktop HUD Flutuante (SingleInstance evita duplicatas)
echo [3/3] Iniciando Desktop HUD...
start "" pythonw main.py

echo.
echo [OK] Tudo pronto! Nenhum terminal ficara piscando em background.
echo - HUD rodando na tela e na bandeja do sistema (proximo ao relogio).
echo - Dashboard Web acessivel em: http://localhost:8090
echo - Logs salvos em: %%APPDATA%%\desktop-hud\logs
echo.
timeout /t 2 >nul
exit /b 0
