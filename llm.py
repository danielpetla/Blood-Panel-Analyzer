from typing import Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from errors import LLMOutputError

MODEL = "gemini-3.8-flash"

PATTERNS = ("dysglycemia", "atherogenic_dyslipidemia", "iron_deficiency")

# Thresholds are written out here on purpose. Don't import them from
# generate.py, or the analyzer would share the answer key it is graded on.
SYSTEM_PROMPT = """You analyze blood panel results for a demo project.
Synthetic data only. The rules below are simplified demo rules, not clinical advice.

Patterns and rules:
- dysglycemia: flagged if glucose_fasting >= 100 mg/dl AND hba1c >= 5.7 %.
  Needs: glucose_fasting, hba1c.
- atherogenic_dyslipidemia: flagged if triglycerides >= 150 mg/dl AND hdl < 40 mg/dl.
  Needs: triglycerides, hdl.
- iron_deficiency: flagged if ferritin < 30 ng/ml.
  Needs: ferritin.

For each pattern, choose exactly one status:
- "insufficient_data": at least one needed marker is NOT in the results.
  Never assume a missing marker is normal.
- "flagged": all needed markers are present and the rule is met.
- "not_flagged": all needed markers are present and the rule is not met.

Use only the results provided. Give a short reason for each pattern."""

class PatternResult(BaseModel):
    status: Literal["flagged", "not_flagged", "insufficient_data"]
    reason: str

class PanelResult(BaseModel):
    dysglycemia: PatternResult
    atherogenic_dyslipidemia: PatternResult
    iron_deficiency: PatternResult

def format_results(accepted):
    if not accepted:
        return "(no valid results)"
    return "\n".join(f"{r.marker}: {r.value} {r.unit}" for r in accepted)

def parse_text(text):
    """Validate the model's JSON text and return {pattern: {"status", "reason"}}."""
    if not text:
        raise LLMOutputError("Empty response")
    try:
        parsed = PanelResult.model_validate_json(text)
    except ValidationError as e:
        raise LLMOutputError(f"Malformed output: {e}") from e
    return {name: getattr(parsed, name).model_dump() for name in PATTERNS}

def analyze(accepted, client=None, model=MODEL):
    """Return {pattern: {"status": ..., "reason": ...}} for a list of LabResults."""
    client = client or genai.Client()   # reads GEMINI_API_KEY (or GOOGLE_API_KEY)
    response = client.models.generate_content(
        model=model,
        contents=f"Panel results:\n{format_results(accepted)}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            response_mime_type="application/json",
            response_schema=PanelResult,
        ),
    )
    return parse_text(response.text)