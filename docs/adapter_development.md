# Adapter Development Guide

This document explains how to add a dataset adapter for new benchmark result
files under `data/`. It is intended for future agents and contributors who do
not already know this project.

Adapter code paths should follow the current implementation. Today the adapter
files are:

- `backend/app/adapters/base.py`
- `backend/app/adapters/aime26.py`
- `backend/app/adapters/registry.py`

Specific file paths should always be checked against the current code, but the
adapter system must keep three responsibilities separate:

- `base`: defines the standard adapter interface and normalized output shape.
- Concrete adapter: maps one dataset's raw JSONL fields into the standard shape.
- `registry`: looks up an adapter by parsed dataset name.

## 1. Adapter Purpose

Different benchmark datasets need adapters because their JSONL schemas are not
guaranteed to match. One dataset might use `id`, another `uid`, another
`problem_id`. Correctness may be stored as `exact_match`, `score`, `passed`, or
may need to be computed from output and target.

The UI and API must not depend directly on raw JSON fields. Instead, ingestion
reads each raw JSONL row, sends it through a dataset adapter, and writes a stable
normalized structure to the database.

When adding a new benchmark dataset, prefer adding a new adapter and registering
it. Do not patch frontend code to understand a dataset-specific raw field.

The adapter registration name must match the parsed dataset name. For example,
`data/Qwen3.5-4B/math500/results.jsonl` must resolve dataset `math500`, and the
registry must provide an adapter for `math500`.

## 2. Data Source Layouts

Raw data is stored under `data/` and may use either of these layouts.

### Layout A: Flat

```text
data/<model_folder>/<dataset>.jsonl
```

Example:

```text
data/Qwen3.5-4B/aime26.jsonl
```

Parsing rules:

- `model = <model_folder>`
- `dataset = <dataset>`, the JSONL file name without `.jsonl`
- `source_file = <dataset>.jsonl`

### Layout B: Nested

```text
data/<model_folder>/<dataset_folder>/<dataset_file>.jsonl
```

Examples:

```text
data/Qwen3.5-4B/aime26/aime26.jsonl
data/Qwen3.5-4B/math500/results.jsonl
data/Qwen3.5-4B/gpqa/gpqa_diamond.jsonl
```

Parsing rules:

- `model = <model_folder>`
- `dataset = <dataset_folder>`
- `source_file = <dataset_file>.jsonl`

Important: in nested layout, the dataset name comes from `dataset_folder`, not
from the JSONL file name. This matters because one dataset directory may contain
files named `results.jsonl`, `output.jsonl`, or `part-000.jsonl`.

Different models may be missing some datasets. Ingestion must tolerate missing
files and continue importing available supported files. The first design only
needs to support one dataset folder level under each model; deeper nesting is
not required.

## 3. Path Parsing Examples

| Path | Model | Dataset | Source file |
|---|---|---|---|
| `data/Qwen3.5-4B/aime26.jsonl` | `Qwen3.5-4B` | `aime26` | `aime26.jsonl` |
| `data/Qwen3.5-4B/aime26/aime26.jsonl` | `Qwen3.5-4B` | `aime26` | `aime26.jsonl` |
| `data/Qwen3.5-4B/math500/results.jsonl` | `Qwen3.5-4B` | `math500` | `results.jsonl` |
| `data/Qwen3.5-4B/gpqa/gpqa_diamond.jsonl` | `Qwen3.5-4B` | `gpqa` | `gpqa_diamond.jsonl` |

## 4. Ingestion Scanning Rules

Ingestion should scan both:

- `data/*/*.jsonl`
- `data/*/*/*.jsonl`

Rules:

- Avoid importing the exact same source more than once.
- Flat layout imports each JSONL file as one dataset source.
- Nested layout organizes imports by `model + dataset_folder`.
- Only one nested folder level is required for the first version.

### Multiple JSONL Files in One Dataset Folder

If a nested dataset contains multiple files:

```text
data/<model_folder>/<dataset_folder>/*.jsonl
```

then all JSONL files under that `model + dataset_folder` should be treated as
data shards for the same import and merged into a single `evaluation_run`.

Required final behavior:

