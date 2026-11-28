# JagSi combined health summary model card

The ranking prototype below is the baseline. The subsequent [local language-model experiment](local-llm-daily-brief.md) records adapter training, dashboard integration and held-out results.

## Task and evidence

The offline prototype writes an Indonesian caregiver summary from reviewed MCU rows and timestamped watch observations for one person. The caller supplies the lab date, watch timestamp, simulation status, stale status and active alert state. Clinical interpretation stays with the source. A flag is attributed to the lab, an unknown date is visible, and an absent report gets its own sentence. Only pass reviewed rows. This function does not authenticate a patient, confirm an OCR result or detect a fall.

## Training method

We separated two decisions that have different costs. Choosing which sentence opens a summary is an editorial preference. Changing a decimal, a comparator or a unit can change the meaning of the result. The locally fitted model makes the first decision. A controlled renderer copies source fields for the second. No external inference service receives the readings.

Six sentence types produce fifteen possible unordered comparisons. Ten distinct hand-authored preferences formed the training set. For each pair we subtracted the second type's one-hot vector from the first, then added its inverse with the opposite label. These twenty training rows represent ten independent preferences. L2-regularized logistic regression learns one score per type. Sorting the available blocks by score generates the reading order. The model does not learn medical ranges, prose generation or patient outcomes.

## Evaluation and reproduction

Five distinct comparisons were reserved for testing. The model recovered all five editorial preferences. Random guessing has an expected success rate of one half per pair. A fixed editorial priority list can also solve this task exactly. This experiment establishes reproducibility and gives a baseline for learning future caregiver preferences. It supplies no evidence of superiority over that list.

The renderer passed 64 fixture combinations across lab flag or absence, watch availability, simulation, stale status and active alert. Assertions check alert placement, dates, source labels, units, exact comparator and value, and high/low attribution. All cases share fixture wording. They do not represent 64 independent patients, reports or OCR evaluations.

From the repository root in PowerShell with NumPy and scikit-learn installed:

~~~powershell
python backend/ml/train_summary_order.py
$env:PYTHONPATH='backend'
python -m unittest discover -s backend/app/tests -p test_evidence_summary.py
~~~

## Research and path to language-model fine-tuning

Van Veen et al. compared in-context examples and quantized low-rank fine-tuning for clinical text summarization. Their evaluation included physician judgments of correctness, completeness and concision and review of fabricated details. For JagSi, copy this evaluation structure and explicitly score separation of historical MCU results from current watch readings. Their performance estimates concern different tasks and populations. [Primary study](https://www.nature.com/articles/s41591-024-02855-5)

A separate clinical dialogue study evaluated models with different training histories, including fine-tuning on anonymized clinical dialogues. Domain-matched examples matter here because a lab flag, a simulator value and an active alert require different attribution even when their numbers look similar. [Primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11707028/)

For a generative successor, collect consented, de-identified paired reports and watch windows with caregiver-facing Indonesian reference summaries. Assign each sentence evidence IDs. Record disagreements about emphasis separately from transcription errors. Split by person before creating paraphrases or overlapping windows. Reserve unseen report layouts and device sessions for testing. Compare the current renderer, a prompted baseline and a locally fine-tuned instruction model on the identical frozen test set. Tune adapter size and training duration only on validation patients. Record model and dataset revisions, seeds, learning curves and held-out subgroup sizes.

Before live use, independently check source attribution, numeric precision, unsupported claims, missed alerts, excessive length on multi-page reports and caregiver comprehension. Have qualified reviewers grade blinded outputs and adjudicate critical errors. Report patient-level uncertainty and failures alongside averages. Patient-linked evidence persistence, live dashboard wiring, clinician-written reference summaries and independent clinical review are outstanding.
