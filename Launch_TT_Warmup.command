#!/bin/bash
cd "$(dirname "$0")"
pip install --user -r requirements.txt
python3 main.py
