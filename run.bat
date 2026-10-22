@echo off
setlocal EnableExtensions
title Conecta System // Painel de Automacao

cd /d "%~dp0"

if not exist "requirements.txt" (
    echo ERRO: requirements.txt nao foi encontrado na pasta do projeto.
    pause
    exit /b 1
)

echo ========================================================
echo        CONECTA SYSTEM // MULTI-ACCOUNT AUTOMATION
echo ========================================================
echo.
echo [1/7] Verificando sistema, arquitetura e espaco em disco...
if /i not "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    echo AVISO: este projeto foi preparado para Windows 64-bit.
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$free=(Get-PSDrive -Name ((Get-Location).Drive.Name)).Free/1GB; if ($free -lt 2) { exit 1 }"
if errorlevel 1 (
    echo ERRO: sao necessarios pelo menos 2 GB livres no disco do projeto.
    pause
    exit /b 1
)

echo [2/7] Verificando acesso a internet e gerenciador de pacotes...
where winget >nul 2>&1
if errorlevel 1 (
    echo ERRO: winget nao foi encontrado. Atualize a App Installer pela Microsoft Store.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri 'https://pypi.org' -UseBasicParsing -TimeoutSec 15 | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo ERRO: sem acesso a internet. A instalacao automatica nao pode continuar.
    pause
    exit /b 1
)

echo [3/7] Verificando runtime Microsoft Visual C++...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed >nul 2>&1
if errorlevel 1 (
    echo Runtime C++ nao encontrado. Instalando Microsoft Visual C++ Redistributable...
    winget install --id Microsoft.VCRedist.2015+.x64 --exact --scope machine --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo ERRO: nao foi possivel instalar o runtime Microsoft Visual C++.
        echo Execute este arquivo como administrador e tente novamente.
        pause
        exit /b 1
    )
) else (
    echo Runtime Microsoft Visual C++ x64 ja instalado.
)

echo [4/7] Verificando Python compativel...

set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 (
    py -3.13 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3.13"
)

if not defined PYTHON_CMD (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3.12 -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.12"
    )
)

if not defined PYTHON_CMD (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3.11 -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=py -3.11"
    )
)

if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(0 if sys.version_info[:2] in [(3, 11), (3, 12), (3, 13)] else 1)" >nul 2>&1
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo Python compativel nao encontrado. Tentando instalar Python 3.13 via winget...
    where winget >nul 2>&1
    if errorlevel 1 (
        echo ERRO: Python 3.11, 3.12 ou 3.13 nao foi encontrado e o winget nao esta disponivel.
        echo Instale o Python 3.13 em https://www.python.org/downloads/
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.13 --exact --scope user --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo ERRO: nao foi possivel instalar o Python automaticamente.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3.13"
)

echo [5/7] Criando ambiente virtual local, se necessario...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] in [(3, 11), (3, 12), (3, 13)] else 1)" >nul 2>&1
    if errorlevel 1 (
        echo Ambiente virtual incompatível encontrado. Recriando...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv ".venv"
    if errorlevel 1 (
        echo ERRO: nao foi possivel criar o ambiente virtual.
        pause
        exit /b 1
    )
)

echo [6/7] Instalando e atualizando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERRO: nao foi possivel atualizar o pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --only-binary=:all: -r "requirements.txt"
if errorlevel 1 (
    echo ERRO: nao foi possivel instalar as dependencias binarias.
    echo Verifique a conexao com a internet ou a versao do Python.
    pause
    exit /b 1
)

echo [7/7] Validando instalacao e iniciando servidor...
".venv\Scripts\python.exe" -c "import fastapi, httpx, pydantic, uvicorn; import core.models, core.manager, core.proxy_manager, core.twitter_api"
if errorlevel 1 (
    echo ERRO: a validacao das dependencias falhou.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m compileall -q server.py core
if errorlevel 1 (
    echo ERRO: existe erro de sintaxe em um arquivo Python do projeto.
    pause
    exit /b 1
)

netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul
if not errorlevel 1 (
    echo ERRO: a porta 8000 ja esta em uso por outro processo.
    echo Feche o processo que usa essa porta e tente novamente.
    pause
    exit /b 1
)

echo Acesse no seu navegador: http://localhost:8000
echo Pressione Ctrl+C para encerrar o servidor.
echo ========================================================
".venv\Scripts\python.exe" -m uvicorn server:app --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo O servidor foi encerrado com erro.
    pause
)
