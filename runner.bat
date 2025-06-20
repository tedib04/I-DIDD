@echo off
REM === Setup ===
setlocal enabledelayedexpansion

REM Load environment variables from .env (basic support)
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%i in (".env") do (
        set %%i=%%j
    )
)

REM Set default ports if not defined in .env
if "%PORT_FRONTEND%"=="" set PORT_FRONTEND=8888
if "%PORT_FLINK%"=="" set PORT_FLINK=8081
if "%PORT_KAFKA_UI%"=="" set PORT_KAFKA_UI=8080

REM === Create virtual environment ===
if not exist .venv (
    echo Creating Python 3.10 virtual environment in .venv...
    py -3.10 -m venv .venv
) else (
    echo Using existing Python 3.10 virtual environment in .venv...
)

REM === Activate virtual environment ===
call .venv\Scripts\activate.bat

REM === Install Python dependencies ===
echo Installing Python dependencies...
pip install -r requirements.txt
pip install --no-deps -r requirements-pydot.txt

REM === Remove old files ===
set SCRIPT_DIR=%cd%
set declare_model_path=%SCRIPT_DIR%\frontend\src\declare_model.png
if exist "%declare_model_path%" (
    echo Removing old declare_model.png...
    del /f "%declare_model_path%"
)

set rules_path=%SCRIPT_DIR%\processor\src\rules\rules.json
if exist "%rules_path%" (
    echo Removing old rules.json...
    del /f "%rules_path%"
)

REM === Kill processes using ports ===
for %%P in (%PORT_FRONTEND% %PORT_FLINK% %PORT_KAFKA_UI%) do (
    echo Checking for process using port %%P...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%P') do (
        echo Killing PID %%a on port %%P...
        taskkill /PID %%a /F >nul 2>&1
    )
)

REM === Docker Compose restart ===
echo Stopping and removing containers from previous run...
docker compose down -v --remove-orphans

echo Starting Docker Compose services...
docker compose up -d

REM === Wait for services to be up ===
echo Waiting for frontend and Kafka UI ports...

:wait_for_frontend
powershell -Command "try { (New-Object Net.Sockets.TcpClient('localhost', %PORT_FRONTEND%)).Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 (
    timeout /t 1 >nul
    goto wait_for_frontend
)

:wait_for_kafka
powershell -Command "try { (New-Object Net.Sockets.TcpClient('localhost', %PORT_KAFKA_UI%)).Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 (
    timeout /t 1 >nul
    goto wait_for_kafka
)

REM === Open browser for services ===
echo Opening service UIs...
start "" http://localhost:%PORT_FRONTEND%
start "" http://localhost:%PORT_KAFKA_UI%

REM === Start processor module ===
echo Running processor module...
start /B cmd /c "python -m processor.src.main"

REM === Wait for Flink UI, then open ===
:wait_for_flink
powershell -Command "try { (New-Object Net.Sockets.TcpClient('localhost', %PORT_FLINK%)).Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 (
    timeout /t 1 >nul
    goto wait_for_flink
)
echo Flink UI is up. Opening in browser...
start "" http://localhost:%PORT_FLINK%

REM === Done ===
echo All services started successfully.
exit /b
