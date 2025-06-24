@echo off
cd /d %~dp0
pip install --user -r requirements.txt
python main.py
pause 