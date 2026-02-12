"""
LoRA fine-tuning skeleton (MVP)
- Add transformers + peft later when you are ready
- This file proves pipeline structure
"""
from pathlib import Path
import json

def main():
    data_path = Path("training/sft_train.json")
    if not data_path.exists():
        raise SystemExit("Run: python3 training/prepare_sft.py first")

    data = json.loads(data_path.read_text(encoding="utf-8"))
    print("✅ SFT samples:", len(data))
    print("Next: install transformers + peft, load model, train LoRA, save adapter.")

if __name__ == "__main__":
    main()
