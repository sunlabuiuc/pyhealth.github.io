---
title: "Faster, Cleaner Healthcare Data Preprocessing with PyHealth"
description: "pyhealth.tasks separates static data loading from dynamic transformation logic, so you can iterate on preprocessing pipelines quickly without re-loading gigabytes of data every time."
author: "John Wu"
updated: "2026-05-30"
---

**TL;DR:** `pyhealth.tasks` makes your life easier when you want to quickly iterate on data preprocessing pipelines over large patient datasets.

---

## The Problem with One Big Preprocessing Function/Module

One of the headline features of PyHealth is its memory efficiency. Processing 100 million patient events on MacOS takes only ~5.43 GB of RAM [(Wu et al., 2026)](https://arxiv.org/pdf/2601.16414), low enough that serious data work is possible on a laptop, assuming you have enough storage space.

But when researchers first try to use PyHealth, they run into something unexpected: you have to define *two* separate modules, a `pyhealth.dataset` and a `pyhealth.task`. This confuses almost everyone, because most research repos have some version of a `data.py`, `dataset.py`, or `create_dataset.py` that does everything in one place.

The problem with that instinct is that it assumes a researcher takes one fixed path through their data. Define your features once, and you're done. But that's not how research actually works.

Preprocessing is an *ever-changing process*. You're constantly refining what features to include, how to define labels, what time windows to use. And once your dataset is too large to fit in memory, which happens fast with EHR data, iterating on that monolithic function means reimplementing memory-disk tricks every single time you want to try something different. Not to mention, a 1000-line `preprocess_data.py` is genuinely painful to read and debug.

---

## The Two-Step Solution

PyHealth splits data processing into two conceptually distinct steps:

1. **`pyhealth.datasets`**: Define what's in your raw data (and how to read it, if it's not already tabular, parallel I/O, memory management, and caching are handled for you either way).
2. **`pyhealth.tasks`**: Define how to transform that loaded data into something usable for a specific experiment.

Once defined, a dataset stays static. Everything downstream (labels, features, time windows) lives in your task.

---

## Why This Separation Matters

**Reproducibility.** Because the dataset is static, any change in training performance or label distributions is *entirely* the result of logic you changed in your task. You're not chasing bugs that live somewhere in a shared loading-and-transformation blob.

**Parallelism.** Each task operates on a fixed, already-loaded dataframe. That means you can define multiple tasks and run them as parallel jobs, comparing how different feature engineering choices or label definitions affect your pipeline without re-loading data each time.

**Iteration speed.** Swap out your task logic, re-run, compare. And because task processing itself is parallelized and cached, you're not just saving mental overhead, the preprocessing actually runs faster too. The annoying engineering is already handled.

---

## Where to Learn More

This post won't go into the code specifics of writing a `pyhealth.task`. For documentation and hands-on examples, see:

- [pyhealth.dev](https://pyhealth.dev), the PyHealth project site
- [pyhealth.tasks API reference](https://pyhealth.readthedocs.io/en/latest/api/tasks.html)
