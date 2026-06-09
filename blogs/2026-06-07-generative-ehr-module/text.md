---
title: "Generate Synthetic Patients with PyHealth"
description: "PyHealth now ships a synthetic EHR generation module, five generators behind one API plus a privacy and utility evaluation suite, and we need your help testing it."
author: "John Wu & Andy Gao"
updated: "2026-06-07"
---

**TL;DR:** PyHealth can now generate synthetic patients, and evaluate how good they are. Five generators sit behind one unified API, with a matching evaluation suite for privacy and utility. It is new, so please help us find the rough edges.

---

## First, the credit

This module is the work of [Andy Gao](https://chufangao.github.io/). He did the heavy lifting of bringing a full synthetic EHR stack into PyHealth, models and evaluation alike.

---

## What's new

Synthetic patient generation is now built directly into PyHealth. You can train a generative model on real EHR sequences, sample brand new synthetic patients, and then measure whether those patients are both useful and privacy-preserving, all without leaving the framework.

You get five generators behind a single, consistent API:

### Sequential Case
Patients can have multiple visits, and each visit has multiple ICD codes
- [**HALO**](https://pyhealth.readthedocs.io/en/latest/api/models/pyhealth.models.HALO.html), a hierarchical autoregressive transformer over visits and codes 
- [**GPT-2**](https://pyhealth.readthedocs.io/en/latest/api/models/pyhealth.models.GPT2.html), a decoder-only baseline over flattened visit streams
- [**PromptEHR**](https://pyhealth.readthedocs.io/en/latest/api/models/pyhealth.models.PromptEHR.html), a BART denoising autoencoder with learnable soft prompts

### Flat Case
Patients are represented only by ICD codes (treated as a single visit)
- [**MedGAN**](https://pyhealth.readthedocs.io/en/latest/api/models/pyhealth.models.MedGAN.html), a bag-of-codes generative adversarial network
- [**CorGAN**](https://pyhealth.readthedocs.io/en/latest/api/models/pyhealth.models.CorGAN.html), a CNN-based Wasserstein GAN variant

On the evaluation side, `evaluate_synthetic_ehr()` scores your synthetic data along two axes: privacy (nearest-neighbor acceptance, membership inference) and utility (train-real-test-real versus train-synthetic-test-real, plus code-prevalence similarity). See the [generative metrics documentation](https://pyhealth.readthedocs.io/en/latest/api/metrics/pyhealth.metrics.generative.html) for the full list.

---

## A quick look

Every generator follows the same shape: load a dataset, set the generation task, train, then sample.

```python
from pyhealth.datasets import MIMIC3Dataset, split_by_patient
from pyhealth.models import HALO
from pyhealth.tasks import EHRGenerationMIMIC3


def main() -> None:
    base = MIMIC3Dataset(root="/path/to/mimic-iii", tables=["diagnoses_icd"])
    samples = base.set_task(EHRGenerationMIMIC3())      # same set_task you already know
    train, val, test = split_by_patient(samples, [0.8, 0.1, 0.1])

    model = HALO(dataset=samples, embed_dim=128, n_heads=4, n_layers=4, epochs=5)
    model.train_model(train, val_dataset=val)

    synthetic = model.generate(num_samples=len(train), random_sampling=True)


if __name__ == "__main__":
    main()
```

Swap `HALO` for `GPT2`, `PromptEHR`, `MedGAN`, or `CorGAN` and the rest barely changes. A full runnable script lives at `examples/halo_mimic3.py` in the repo.

---

## Help us test it

We merged this in fast because we would rather get it into your hands than sit on it. That also means there are bugs and awkward corners we have not found yet.

If you hit something strange, a confusing error, a model that will not train, a metric that looks off, please post it in the [generative modeling bug thread](https://github.com/sunlabuiuc/PyHealth/issues/1156). Every report makes the module better for the next person.

Prefer to talk it through? [Join our Discord community](https://discord.gg/mpb835EHaX) for direct support and feedback. We are happy to help you get started or dig into whatever you run into.
