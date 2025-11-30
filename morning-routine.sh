#!/bin/bash

# --- CONFIGURATION ---
# Absolute path to your project
PROJECT_DIR="$HOME/sandbox/obsidian"

# Navigate to project
cd "$PROJECT_DIR" || exit 1

# --- STEP 1: TRANSCRIPTION (Always run this first) ---
echo "Starting Morning Transcription..."
uv run --env-file .env transcriber.py

# --- STEP 2: ANALYSIS (Conditional Logic) ---
echo "Checking Analysis Schedule..."

DOM=$(date +%d) # Day of Month (01..31)
DOW=$(date +%u) # Day of Week (1..7, 7 is Sunday)

# A. Weekly Retro (Every Sunday)
if [ "$DOW" -eq 7 ]; then
    echo "Running Weekly Retro..."
    uv run --env-file .env wisdom_bro.py weekly_retro
fi

# B. Bi-Weekly Tasks (1st and 15th)
if [ "$DOM" -eq "01" ] || [ "$DOM" -eq "15" ]; then
    echo "Running Health Check & Laboratory..."
    uv run --env-file .env wisdom_bro.py health_check
    uv run --env-file .env wisdom_bro.py laboratory
fi

# C. Monthly Tasks (1st only)
if [ "$DOM" -eq "01" ]; then
    echo "Running Monthly Success & Linguistic Analysis..."
    uv run wisdom_bro.py success_recipe
    uv run wisdom_bro.py linguistic_analysis
fi

echo "Morning Routine Complete."
