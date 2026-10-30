@echo off
REM Uruchamianie aplikacji 3D Load Capacity Combinator
cd /d "%~dp0"

REM Tworzenie/aktywizacja wirtualnego środowiska
if not exist ".venv" (
    echo Tworzenie wirtualnego srodowiska .venv...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Instalowanie/aktualizacja wymaganych pakietow Pythona...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Uruchamianie aplikacji...
python main.py

pause
