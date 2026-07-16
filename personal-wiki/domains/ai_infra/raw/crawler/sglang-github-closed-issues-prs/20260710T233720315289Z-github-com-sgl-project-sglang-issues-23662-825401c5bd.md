---
source_id: sglang-github-closed-issues-prs
title: '/v1/responses: previous_response_id injects system instructions instead of
  assistant output in conversation history'
canonical_url: https://github.com/sgl-project/sglang/issues/23662
captured_at: '2026-07-10T23:37:20.315289+00:00'
content_hash: 825401c5bd4c8478aab16564a028961e59713a72c004e6aa7dc6431a0c16a842
---
# /v1/responses: previous_response_id injects system instructions instead of assistant output in conversation history

URL: https://github.com/sgl-project/sglang/issues/23662
State: closed
Labels: 
Closed at: 2026-07-10T01:24:41Z
Merged at: 

### Describe the bug

The `/v1/responses` endpoint's `_construct_input_messages()` method in `serving_responses.py` incorrectly constructs the conversation history when using `previous_response_id` for multi-turn conversations.

When chaining responses, the code is supposed to inject the previous assistant's output into the message history. Instead, it:

1. Uses `role: "system"` instead of `role: "assistant"`
2. Passes `request.instructions` (the system prompt) instead of the actual `content.text` from the previous assistant output

This means the model never sees its own previous response during multi-turn conversations — it sees duplicated system prompts instead. The bug is in lines 614-620 of `serving_responses.py`:

```python
# Current (buggy):
for content in output_item.content:
    messages.append(
        {
            "role": "system",              # ← should be "assistant"
            "content": request.instructions, # ← should be content.text
        }
    )
```

This bug affects **only the non-Harmony code path** (open-source models). The Harmony path (`_construct_input_messages_with_harmony`) has its own separate logic.

### Reproduction

The following script asks the model to compose a creative phrase in Turn 1, then asks it to repeat what *it* said in Turn 2 using `previous_response_id`. The model repeats the system instructions instead of its Turn 1 output, confirming the bug.

<details>
<summary><code>repro_responses_multi_turn.py</code></summary>

```python
import argparse, json, sys, requests

def main(args):
    base = args.base_url.rstrip("/")

    # Turn 1: Ask the model to invent a phrase
    r1 = requests.post(f"{base}/v1/responses", json={
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "input": "Compose a unique, creative three-word phrase. Just output the phrase and nothing else.",
        "instructions": "You are a creative assistant.",
        "store": True, "max_output_tokens": 30, "temperature": 0.7,
    }, timeout=30)
    resp1 = r1.json()
    resp1_id = resp1["id"]
    turn1_text = ""
    for item in resp1.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    turn1_text += c.get("text", "")
    print(f"Turn 1 output: {turn1_text.strip()!r}")

    # Turn 2: Ask model to repeat what IT said
    r2 = requests.post(f"{base}/v1/responses", json={
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "input": "Repeat exactly what you said in your last response. Just output the phrase you gave me, nothing else.",
        "previous_response_id": resp1_id,
        "instructions": "You are a creative assistant.",
        "store": True, "max_output_tokens": 50, "temperature": 0.0,
    }, timeout=30)
    resp2 = r2.json()
    turn2_text = ""
    for item in resp2.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    turn2_text += c.get("text", "")
    print(f"Turn 2 output: {turn2_text.strip()!r}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://localhost:30000")
    main(p.parse_args())
```
</details>

**Before Logs (Bug present)**
```
$ python3 repro_responses_multi_turn.py --base-url http://localhost:30000

Turn 1 output: 'Echoes of midnight'
Turn 2 output: 'You are a creative assistant.'
```

Turn 2 output is `"You are a creative assistant."` — this is literally the `instructions` field (the system prompt), not the model's Turn 1 output. The model was asked to repeat what it said, and it echoed the system prompt because that's what was injected into the conversation history in place of the actual assistant output.

### Environment setup
- SGLang latest release via pip
- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- GCP `g2-standard-8` (NVIDIA L4), `[redacted-region]`
- Non-Harmony code path (open-source models)
- Bug present since initial `v1/responses` commit (`92cc32d9`, Aug 2025)
