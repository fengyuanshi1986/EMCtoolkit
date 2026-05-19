#!/bin/bash
cd "$(dirname "$0")"
echo "Starting EMC Facility Toolkit..."
pip install -r requirements.txt --quiet
# Launch Toolkit (8503)
streamlit run toolkit.py --server.port 8503 &
# Launch Tracker Standalone (8501)
streamlit run tracker/app.py --server.port 8501 &
# Launch Calculator Standalone (8502)
streamlit run rate_calculator/rate_app.py --server.port 8502