- `source_path` may record the dataset folder path.
- `source_hash` should be computed from all JSONL file contents in that folder.
- Any shard change should trigger a new import.
- `item_id` must remain stable across imports and models. Do not prefer global
  line number as the item ID for sharded datasets.

Final design should support merging multiple JSONL shards under the same
`dataset_folder` into one run. Current implementation may only support
single-file imports; if so, this must be completed in the ingestion layer.

## 5. Fixed Dataset Configuration

Supported datasets are fixed configuration, not arbitrary files discovered at
runtime. Example:

```python
DATASETS = ["aime26", "math500", "gpqa"]
```

Rules:

- Flat layout compares the JSONL file stem against `DATASETS`.
- Nested layout compares `dataset_folder` against `DATASETS`.
- Only datasets listed in `DATASETS` and registered with an adapter can import.
- Unsupported or unregistered datasets must be explicitly skipped or reported as
  unsupported. Do not silently compute against raw fields.

## 6. Adapter Registry Matching

Adapters must be matched by parsed dataset name, not JSONL file name.

Example:

```text
data/Qwen3.5-4B/math500/results.jsonl
```

This must look up:

```text
adapter_key = math500
```

not:

```text
adapter_key = results
```

The registry key, dataset config name, and parsed dataset name should be the
same string unless the current code explicitly defines a separate aliasing
scheme.

## 7. Standard Normalized Output

Each adapter should return a normalized structure with these fields:

| Field | Required | Meaning and fallback |
|---|---:|---|
| `dataset` | Yes | Parsed dataset name, for example `aime26` or `math500`. |
| `model` | Yes | Model folder name, for example `Qwen3.5-4B`. |
| `item_id` | Yes | Stable problem ID used to align the same question across models. Prefer a dataset-provided ID. |
| `item_index` | No | Problem order within the dataset. Use `null` if unavailable. |
| `prompt` | Recommended | Prompt sent to the model. If missing, use `question` when appropriate. |
| `question` | No | Original question/problem text used for display and search. |
| `target` | No | Standard answer, expected output, rubric, or target metadata. Missing targets reduce error-analysis quality. |
| `output` | Recommended | Model's final answer or extracted output. Keep type consistent as string or `null`. |
| `raw_output` | No | Full model output, reasoning trace, or unparsed response. If missing, use `output` when useful. |
| `is_correct` | No | `true`, `false`, or `null`. Use `null` when correctness cannot be determined. |
| `output_length` | No | Number or `null`; token count is preferred over character count. |
| `inference_time` | No | Number or `null`; elapsed model inference time. |
| `original` | Yes | Full original JSON object for the row. Always preserve this for debugging. |

Current code may store `dataset` and `model` on the run/record context rather
than directly inside the adapter return object. Keep the final design in mind,
but follow the actual `base.py` interface in this repository when implementing.

## 8. Current Records Table Mapping

Adapter output maps to `records` as follows:

- `item_id -> records.item_id`
- `item_index -> records.item_index`
- `prompt -> records.prompt`
- `question -> records.question`
- `target -> records.target_json`
- `output -> records.output`
- `raw_output -> records.raw_output`
- `is_correct -> records.is_correct`
- `output_length -> records.output_length`
- `inference_time -> records.inference_time`
- `original -> records.original_json`

`model` and `dataset` are represented by `model_id` and `dataset_id` foreign
keys on `records`.

## 9. Adapter File Structure

Current adapter files:

```text
backend/app/adapters/base.py
backend/app/adapters/aime26.py
backend/app/adapters/registry.py
```

Concrete adapters should contain only dataset-specific normalization logic.
Registry code should contain dataset configuration and lookup. Ingestion should
handle path parsing, source hashes, run creation, database writes, and summary
metrics.

## 10. New Adapter Checklist

- Confirm whether the new data uses flat or nested layout.
- If flat, confirm the dataset name comes from the JSONL file name.
- If nested, confirm the dataset name comes from `dataset_folder`.
- If the same `dataset_folder` has multiple JSONL files, decide whether they
  must be merged as shards.
