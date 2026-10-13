from anthropic import Anthropic

MODEL = "claude-sonnet-5-5"

PATTERNS = ("dysglycemia", "atherogenic_dyslipidemia", "iron_deficiency")
STATUSES = ("flagged", "not_flagged", "insufficient_data")

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

TOOL = {
    "name": "report_patterns",
    "description": "Report the status of every pattern.",
    "input_schema": {
        "type": "object",
        "properties": {
            name: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": list(STATUSES)},
                    "reason": {"type": "string"},
                },
                "required": ["status", "reason"],
            }
            for name in PATTERNS
        },
        "required": list(PATTERNS),
    },
}

class LLMOutputError(ValueError):
    """Raised when the LLM output is not valid JSON or does not match the expected schema."""

def format_results(accepted):
    if not accepted:
        return "No results were accepted."
    return "\n".join(f"{r.marker}: {r.value} {r.unit}" for r in accepted)

def parse_response(response):
    block = next((b for b in response.content if b.type == "tool_use"), None)
    if block is None:
        raise LLMOutputError("No tool call in response")

    data = block.input
    out = {}
    for name in PATTERNS:
        entry = data.get(name)
        if not isinstance(entry, dict):
            raise LLMOutputError(f"Missing pattern: {name}")
        status = entry.get("status")
        if status not in STATUSES:
            raise LLMOutputError(f"Bad status for {name}: {status!r}")
        out[name] = {"status": status, "reason": str(entry.get("reason", ""))}
    return out

def analyze(accepted, client=None):
    """Return {pattern: {"status": ..., "reason": ...}} for a list of LabResults"""
    client = client or Anthropic()  # reads Anthropic_API_KEY
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "report_patterns"},
        messages=[{
            "role": "user",
            "content": f"Panel results: \n{format_results(accepted)}",
        }]
    )
    return parse_response(response)