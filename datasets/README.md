# Datasets Pipeline (MVP)

## Input
Put your raw text files in:
- datasets/raw/*.txt
- datasets/raw/*.md

## Run order
1) Collect:
   python3 -m datasets.collect

2) Clean:
   python3 -m datasets.clean

3) Split:
   python3 -m datasets.split

4) Export instruction JSONL:
   python3 -m datasets.export_jsonl

## Outputs
- datasets/processed/raw.jsonl
- datasets/processed/clean.jsonl
- datasets/splits/train.jsonl, val.jsonl, test.jsonl
- datasets/export/train_instruct.jsonl, val_instruct.jsonl

Note: export_jsonl uses weak-supervision (pseudo labels).
Replace with real labeled data for best fine-tuning results.