- Inspect representative JSONL rows for the new dataset.
- Identify the stable unique problem ID field.
- Identify prompt and question fields.
- Identify standard answer or target fields.
- Identify model output fields.
- Identify raw output fields.
- Identify correctness field or correctness computation.
- Identify output length field or fallback.
- Identify inference time field or fallback.
- Create a new concrete adapter file.
- Register the adapter in the registry.
- Ensure the adapter registration name matches the parsed dataset name.
- Update fixed `DATASETS` configuration.
- Run ingestion.
- Verify `records`.
- Verify `metrics_summary`.
- Verify metrics matrix API.
- Verify records search API.
- Verify compare API.

## 11. Field Fallback Rules

- For `item_id`, prefer a globally stable `uid` when present. If `uid` is not
  available or is known to be unreliable, use a composite such as
  `f"{pid}:{id}"`. Use plain `id`, `idx`, `index`, or line number only as a last
  resort. This is risky because compare API relies on stable `item_id`
  alignment, and local IDs can repeat across shards.
- If `item_index` is missing, use `null`.
- If `prompt` is missing, use `question` as a fallback when it represents the
  model input.
- If `question` is missing, use `null`.
- If `target` is missing, use `null`; error analysis will be less useful.
- If `output` is missing, use an empty string or `null`, but keep the choice
  consistent for that adapter.
- If `raw_output` is missing, use `output` as a fallback when helpful.
- If no correctness field exists, implement dataset-specific correctness logic
  in the adapter. If correctness cannot be determined, use `null`.
- If `output_length` is missing, prefer an output token count, then character
  length, then `null`.
- If `inference_time` is missing, use `null`.
- `original` must always store the full raw JSON row.

## 12. Additional Adapter Patterns

Recent benchmark files use several naming conventions that adapters must keep
distinct:

- `raw_output`: usually the model's raw text response.
- `raw_response`: used by BrowseComp-style files for the original response; map
  this to normalized `raw_output`.
- `response`: used by BrowseComp-ZH-style files; map this to normalized
  `raw_output`.
- `reasoning`: can be used as a `raw_output` fallback when the raw response is
  absent.

Correctness fields also vary:

- `exact_match`: integer `0` or `1`; normalize with `exact_match == 1`.
- `is_correct`: already boolean; preserve as boolean/null.
- `score`: integer `0` or `1`; normalize with `score == 1`.

For choice-like datasets such as BrowseComp, MMMLU-lite, MMLU-Pro, and
MMLU-Redux, prefer this `item_id` order:

1. `uid`
2. `f"{pid}:{id}"`
3. `id`

Do not choose local `id` first when `uid` or `pid:id` is available, especially
for datasets that may later be split into multiple JSONL shards.

## 13. AIME26 Adapter Example

Current `aime26.jsonl` mapping:

- `item_id <- id`
- `item_index <- idx`
- `prompt <- prompt`
- `question <- question`
- `target <- target`
- `output <- output`
- `raw_output <- raw_output`
- `is_correct <- exact_match == 1`
- `output_length <- output_token_len`
- `inference_time <- output_time`
- `original <- raw full-line JSON`

Example normalization code:

```python
def normalize(row: dict, model: str, dataset: str) -> dict:
    return {
        "dataset": dataset,
        "model": model,
        "item_id": str(row["id"]),
        "item_index": row.get("idx"),
        "prompt": row.get("prompt"),
        "question": row.get("question"),
        "target": row.get("target"),
        "output": row.get("output"),
        "raw_output": row.get("raw_output"),
        "is_correct": None
        if row.get("exact_match") is None
        else int(row["exact_match"]) == 1,
        "output_length": row.get("output_token_len"),
        "inference_time": row.get("output_time"),
        "original": row,
    }
```

This snippet is intentionally small. The concrete adapter in the codebase may
return a dataclass or model instead of a dict; use the current `base.py`
contract.

## 14. Current Choice-Like Dataset Mappings

### BrowseComp

- Dataset key: `browsecomp`
- Filename aliases: `browsecomp_score.jsonl`, `browsecomp.jsonl`
- `item_id <- uid`, fallback `pid:id`, fallback `id`
- `item_index <- id`
- `prompt <- prompt`
- `question <- question`
- `target <- targets`
- `output <- model_extracted_answer`, fallback `output`
- `raw_output <- raw_response`, fallback `reasoning`, fallback `output`
- `is_correct <- is_correct`
- `output_length <- output_token_len`
- `inference_time <- output_time`
- `original <- raw full-line JSON`

