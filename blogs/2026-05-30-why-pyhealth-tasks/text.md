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

The problem with that instinct is that it assumes a researcher takes one fixed path through their data. Define your features once, and you're done. But that's not how research actually works, even if the average researcher's codebase doesn't reflect it. 

Preprocessing is an *ever-changing process*. You're constantly refining what features to include, how to define labels, what time windows to use. And once your dataset is too large to fit in memory, which happens fast with EHR data, iterating on that monolithic function means reimplementing memory-disk tricks every single time you want to try something different. Not to mention, a 1000-line `preprocess_data.py` is genuinely painful to read and debug.

---

## The Two-Step Solution

When you strip away all the engineering, every data preprocessing pipeline really comes down to two questions: what is your data, and how do you use it to do something meaningful? PyHealth just formalizes that into two explicit pieces.

The names are intentional. A *dataset* is just a set of data: it describes what exists and how to access it. A *task* is what you're trying to do with that data: the clinical question you're asking, and all the logic that goes into answering it.

PyHealth makes this split explicit:

1. **`pyhealth.datasets`**: Describes your raw data as a collection, what patients are in it, what events exist, and where it lives (and how to read it, if it's not already tabular). All the complexity behind actually working with that data, file I/O, memory management, caching, is handled by PyHealth automatically. You just tell us what's there.
2. **`pyhealth.tasks`**: Defines how you use that data to do something. This is where your research decisions live: inclusion and exclusion criteria, which features go in, what the output label is, how you window time-series events. Every design choice that turns raw records into a model-ready sample belongs here.

To make this concrete, say you want to predict diabetes. Your `pyhealth.datasets` step is just declaring what's in your pool of EHR records: which patients are there, their demographics like age and gender, their weight, and their glucose lab results, along with where those records actually live. You're not deciding what matters yet, only describing what exists.

Once defined, that dataset stays static. Nothing below this point changes how the data is read or stored. Everything downstream now lives in your `pyhealth.tasks` step.

So how do we actually decide which features to use? That question is the whole job of `pyhealth.tasks`. You pick the features you want, say glucose, age, gender, and weight, and you define the label: does this patient go on to develop diabetes? And because a task is just an object, those choices become simple parameters. You can flip features on and off with boolean flags right in the task, so a whole feature ablation study (glucose only, glucose plus weight, all of them) is just a handful of one-line task definitions you can run and cross-compare at once. One task might use a single glucose value, another might reframe glucose as a sequence of readings over time and turn the whole thing into a time-series problem. The underlying pool of records never moves; you're just asking sharper questions of the same static dataset.

---

## Why This Separation Matters

**Reproducibility.** Because the dataset is static, any change in training performance or label distributions is *entirely* the result of logic you changed in your task. You're not chasing bugs that live somewhere in a shared loading-and-transformation blob.

**Parallelism.** Each task operates on a fixed, already-loaded dataframe. That means you can define multiple tasks and run them as parallel jobs, comparing how different feature engineering choices or label definitions affect your pipeline without re-loading data each time.

**Iteration speed.** Swap out your task logic, re-run, compare. And because task processing itself is parallelized and cached, you're not just saving mental overhead, the preprocessing actually runs faster too. The annoying engineering is already handled.

---

## Example in Action

Here's that two-step split in practice, using two tasks that already ship with PyHealth: mortality prediction and drug recommendation.

First, the reuse. You define the data once, then point as many tasks at it as you like:

```python
from pyhealth.datasets import MIMIC4Dataset
from pyhealth.tasks import MortalityPredictionMIMIC4, DrugRecommendationMIMIC4

base = MIMIC4Dataset(                       # define the data once
    ehr_root="...",
    ehr_tables=["patients", "admissions", "diagnoses_icd",
                "procedures_icd", "prescriptions"],
)

mortality = base.set_task(MortalityPredictionMIMIC4())   # same call,
drug_rec  = base.set_task(DrugRecommendationMIMIC4())     # different task
```

The dataset is built and cached once. Each task is the exact same one-line `set_task`, just with a different task object. Swapping your research question never touches the data layer.

Now the part that makes this pleasant to live with: a task is genuinely easy to read. Here's a trimmed version of the mortality task:

```python
class MortalityPredictionMIMIC4(BaseTask):
    task_name: str = "MortalityPredictionMIMIC4"
    input_schema:  Dict[str, str] = {"conditions": "sequence",
                                      "procedures": "sequence",
                                      "drugs": "sequence"}
    output_schema: Dict[str, str] = {"mortality": "binary"}

    def __call__(self, patient):
        samples = []
        admissions = patient.get_events(event_type="admissions")
        for i in range(len(admissions) - 1):
            # ... pull this visit's conditions / procedures / drugs
            # ... derive the mortality label from the next admission
            samples.append({"conditions": conditions,
                            "procedures": procedures,
                            "drugs": drugs,
                            "mortality": mortality_label})
        return samples
```

A few things fall out of this structure:

**The contract is the first thing you read.** `input_schema` and `output_schema` sit right at the top and tell you exactly what goes in and what comes out, before you read a single line of logic. Mortality maps three `sequence` inputs to one `binary` label. Drug recommendation instead maps `nested_sequence` visit history to a `multilabel` output. Each schema value names a reusable processor that turns raw codes into model-ready tensors for you, and you can always drop to a custom one when a field is too complex.

**All the logic funnels through one `__call__(patient)`.** Every cohort filter, label definition, and time window lives in that single per-patient method. If a sample comes out wrong, there is exactly one place to look, instead of hunting through a 1000-line `preprocess_data.py`.

**You write it for one patient, PyHealth runs it for all of them.** `set_task` fans `__call__` across every patient automatically, so you never write the parallelism, batching, or I/O yourself.

If you want to see the real, untrimmed code, here are the full files: [mortality prediction](https://github.com/sunlabuiuc/PyHealth/blob/master/pyhealth/tasks/mortality_prediction.py), [drug recommendation](https://github.com/sunlabuiuc/PyHealth/blob/master/pyhealth/tasks/drug_recommendation.py), the [base task class](https://github.com/sunlabuiuc/PyHealth/blob/master/pyhealth/tasks/base_task.py), and [`set_task`](https://github.com/sunlabuiuc/PyHealth/blob/master/pyhealth/datasets/base_dataset.py) where the parallelization happens.

Want the whole thing end to end? Try the [runnable Colab notebook](https://colab.research.google.com/drive/1QB0acnGb-wOuK53UNSgHxjCW74QeYjUl?usp=sharing), or keep reading below for docs and guides.

---

## Where to Learn More

Every built-in task follows this same shape, so once you've read one, you've read them all. For full documentation and more hands-on examples, see:

- [pyhealth.dev](https://pyhealth.dev), the PyHealth project site
- [pyhealth.tasks API reference](https://pyhealth.readthedocs.io/en/latest/api/tasks.html)
