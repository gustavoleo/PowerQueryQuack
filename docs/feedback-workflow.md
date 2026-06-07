# Feedback Workflow

Every conversion ends with a beta feedback prompt (goal section 19). Feedback
drives continuous improvement and feeds the human-supervisor workflow
(goal section 20).

## Feedback options

After every conversion, exactly these options are presented:

```
Was the conversion successful?

👍 Correct
👎 Incorrect
🛠 Help Me Fix It
```

### 👍 Correct

- Mark the conversion as successful.
- Save anonymized conversion metadata when possible.
- Do not save sensitive data unless explicitly allowed.

### 👎 Incorrect

Ask for:

1. Original Power Query code
2. Generated SQL
3. Error message
4. Expected result
5. Actual result
6. Target runtime

Then regenerate a corrected version.

### 🛠 Help Me Fix It

Start an assisted debugging flow. Ask for the **smallest** missing information
needed. Do not restart the whole conversion unless required.

## Human-supervisor workflow (goal section 20)

Every failed or uncertain conversion is exportable for human review. The product
owner is the primary human supervisor. The system supports human validation,
correction, approval, notes, and re-test after correction.

### Review record schema

Implemented as `pqquack.feedback.ReviewRecord`:

```json
{
  "conversion_id": "string",
  "language": "pt-BR | en-US",
  "target_runtime": "duckdb | gizmosql | motherduck",
  "status": "correct | incorrect | needs_help | human_review",
  "original_power_query_summary": "string",
  "generated_sql_summary": "string",
  "error_message": "string | null",
  "expected_result": "string | null",
  "actual_result": "string | null",
  "human_supervisor_notes": "string | null",
  "approved_by_human": false
}
```

## Privacy & cost

Records are **anonymized by default**. Sensitive data is not stored unless the
user explicitly allows it. Stored feedback volume is bounded for the beta
(goal section 23).

## Status

The record schema ships in Phase 0. Persistence (SQLite/DuckDB-backed) and the
UI feedback buttons are wired in Phases 6–7.
