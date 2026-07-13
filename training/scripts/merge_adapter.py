"""Merge a LoRA/QLoRA adapter into the base weights -> standalone HF checkpoint (for GGUF export)."""

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "training" / "artifacts"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="LiquidAI/LFM2.5-230M")
    parser.add_argument("--adapter", default=str(ARTIFACTS / "lora-230m"))
    parser.add_argument("--out", default=str(ARTIFACTS / "merged-230m"))
    args = parser.parse_args()

    tok = AutoTokenizer.from_pretrained(args.base)
    base = AutoModelForCausalLM.from_pretrained(args.base, dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(base, args.adapter)
    merged = model.merge_and_unload()
    merged.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print(f"Merged checkpoint saved to {args.out}")


if __name__ == "__main__":
    main()
