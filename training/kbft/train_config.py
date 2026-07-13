"""Typed training configuration.

One `TrainingConfig` (pydantic-settings) is the single knob surface, resolved from CLI + ENV + YAML
with library-native precedence — CLI > ENV (`TRAIN_*`) > `--config` YAML > defaults — no hand-rolled
merging. Ship hardware presets as YAML in `configs/`; override any value with a flag or env var.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class TrainingConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRAIN_",
        cli_parse_args=True,
        cli_kebab_case=True,
        extra="ignore",
    )

    config: str | None = Field(None, description="YAML preset to load (values overridden by ENV/CLI)")

    # model / method
    model: str = "LiquidAI/LFM2.5-230M"
    method: Literal["full", "lora", "qlora"] = "full"
    dtype: Literal["fp32", "bf16"] = "fp32"
    data: str | None = Field(None, description="dataset dir with sft_train.jsonl/sft_eval.jsonl")
    out: str | None = None
    resume: bool = False  # resume from the latest checkpoint in `out` (survives a killed run)

    # schedule / batch
    epochs: float = 1.3
    max_steps: int = -1  # >0 caps steps (smoke tests); -1 = full epochs
    batch_size: int = 8
    grad_accum: int = 2
    eval_batch_size: int | None = None
    max_len: int = 2560
    lr: float | None = None  # None -> method default (full 2e-5, lora/qlora 2e-4)
    warmup_ratio: float = 0.03
    lr_scheduler: str = "cosine"

    # memory / optimizer
    grad_checkpointing: bool = False
    optim: str = "adamw_torch"
    seed: int = 1234
    save_total_limit: int = 1
    logging_steps: int = 10

    # loss
    completion_only_loss: bool = False  # assistant-only loss; OFF reproduces v1.0.0

    # LoRA / QLoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: str = "all-linear"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # precedence, highest first: CLI/init > ENV > YAML preset > field defaults
        yaml_file = cls.model_config.get("yaml_file")
        sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
        if yaml_file:
            sources.append(YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file))
        return tuple(sources)

    @classmethod
    def load(cls) -> "TrainingConfig":
        """Resolve config: peek CLI/ENV for `--config`, bind that YAML, then re-resolve with full
        precedence. The peek only locates the preset file; pydantic-settings does all merging."""
        pre = cls()
        if pre.config:
            path = Path(pre.config)
            if not path.exists():
                raise FileNotFoundError(f"--config preset not found: {path}")
            cls.model_config["yaml_file"] = str(path)
        return cls()

    def resolved_lr(self) -> float:
        if self.lr is not None:
            return self.lr
        return 2e-5 if self.method == "full" else 2e-4
