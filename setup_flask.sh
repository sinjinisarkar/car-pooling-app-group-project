#!/bin/bash

echo "!!! Deleting existing virtual environment (flask/)..."
rm -rf flask/

echo "!!! Creating new virtual environment..."
python3 -m venv flask

echo "!!! Activating new environment..."
source flask/bin/activate

echo "!!! Upgrading pip..."
pip install --upgrade pip

echo "!!! Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "!!! Flask environment set up successfully!"
echo "To activate it, run: source flask/bin/activate"