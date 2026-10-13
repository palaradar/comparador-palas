@echo off
rem Doble clic: actualiza precios, regenera la web y la abre en el navegador.
cd /d "%~dp0"
python scripts\actualizar_precios.py
python scripts\buscar_cupones.py
python scripts\buscar_videos.py
python scripts\generar_web.py
start "" "web\index.html"
pause
