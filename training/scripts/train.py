"""Fine-tune a small LFM2.5 model on the generated SFT dataset.

Config resolves from CLI + ENV (`TRAIN_*`) + a `--config` YAML preset (see `configs/`), CLI winning.
Defaults to FULL-parameter fp32 fine-tuning — for a 230M model this fits a 16GB card and gives more
capacity than LoRA. `--method lora|qlora` for the low-rank / 4-bit paths. Check GPU load (nvidia-smi)
first — the card is shared.
"""

import json
import os
from pathlib import Path

# fp32 230M at max_len 2560 sits at the 16GB edge; defrag the allocator so it fits reliably
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import SFTConfig, SFTTrainer

from kbft.train_config import TrainingConfig

REPO = Path(__file__).resolve().parents[2]
DATASET = REPO / "training" / "data" / "dataset"
ARTIFACTS = REPO / "training" / "artifacts"


def main() -> None:
    cfg = TrainingConfig.load()

    out = cfg.out or str(ARTIFACTS / f"{cfg.method}-230m")
    lr = cfg.resolved_lr()
    torch_dtype = torch.float32 if cfg.dtype == "fp32" else torch.bfloat16
    # TF32 matmuls keep fp32 storage but run faster on Blackwell — free speedup for fp32 FT
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    tokenizer = AutoTokenizer.from_pretrained(cfg.model)

    quant_config = None
    if cfg.method == "qlora":
        from transformers import BitsAndBytesConfig
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch_dtype, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(cfg.model, dtype=torch_dtype,
                                                 quantization_config=quant_config)

    data_dir = Path(cfg.data) if cfg.data else DATASET
    # Provenance gate: surface WHAT we train on (version, seed, sha, leakage-check) so a stale or
    # unpinned data dir is visible, not silent. Prefer the snapshot manifest; else the run-manifest.
    mf_path = next((data_dir / n for n in ("manifest.json", "run_manifest.json")
                    if (data_dir / n).exists()), None)
    if mf_path:
        mf = json.loads(mf_path.read_text())
        sha = (mf.get("files", {}).get("sft_train.jsonl", {}).get("sha256_12")
               or mf.get("sha", {}).get("sft_train.jsonl", "?"))
        print(f"[data] {data_dir.name}: version={mf.get('version','(processed)')} "
              f"seed={mf.get('seed','?')} train_sha={sha} held_out={mf.get('held_out','?')}")
    else:
        print(f"[data] WARNING: {data_dir} has no manifest.json/run_manifest.json — training on "
              f"unversioned/unverified data. Provenance and held-out guarantee are UNKNOWN.")
    train_ds = load_dataset("json", data_files=str(data_dir / "sft_train.jsonl"), split="train")
    eval_ds = load_dataset("json", data_files=str(data_dir / "sft_eval.jsonl"), split="train")

    # Report the training-token budget (capped at max_len, times epochs) to confirm the target.
    lens = [len(tokenizer(t, add_special_tokens=False)["input_ids"]) for t in train_ds["text"]]
    tot = sum(min(x, cfg.max_len) for x in lens)
    over = sum(1 for x in lens if x > cfg.max_len)
    print(f"train examples={len(train_ds)} dataset_tokens={tot:,} "
          f"trained_tokens@{cfg.epochs}ep={int(tot * cfg.epochs):,} "
          f"max_example={max(lens)} over_max_len={over}")
    if over:
        print(f"WARNING: {over} examples exceed max_len={cfg.max_len} and WILL be truncated "
              f"(longest={max(lens)}). Bump max_len so multi-turn flows aren't cut off.")

    sft = SFTConfig(
        output_dir=out,
        num_train_epochs=cfg.epochs,
        max_steps=cfg.max_steps,
        per_device_train_batch_size=cfg.batch_size,
        per_device_eval_batch_size=(cfg.eval_batch_size or cfg.batch_size),
        gradient_accumulation_steps=cfg.grad_accum,
        optim=cfg.optim,
        learning_rate=lr,
        lr_scheduler_type=cfg.lr_scheduler,
        warmup_ratio=cfg.warmup_ratio,
        logging_steps=cfg.logging_steps,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=cfg.save_total_limit,
        bf16=(cfg.dtype == "bf16"),
        fp16=False,
        gradient_checkpointing=cfg.grad_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False} if cfg.grad_checkpointing else None,
        max_length=cfg.max_len,
        packing=False,
        dataset_text_field="text",
        # Assistant-only loss: mask everything but the assistant turns. OFF reproduces v1.0.0 (trained
        # on the full sequence); ON is the canonical choice for a tool-calling model on a retrain.
        completion_only_loss=cfg.completion_only_loss,
        report_to="none",
        seed=cfg.seed,
    )

    peft_config = None
    if cfg.method in ("lora", "qlora"):
        from peft import LoraConfig
        peft_config = LoraConfig(
            r=cfg.lora_r, lora_alpha=cfg.lora_alpha, lora_dropout=cfg.lora_dropout, bias="none",
            task_type="CAUSAL_LM", target_modules=cfg.lora_target_modules)

    trainer = SFTTrainer(model=model, args=sft, train_dataset=train_ds, eval_dataset=eval_ds,
                         peft_config=peft_config, processing_class=tokenizer)

    n_train = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
    print(f"method={cfg.method} dtype={cfg.dtype} lr={lr} "
          f"completion_only_loss={cfg.completion_only_loss} trainable_params={n_train/1e6:.1f}M")
    trainer.train(resume_from_checkpoint=cfg.resume or None)
    trainer.save_model(out)
    tokenizer.save_pretrained(out)
    print(f"Saved {cfg.method} model to {out}")


if __name__ == "__main__":
    main()
