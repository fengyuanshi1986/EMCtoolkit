#!/bin/bash
cd "$(dirname "$0")"
echo "Starting EMC Facility Toolkit..."
echo "Checking for updates and libraries..."
pip install -r requirements.txt --quiet
streamlit run toolkit.py