### BrowseComp-ZH

- Dataset key: `browsecomp-zn`
- Filename aliases: `browsecomp_zh_score.jsonl`, `browsecomp_zh.jsonl`,
  `browsecomp-zh.jsonl`
- `item_id <- uid`, fallback `pid:id`, fallback `id`
- `item_index <- id`
- `prompt <- prompt`
- `question <- question`
- `target <- targets`; this may be an object and should be stored as-is.
- `output <- output`
- `raw_output <- response`, fallback `output`
- `is_correct <- score == 1`
- `output_length <- output_token_len`
- `inference_time <- output_time`
- `original <- raw full-line JSON`

### MMMLU-lite

- Dataset key: `MMMLU-lite`
- Filename aliases: `mmmlu_lite.jsonl`, `MMMLU-lite.jsonl`
- `item_id <- uid`, fallback `pid:id`, fallback `id`
- `item_index <- id`
- `prompt <- prompt`
- `question <- question`; keep multilingual text unchanged.
- `target <- targets`
- `output <- output`
- `raw_output <- raw_output`, fallback `output`
- `is_correct <- exact_match == 1`
- `output_length <- output_token_len`
- `inference_time <- output_time`
- `original <- raw full-line JSON`

### MMLU-Pro

- Dataset key: `MMLU-Pro`
- Filename aliases: `mmlu_pro.jsonl`, `MMLU-Pro.jsonl`
- `item_id <- uid`, fallback `pid:id`, fallback `id`
- `item_index <- id`
- `prompt <- prompt`
- `question <- question`
- `target <- targets`
- `output <- output`
- `raw_output <- raw_output`, fallback `output`; preserve LaTeX as-is.
- `is_correct <- exact_match == 1`
- `output_length <- output_token_len`
- `inference_time <- output_time`
- `original <- raw full-line JSON`

### MMLU-Redux

- Dataset key: `MMLU-Redux`
- Filename aliases: `mmlu.jsonl`, `MMLU-Redux.jsonl`
- This project currently maps `mmlu.jsonl` to `MMLU-Redux` because the category
  configuration already includes `MMLU-Redux`.
- `item_id <- uid`, fallback `pid:id`, fallback `id`
- `item_index <- id`
- `prompt <- prompt`
- `question <- question`
- `target <- targets`
- `output <- output`
- `raw_output <- raw_output`, fallback `output`
- `is_correct <- exact_match == 1`
- `output_length <- output_token_len`
- `inference_time <- output_time`
- `original <- raw full-line JSON`

## 15. Verification

After adding or changing an adapter:

1. Run ingestion:

   ```bash
   cd backend
   python -m app.ingest --data-dir ../data
   ```

2. Check `evaluation_runs` for a successful/completed run for the dataset.
3. Check `records` contains rows for the expected `model + dataset`.
4. Check `metrics_summary` has `accuracy`, `avg_output_length`, and
   `avg_inference_time` where the source data supports them.
5. Call the metrics matrix API and confirm the homepage can see the new dataset.
6. Call the records search API and confirm wrong-answer search works.
7. Call the compare API and confirm two-model comparison aligns records by
   `item_id`.

## 16. Common Mistakes

- Confusing dataset name with JSONL file name, especially using `results` as the
  dataset for nested `math500/results.jsonl`.
- Creating an adapter but not registering it.
- Forgetting to update fixed `DATASETS` configuration.
- Using unstable `item_id`, causing model comparisons to fail alignment.
- Creating multiple runs for sharded files that should be one run.
- Computing `source_hash` from only one shard, so other shard changes do not
  trigger re-import.
- Returning `is_correct` as `0`, `1`, or string instead of boolean or `null`.
- Returning `output_length` or `inference_time` as strings instead of numbers or
  `null`.
- Not preserving the full original JSON row.
- Re-importing the same source hash instead of skipping it.
- Failing ingestion when a model is missing one supported dataset.
