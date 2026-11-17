#!/bin/bash
# Runs the whole pipeline from the project root.
set -e
python src/01_clean_data.py
python src/02_build_student_table.py
python src/03_baseline_metrics.py
