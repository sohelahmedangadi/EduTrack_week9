#!/bin/bash
# Runs the whole pipeline from the project root.
set -e
python src/01_clean_data.py
python src/02_build_student_table.py
python src/03_baseline_metrics.py
# Week 6 analysis
python src/04_train_at_risk_model.py
python src/05_segmentation_and_cohorts.py
python src/06_statistical_tests.py
