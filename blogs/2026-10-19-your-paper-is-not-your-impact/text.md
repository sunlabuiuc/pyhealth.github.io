---
title: "Your Paper Is Not Your Impact"
description: "In the age of AI, publication alone no longer carries a method. Impact comes from being easy to use, and PyHealth can take your work there."
author: "Jimeng Sun & PyHealth Team"
updated: "2026-10-19"
---

*Why publication alone no longer carries a method, and what does.*

A decade ago, a strong paper at a good venue was enough. People read it, re-implemented it, and cited it. The paper was the product.

That is no longer how methods spread. NeurIPS, ICML, KDD, AAAI, CHIL, MLHC and the journals now publish more AI-for-health papers each year than any researcher can read. AI assistants summarise them faster than we can open the PDF. The bottleneck is no longer *finding* your method. It is *using* it.

And using a clinical ML method is hard. Before anyone can try yours, they have to:

- get credentialed access to the same data (MIMIC, eICU, a hospital extract)
- reproduce your cohort, your label definition and your preprocessing
- guess at the details the paper left out: which codes, which time window, which split
- re-implement your model, or untangle a research repository written for one deadline
- rebuild the baselines you compared against, so the comparison still means something

Most people stop at the second bullet. They cite you, compare against an approximation of your method, or skip it.

## Impact now comes from being easy to use

The methods that shape a field are the ones others can run in an afternoon. They become defaults, baselines and building blocks, and each new paper that uses them adds to their reach. That is a distribution problem, not a writing problem, and it is the one PyHealth was built to solve for healthcare AI.

PyHealth is the open-source Python toolkit for clinical predictive modeling. It has 25+ dataset loaders, 50+ ready-made clinical tasks and 50+ models behind one API. Researchers at more than 60 institutions have used it in published work; we found [81 papers that use or cite it](https://pyhealth.dev/citations.html). When your method lives in PyHealth, someone can run it on MIMIC, eICU or EHRSHOT with a few lines of code:

```python
model = YourModel(dataset=train_ds)
trainer = Trainer(model=model, metrics=["pr_auc", "roc_auc"])
trainer.train(train_loader, val_loader, epochs=50)
```

No cohort rebuilding. No preprocessing archaeology. Your exact method, on their data, today.

## What changes for you

- **Reach.** Your method shows up where people already work, next to the models they already use.
- **Citations that come from use.** Every paper that runs your method through PyHealth cites your paper, not an approximation of it.
- **A fair comparison.** Your method is benchmarked against the others on the same pipelines, patient splits and metrics, so the numbers people quote are the right ones.
- **Longevity.** Research code decays when its author graduates. Code in PyHealth is tested and maintained with the library.

## The next step after acceptance

You already did the hard part: the idea, the experiments, the paper. Putting it into PyHealth is usually a model or task class, a test and a short example, and our team will help you with the port.

If you have published a clinical prediction method, task or dataset in the last year or two, we would like to hear from you. Message us on [Discord](https://discord.gg/mpb835EHaX), or start from the [contribution guide](https://pyhealth.dev/how_to_contribute.html).

In the age of AI, the paper is the beginning. Make your work the one people can use.

*This is the first of three weekly posts on bringing your research into PyHealth. Next Monday: how to make your work the easy one to build on.*
