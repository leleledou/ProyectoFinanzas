@echo off
cd /d "%~dp0"
echo Iniciando Simulador Financiero...
echo.
python -m streamlit run app.py
echo.
echo Si hubo un error, revisa el mensaje arriba.
pause
