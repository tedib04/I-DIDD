@echo off
setlocal enabledelayedexpansion

REM Verify Python 3.10 exists
py -3.10 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.10 not found. Install Python 3.10 first.
    pause
    exit /b 1
)

REM Load environment variables from .env
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%i in (".env") do (
        set %%i=%%j
    )
)

REM Set default ports if not defined
if "%PORT_FRONTEND%"=="" set PORT_FRONTEND=8888
if "%PORT_FLINK%"=="" set PORT_FLINK=8081
if "%PORT_KAFKA_UI%"=="" set PORT_KAFKA_UI=8080

REM Create virtual environment explicitly with Python 3.10
if not exist .venv (
    echo Creating Python 3.10 virtual environment...
    py -3.10 -m venv .venv
) else (
    echo Using existing Python 3.10 virtual environment...
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Upgrade pip first
python -m pip install --upgrade pip setuptools wheel

REM Install dependencies explicitly
echo Installing dependencies...
pip install -r requirements.txt
pip install --no-deps -r requirements-pydot.txt

REM Remove old files
set SCRIPT_DIR=%cd%
set DECLARE_MODEL_PATH=%SCRIPT_DIR%\frontend\src\declare_model.png
if exist "%DECLARE_MODEL_PATH%" (
    echo Removing old declare_model.png...
    del /f "%DECLARE_MODEL_PATH%"
)

set RULES_PATH=%SCRIPT_DIR%\processor\src\rules\rules.json
if exist "%RULES_PATH%" (
    echo Removing old rules.json...
    del /f "%RULES_PATH%"
)

REM Kill processes using ports
for %%P in (%PORT_FRONTEND% %PORT_FLINK% %PORT_KAFKA_UI%) do (
    echo Checking processes on port %%P...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%P') do (
        taskkill /PID %%a /F >nul 2>&1
    )
)

REM Restart Docker Compose
docker compose down -v --remove-orphans
docker compose up -d

REM Wait for frontend port
:wait_for_frontend
powershell -Command "exit !(Test-NetConnection localhost -Port %PORT_FRONTEND%).TcpTestSucceeded"
if errorlevel 1 (
    timeout /t 1 >nul
    goto wait_for_frontend
)

REM Wait for Kafka UI port
:wait_for_kafka
powershell -Command "exit !(Test-NetConnection localhost -Port %PORT_KAFKA_UI%).TcpTestSucceeded"
if errorlevel 1 (
    timeout /t 1 >nul
    goto wait_for_kafka
)

REM Open UI services
start "" http://localhost:%PORT_FRONTEND%
start "" http://localhost:%PORT_KAFKA_UI%

REM Run processor module
start /B cmd /c "python -m processor.src.main"

REM Wait for Flink UI, then open
:wait_for_flink
powershell -Command "exit !(Test-NetConnection localhost -Port %PORT_FLINK%).TcpTestSucceeded"
if errorlevel 1 (
    timeout /t 1 >nul
    goto wait_for_flink
)
start "" http://localhost:%PORT_FLINK%

echo All services started successfully.
pause
