#!/bin/bash
set -e
source .venv/bin/activate
python -m security.approval_pipeline .
