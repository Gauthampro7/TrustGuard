"""Optional pretrained CPU models for the forensic extractors.

Extractors never touch the network. They load weights with local_files_only from
the Hugging Face cache and abstain when PyTorch/transformers or the weights are
missing, so the baseline install behaves exactly as before.

Install and fetch once (pinned revisions, about 850 MB):

    python -m pip install -r backend/app/forensics/requirements-ml.txt
    python -m backend.app.forensics.model_store --download

Set TRUSTGUARD_ML=0 to disable every model without uninstalling anything.
Model scores are uncalibrated classifier outputs, never proof.
"""

import argparse
from functools import lru_cache
from importlib.util import find_spec
import os

# Pinned revisions keep results reproducible across machines.
MODELS = {
    "ai_text": {
        "repo": "fakespot-ai/roberta-base-ai-text-detection-v1",
        "revision": "f9cdb14d1f8b105f597d80fa7b56f20c6ea0e9db",
        "files": ["config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json",
                  "special_tokens_map.json", "vocab.json", "merges.txt"],
        "license": "Apache-2.0",
    },
    "ai_image": {
        "repo": "haywoodsloan/ai-image-detector-deploy",
        "revision": "4ae1822603cb1ec980c217cfde1ef1b8e0477a16",
        "files": ["config.json", "model.safetensors", "preprocessor_config.json"],
        "license": "Apache-2.0",
    },
}
# Chosen by comparison on a labelled set of 15 real photos and 18 SDXL/SDXL-Turbo/FLUX/SD
# images (see VALIDATION.md): this Swin-v2 model had the fewest false positives.
INSTALL_HINT = "Install backend/app/forensics/requirements-ml.txt and run python -m backend.app.forensics.model_store --download."


def dependencies_installed():
    return all(find_spec(name) is not None for name in ("torch", "transformers"))


def enabled():
    return os.environ.get("TRUSTGUARD_ML", "1") != "0"


@lru_cache(maxsize=None)
def load(kind):
    """Return (preprocessor, model) from the local cache; raise LookupError when unavailable."""
    if not enabled():
        raise LookupError("Pretrained models are disabled by TRUSTGUARD_ML=0.")
    if not dependencies_installed():
        raise LookupError("PyTorch/transformers are not installed. " + INSTALL_HINT)
    import transformers

    spec = MODELS[kind]
    options = {"revision": spec["revision"], "local_files_only": True}
    try:
        if kind == "ai_text":
            pre = transformers.AutoTokenizer.from_pretrained(spec["repo"], **options)
            model = transformers.AutoModelForSequenceClassification.from_pretrained(spec["repo"], **options)
        else:
            # The ViT preprocessing is applied directly (see ai_image_classifier) so torchvision is not required.
            from huggingface_hub import hf_hub_download
            import json
            with open(hf_hub_download(spec["repo"], "preprocessor_config.json", **options), encoding="utf-8") as handle:
                pre = json.load(handle)
            model = transformers.AutoModelForImageClassification.from_pretrained(spec["repo"], **options)
    except (OSError, ImportError, ValueError) as error:
        raise LookupError(f"{spec['repo']} could not be loaded locally ({type(error).__name__}). " + INSTALL_HINT) from error
    transformers.utils.logging.disable_progress_bar()
    return pre, model.eval()


def available(kind):
    try:
        load(kind)
        return True
    except LookupError:
        return False


def download():
    """Explicit, operator-run fetch; never called by an extractor."""
    from huggingface_hub import hf_hub_download

    for kind, spec in MODELS.items():
        for name in spec["files"]:
            hf_hub_download(spec["repo"], name, revision=spec["revision"])
        print(f"{kind}: {spec['repo']}@{spec['revision'][:8]} cached ({spec['license']})")
    load.cache_clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--download", action="store_true", help="Fetch the pinned model weights into the local Hugging Face cache")
    args = parser.parse_args()
    if args.download:
        download()
    for kind, spec in MODELS.items():
        state = "ready" if available(kind) else "unavailable"
        print(f"{kind}: {spec['repo']} -> {state}")


if __name__ == "__main__":
    main()
