# Accelerator Spec Candidates

Crawler and extractor output should land here before it becomes an observation
or resolved specification.

Candidate files use YAML and contain proposed records only. They do not change
accepted values until reviewed by a resolver or human reviewer.

## Candidate Shape

```yaml
candidates:
  - candidate_id: candidate-source-sku-field
    source_id: nvidia-h200-product-page
    sku_hint: NVIDIA H200 SXM
    field: memory_capacity
    raw_value: "141GB"
    normalized_value: 141
    normalized_unit: GB
    source_rank: S1
    confidence: high
    review_status: pending
    notes: Extracted from official product page.
```

## Review Rules

- S1 candidates can become observations when field extraction is unambiguous.
- S2 candidates update cloud offering fields, not single-card specs.
- S3 benchmark candidates stay benchmark-specific.
- S4 candidates stay observed/runtime-specific.
- S5 candidates require human review before resolution.
