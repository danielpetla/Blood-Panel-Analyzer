# Blood-Panel-Analyzer

A small Python pipeline that turns messy blood-panel data into validated,
structured records and uses an LLM to flag well-documented patterns,
with an evaluation suite that tests whether the model abstains when data is missing.

> ⚠️ Demo project on synthetic data only. Not a medical device and not clinically validated.

## What it does
1. **Parses** CSV/JSON panels with mixed units, decimal commas and inconsistent marker names
2. **Validates** them against a pydantic schema (rejects invalid input instead of guessing)
3. **Analyses** the normalised panel with an LLM, returning structured JSON where every flag cites the input values behind it
4. **Evaluates** the output on hand-labelled cases: schema validity, flag accuracy, abstention on incomplete data, and a check that cited values exist in the input

## Results
(table from run_eval.py goes here once built)

## Limitations
Marker numbers containing "<" or ">" are not supported
(be specific: synthetic data, small case set, reference ranges from public sources, no clinical validation)
