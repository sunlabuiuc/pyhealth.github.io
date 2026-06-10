---
title: "FHIR Data Loading Comes to PyHealth"
description: "PyHealth now loads FHIR data natively, starting with MIMIC-IV-on-FHIR and an EHRMamba pipeline. It is early, so we want your bug reports."
author: "John Wu"
updated: "2026-06-07"
---

**TL;DR:** PyHealth can now read FHIR. A new `FHIRDataset` streams FHIR resources into clean, flat tables driven by a single YAML config, and `MIMIC4FHIR` gives you a turnkey loader for MIMIC-IV-on-FHIR. This is fresh and lightly tested, so we would love your help.

---

## What's new

FHIR is the language healthcare systems use to exchange data, and until now PyHealth could not read it directly. That changes today.

[`FHIRDataset`](https://pyhealth.readthedocs.io/en/latest/api/datasets/pyhealth.datasets.FHIRDataset.html) streams NDJSON FHIR resources from disk and flattens each resource type into a tidy table, all controlled by one declarative YAML config. On top of it, `MIMIC4FHIR` is the first ready-to-use loader: point it at a MIMIC-IV-on-FHIR export and it handles the rest, with the same caching, parallelism, and `set_task` flow you already use everywhere else in PyHealth.

---

## What works today

The bundled MIMIC4FHIR config covers six FHIR resources: Patient, Encounter, Condition, Observation, MedicationRequest, and Procedure. And it runs end to end: you can take MIMIC-IV-on-FHIR straight into an `EHRMambaCEHR` model for mortality prediction.

One caveat worth stating plainly: we have only tested against the [MIMIC-IV-on-FHIR demo dataset](https://physionet.org/content/mimic-iv-fhir/2.1/). Publicly available FHIR datasets are scarce, so that demo is, realistically, the one source we could validate against.

```python
from pyhealth.datasets import MIMIC4FHIR, get_dataloader, split_by_patient
from pyhealth.models import EHRMambaCEHR
from pyhealth.tasks.mpf_clinical_prediction import MPFClinicalPredictionTask
from pyhealth.trainer import Trainer


def main() -> None:
    dataset = MIMIC4FHIR(root="/path/to/mimic-iv-fhir")
    samples = dataset.set_task(MPFClinicalPredictionTask())   # same set_task pattern
    train, val, test = split_by_patient(samples, [0.7, 0.1, 0.2])

    train_loader = get_dataloader(train, batch_size=8, shuffle=True)
    val_loader = get_dataloader(val, batch_size=8, shuffle=False)

    vocab_size = samples.input_processors["concept_ids"].vocab.vocab_size
    model = EHRMambaCEHR(dataset=samples, vocab_size=vocab_size, embedding_dim=32)

    trainer = Trainer(model=model, metrics=["roc_auc", "pr_auc"])
    trainer.train(train_dataloader=train_loader, val_dataloader=val_loader, epochs=2)


if __name__ == "__main__":
    main()
```

A full runnable script lives at `examples/mimic4fhir_mpf_ehrmamba.py` in the repo.

---

## Write your own FHIRDataset

MIMIC4FHIR is just `FHIRDataset` pointed at one YAML config. Any other FHIR export, a BigQuery dump, a Synthea bundle, your hospital's extract, works the same way: you write a YAML that describes the export, and PyHealth handles the streaming, flattening, and caching.

A config has three sections.

**1. `glob_patterns`**: which NDJSON files on disk to read. If your export splits resources into per-type files, list them so PyHealth can skip the ones you do not need. If everything lives in one bundle, you can leave this out and it defaults to reading every `.ndjson.gz`.

```yaml
glob_patterns:
  - "**/Patient*.ndjson.gz"
  - "**/Condition*.ndjson.gz"
```

**2. `resource_specs`**: how to turn one FHIR JSON document into a flat row. Keyed by FHIR `resourceType`, each entry names an output `table` and its `columns`. For every column you give an ordered list of JSON paths in `locate`, and the first path that resolves wins (this is how FHIR choice-types like `onset[x]` are handled). An optional `transform` maps the located value to a clean string, and `required: true` drops the resource when the value is missing.

```yaml
resource_specs:
  Condition:
    table: condition
    columns:
      patient_id:   { locate: ["subject.reference"], transform: ref_id, required: true }
      encounter_id: { locate: ["encounter.reference"], transform: ref_id }
      event_time:   { locate: ["onsetDateTime", "onsetPeriod.start", "recordedDate"] }
      concept_key:  { locate: ["code"], transform: coding_key }
```

A `transform` is just a named function that takes whatever `locate` found, a raw chunk of FHIR JSON, and turns it into a clean, flat string for the column. FHIR rarely stores values as plain strings: a patient pointer is a reference object, a diagnosis is a nested coding, a flag is a JSON boolean. Transforms smooth those shapes out so your tables hold simple values. PyHealth ships five:

- **`identity`**: passes the value through, stringifying scalars. This is the default when you omit `transform`, so `"2026-06-07"` stays `"2026-06-07"`.
- **`ref_id`**: pulls the bare id out of a FHIR reference, dropping the `ResourceType/` prefix. Use it for any cross-resource link like `subject` or `encounter`, so `{"reference": "Patient/10000032"}` becomes `"10000032"`.
- **`coding_key`**: collapses a CodeableConcept into a `system|code` string from its first coding. Use it for diagnoses, procedures, and observations, so an ICD-10 code object becomes something like `"icd-10|E11"`.
- **`bool_norm`**: normalizes a JSON boolean, or a `"true"`/`"false"` string, into a clean `"true"` or `"false"` (and nothing when it is absent).
- **`med_concept`**: handles a MedicationRequest's `medication[x]` choice-type, using the codeable concept when it is present and falling back to a `MedicationRequest/reference|<id>` string otherwise.

Need a shape these do not cover? Register your own function once in `pyhealth/datasets/fhir/utils.py` and reference it by name in your YAML, exactly like the built-ins.

**3. `tables`**: how those flat rows become events. Each entry points at the output table, names the `patient_id` and `timestamp` columns, and lists the `attributes` to surface, which then show up on `patient.get_events(...)` downstream, exactly like every other PyHealth dataset.

```yaml
tables:
  condition:
    file_path: "condition.parquet"
    patient_id: "patient_id"
    timestamp: "event_time"
    attributes: ["encounter_id", "event_time", "concept_key"]
```

Then point `FHIRDataset` at it and you are done:

```python
from pyhealth.datasets.fhir import FHIRDataset


def main() -> None:
    dataset = FHIRDataset(root="/path/to/export", config_path="my_fhir.yaml")


if __name__ == "__main__":
    main()
```

The bundled [`mimic4fhir.yaml`](https://github.com/sunlabuiuc/PyHealth/blob/master/pyhealth/datasets/fhir/configs/mimic4fhir.yaml) is a complete, commented worked example. The fastest way to write your own is to copy it and adjust the paths and resources.

---

## Future things planned (if there's interest)

This is just the start. The big one on our list is faster FHIR parsing, the current streamer is correct but leaves real speedups on the table, and we would love to make large exports process noticeably quicker. If FHIR support is useful to you, let us know, since interest is what tells us where to spend the time.

---

## Hit a bug?

If you try the FHIR loader on your own data, or push it past mortality prediction, you will probably find something broken. Please tell us. Post anything you run into in the [FHIR bug thread](https://github.com/sunlabuiuc/PyHealth/issues/1157) so we can fix it and broaden support faster.

Prefer to talk it through? [Join our Discord community](https://discord.gg/mpb835EHaX) for direct support and feedback. It is the fastest way to reach us and shape where FHIR support goes next.

---

## Acknowledgements

Thanks to PyHealth contributor Evan Febrianto for helping lay the groundwork for this approach.
