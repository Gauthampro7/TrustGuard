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
import threading
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


_LOCK = threading.Lock()
_LOADED = {}


def _load(kind):
    spec = MODELS[kind]
    options = {"revision": spec["revision"], "local_files_only": True}
    # Explicit imports: transformers' lazy attribute loading is not safe to race across threads.
    from transformers import AutoModelForImageClassification, AutoModelForSequenceClassification, AutoTokenizer
    from transformers.utils import logging as transformers_logging

    if kind == "ai_text":
        pre = AutoTokenizer.from_pretrained(spec["repo"], **options)
        model = AutoModelForSequenceClassification.from_pretrained(spec["repo"], **options)
    else:
        # The ViT preprocessing is applied directly (see ai_image_classifier) so torchvision is not required.
        from huggingface_hub import hf_hub_download
        import json
        with open(hf_hub_download(spec["repo"], "preprocessor_config.json", **options), encoding="utf-8") as handle:
            pre = json.load(handle)
        model = AutoModelForImageClassification.from_pretrained(spec["repo"], **options)
    transformers_logging.disable_progress_bar()
    return pre, model.eval()


def load(kind):
    """Return (preprocessor, model) from the local cache; raise LookupError when unavailable.

    Thread-safe: API requests run on worker threads, and the first two concurrent
    requests must not both import and load a model.
    """
    if kind in _LOADED:
        return _LOADED[kind]
    if not enabled():
        raise LookupError("Pretrained models are disabled by TRUSTGUARD_ML=0.")
    if not dependencies_installed():
        raise LookupError("PyTorch/transformers are not installed. " + INSTALL_HINT)
    with _LOCK:
        if kind not in _LOADED:
            try:
                _LOADED[kind] = _load(kind)
            except Exception as error:  # any load failure must abstain, never fail the request
                raise LookupError(f"{MODELS[kind]['repo']} could not be loaded locally ({type(error).__name__}). " + INSTALL_HINT) from error
    return _LOADED[kind]


load.cache_clear = _LOADED.clear


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
