---
title: "Join the PyHealth Benchmark"
description: "Become a reference point that others report against: how to bring your method, task or dataset into the PyHealth clinical prediction benchmark, and how we help."
author: "Jimeng Sun & PyHealth Team"
updated: "2026-11-02"
---

*Become a reference point that others report against, and let us help you get there.*

Every clinical ML paper compares against something. Today that something is usually a handful of baselines, re-implemented by the authors, on their own preprocessing and splits. Two papers that both report "mortality prediction on MIMIC" often aren't measuring the same thing, so the field can't tell which ideas actually work.

We are building PyHealth into a shared, living benchmark for clinical predictive models: methods, tasks and datasets that all run through the same data pipelines, the same patient-level splits and the same metrics, including calibration and confidence intervals. We want the strongest recent work from the community in it, including yours.

## Three ways in

- **A new model or method** → contribute a model class that plugs into PyHealth's training and evaluation. Others can then benchmark it against 50+ models on any PyHealth task, in a few lines.
- **A new prediction question** → contribute a task: your cohort and label definition, on a dataset PyHealth already loads. Others can then use your exact definition instead of approximating it.
- **A new data source** → contribute a dataset loader, with a default task. Others can then run every PyHealth model on your data.

Not every contribution is a model. A careful task definition or a well-built dataset loader often has the longest life in a benchmark, because every future method gets evaluated on it.

## What you get

- **A fair comparison.** Your method is evaluated next to the others under identical conditions, and the numbers people quote come from the same pipeline.
- **Lasting visibility.** Benchmark entries are what new papers report against. Each one cites the work it compares with.
- **Credit.** Contributors are credited in PyHealth and featured on pyhealth.dev.
- **Reach.** PyHealth is already used in published work at more than 60 institutions, from university labs to hospitals and industry.

## What a contribution looks like

1. Tell us about your paper on [Discord](https://discord.gg/mpb835EHaX) or in a [GitHub issue](https://github.com/sunlabuiuc/PyHealth/issues). We'll suggest the right shape: model, task or dataset.
2. Port the core of your method into a PyHealth class. Our team will help with the parts that touch PyHealth's internals.
3. Add a test that runs on a few rows of synthetic data (never real patient data) and a short example script.
4. Open a pull request. Our CI checks the docs, the docstring example and the lint for you, and a maintainer reviews it.
5. Once it's merged, we announce it on pyhealth.dev and our channels, and your method is part of the benchmark.

[Tutorial 08](https://colab.research.google.com/drive/1tuiooZgK-rR50NdCG9Ylq5HNgqSUBwvE) walks through a complete contribution in Colab, and the [contribution guide](https://pyhealth.dev/how_to_contribute.html) has the checklist.

## Who we especially want to hear from

Authors of recent clinical prediction work at venues such as NeurIPS, ICML, ICLR, KDD, AAAI, CHIL, MLHC and ML4H, and in journals such as npj Digital Medicine, Nature Communications and JAMIA: EHR foundation models, medication recommendation, ICU time series, biosignals, multimodal fusion, survival and calibration methods. If your paper has public-data experiments and released code, it is likely a quick port.

Your paper earned its acceptance. Let's make it part of how the field measures progress.

*This is the last of three weekly posts on bringing your research into PyHealth. Earlier: [Your Paper Is Not Your Impact](https://pyhealth.dev/blogs/2026-10-19-your-paper-is-not-your-impact/) and [Make Your Work the Easy One to Build On](https://pyhealth.dev/blogs/2026-10-26-make-your-work-easy-to-build-on/).*
