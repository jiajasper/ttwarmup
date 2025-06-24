#!/bin/bash
cd "$(dirname "$0")"

# Ensure pip is available
if ! python3 -m pip --version >/dev/null 2>&1; then
  echo "pip not found, installing pip..."
  curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
  python3 get-pip.py --user
  rm get-pip.py
fi

# Install dependencies
python3 -m pip install --user -r requirements.txt

# Run the main script
python3 main.py
