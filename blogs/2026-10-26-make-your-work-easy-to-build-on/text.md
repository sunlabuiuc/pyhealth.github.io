---
title: "Make Your Work the Easy One to Build On"
description: "Reproducibility is not a chore for reviewers. It is how your method earns its next hundred users, and PyHealth makes it the default."
author: "Jimeng Sun & PyHealth Team"
updated: "2026-10-26"
---

*Reproducibility is not a chore you do for reviewers. It is how your method earns its next hundred users.*

Ask anyone who has tried to reproduce a clinical ML paper. The model is rarely the problem. The problem is everything around it:

- **The cohort.** Which admissions were kept? Adults only? First ICU stay or all of them?
- **The label.** Mortality within the stay, or within 30 days? Measured from admission or from 24 hours in?
- **The split.** By visit or by patient? If by visit, the same patient may sit in train and test, and the reported score is inflated.
- **The preprocessing.** Were code vocabularies and normalisation fitted on all the data, so the model already "knew" the test patients?
- **The number.** One test-set score, no interval, from one seed.

Each of these can move a result by as much as the gap between two methods. When readers can't pin them down, they can't trust the comparison, and they can't build on your work.

## What reproduction in PyHealth means

PyHealth turns those choices into code that everyone shares:

1. **Datasets** load raw tables into patient timelines the same way for everyone.
2. **Tasks** define the cohort and the label as a small, readable function, so "in-hospital mortality on MIMIC-III" means one thing.
3. **Splits** are by patient, and since PyHealth 2.1, `set_task(task, split=PatientSplit(...))` fits every vocabulary and normaliser on the training patients only.
4. **Training** is seeded, so `torch.manual_seed` alone reproduces a run.
5. **Evaluation** reports discrimination and calibration (Brier score, observed/expected ratio, calibration slope and intercept), with bootstrap confidence intervals that resample whole patients.

When your method runs through these pipes, anyone can rerun your exact experiment, change one thing, and know that the change, not the plumbing, moved the result.

## Why this pays you back

- **Trust.** A result others can rerun is a result others repeat in their related work.
- **Follow-up work.** The easiest method to extend is the one already in the library people use. Extensions cite the original.
- **Fewer emails.** "Which split did you use?" has a one-line answer: the PyHealth one.
- **Stronger reviews for the next paper.** Reviewers increasingly ask for standard baselines and confidence intervals. Your follow-up starts with both.

## It runs where researchers are

You don't need a cluster to use it. PyHealth's data pipeline runs the full MIMIC-IV in-hospital mortality task on a laptop in about 5 GB of memory, and in our [ICML 2026 benchmark](https://openreview.net/forum?id=gMLVFN9hl8) it was up to 39× faster than a pandas pipeline. A student with a laptop can reproduce your method on full-size data.

## Bring your paper in

If your method, task or dataset deserves to be easy to reproduce, let's put it in PyHealth together. Our team helps with the port and credits contributors on pyhealth.dev. Start with [Tutorial 08](https://colab.research.google.com/drive/1tuiooZgK-rR50NdCG9Ylq5HNgqSUBwvE), which walks through a complete contribution in Colab, then say hello on [Discord](https://discord.gg/mpb835EHaX).

*This is the second of three weekly posts on bringing your research into PyHealth. Last week: [Your Paper Is Not Your Impact](https://pyhealth.dev/blogs/2026-10-19-your-paper-is-not-your-impact/). Next Monday: joining the PyHealth benchmark.*
