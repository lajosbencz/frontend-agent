"""Publish the model and/or dataset to the Hugging Face Hub.

Token is read from the environment only (HF_WRITE_TOKEN, then HF_TOKEN) and never logged. Repos are
created private by default; re-run with --public to flip visibility once the rendered cards look right.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PUB = REPO / "artifacts" / "gguf" / "publish"
MODEL_CARD = REPO / "publish" / "model_card.md"  # tracked source for the model README/card


def _token() -> str:
    tok = os.environ.get("HF_WRITE_TOKEN") or os.environ.get("HF_TOKEN")
    if not tok:
        sys.exit("HF_WRITE_TOKEN (or HF_TOKEN) not set in the environment.")
    return tok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["model", "dataset", "both"], default="both")
    ap.add_argument("--model-repo", default="lazos/lfm2.5-230m-frontend-agent")
    ap.add_argument("--dataset-repo", default="lazos/frontend-agent-sft")
    ap.add_argument("--model-dir", default=str(PUB / "hf-model"))
    ap.add_argument("--dataset-dir", default=str(PUB / "hf-dataset"))
    ap.add_argument("--public", action="store_true", help="create/set the repo public (default private)")
    ap.add_argument("--version", required=True, help="release tag, e.g. v1.0.1 — the commit is git-tagged "
                    "so a stable file path resolves per ref (resolve/<version>/... vs resolve/main/...)")
    args = ap.parse_args()

    from huggingface_hub import HfApi
    api = HfApi(token=_token())
    who = api.whoami()
    print(f"authenticated as: {who.get('name')}")
    private = not args.public

    jobs = []
    if args.what in ("model", "both"):
        jobs.append(("model", args.model_repo, args.model_dir))
    if args.what in ("dataset", "both"):
        jobs.append(("dataset", args.dataset_repo, args.dataset_dir))

    for repo_type, repo_id, folder in jobs:
        folder = Path(folder)
        if not folder.is_dir():
            sys.exit(f"missing {repo_type} folder: {folder}")
        if repo_type == "model" and not (folder / "README.md").exists() and MODEL_CARD.exists():
            shutil.copy(MODEL_CARD, folder / "README.md")  # stamp the tracked card if unbuilt
            print(f"[model] wrote card from {MODEL_CARD}")
        api.create_repo(repo_id, repo_type=repo_type, private=private, exist_ok=True)
        if not private:
            api.update_repo_settings(repo_id, private=False, repo_type=repo_type)
        print(f"[{repo_type}] uploading {folder} -> {repo_id} (private={private}) ...")
        # Stable filenames + one tag per release: main tracks latest, tags pin history. delete_patterns
        # keeps main from accumulating stale GGUFs from prior versions (filenames carry NO version).
        api.upload_folder(repo_id=repo_id, repo_type=repo_type, folder_path=str(folder),
                          commit_message=f"publish frontend-agent {args.version}",
                          delete_patterns=["*.gguf"] if repo_type == "model" else None)
        try:
            api.delete_tag(repo_id, tag=args.version, repo_type=repo_type)
        except Exception:
            pass
        api.create_tag(repo_id, tag=args.version, repo_type=repo_type, revision="main")
        url = f"https://huggingface.co/{'datasets/' if repo_type == 'dataset' else ''}{repo_id}"
        print(f"[{repo_type}] done: {url}  (tagged {args.version})")


if __name__ == "__main__":
    main()
