@echo off
cd /d "C:\Users\graja\Desktop\AP_Analytics_Project"
echo Run started: %date% %time% >> pipeline_log.txt
python generate_new_month.py >> pipeline_log.txt 2>&1
python clean_and_analyze.py >> pipeline_log.txt 2>&1
echo Run finished: %date% %time% >> pipeline_log.txt