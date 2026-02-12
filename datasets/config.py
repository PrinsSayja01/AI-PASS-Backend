from __future__ import annotations

# Input folder where you drop text files
RAW_DIR = "datasets/raw"

# Intermediate processed data
PROCESSED_DIR = "datasets/processed"

# Split output
SPLITS_DIR = "datasets/splits"

# Fine-tune / prompt-engineering export
EXPORT_DIR = "datasets/export"

# Train/Val/Test split ratios
SPLIT = {"train": 0.90, "val": 0.05, "test": 0.05}

# Max chars per sample (to avoid huge samples)
MAX_CHARS = 8000

# Enable PII masking in cleaning step
MASK_PII = True
