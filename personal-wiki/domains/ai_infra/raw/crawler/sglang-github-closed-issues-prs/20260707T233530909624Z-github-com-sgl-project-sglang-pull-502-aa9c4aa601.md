---
source_id: sglang-github-closed-issues-prs
title: Litellm Backend
canonical_url: https://github.com/sgl-project/sglang/pull/502
captured_at: '2026-07-07T23:35:30.909624+00:00'
content_hash: aa9c4aa60148ede99bbda8958ea0ae02940028da86f9cf8852ae7d3227480160
---
# Litellm Backend

URL: https://github.com/sgl-project/sglang/pull/502
State: closed
Labels: 
Closed at: 2024-06-07T19:24:28Z
Merged at: 2024-06-07T19:24:28Z

Example

```python
import sglang as sgl
from sglang import LiteLLM, function, set_default_backend


@function
def multi_turn_question(s, question):
    s += sgl.system("You are a helpful assistant.")
    s += sgl.user(question)
    s += sgl.assistant_begin()
    s += " Let's think step by step. "
    s += sgl.gen("answer", max_tokens=256)
    s += sgl.assistant_end()


set_default_backend(LiteLLM("gpt-3.5-turbo", base_url="", api_key=""))

state = multi_turn_question.run(
    question=
    "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?",
)
for m in state.messages():
    print(m["role"], ":", m["content"])

state = multi_turn_question.run(
    question=
    "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?",
    stream=True,
)
for out in state.text_iter():
    print(out, end="", flush=True)
```

<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: **Missing `run-ci` label** -- add it to run CI tests.<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: **Blocked** -- `run-ci` is required first.<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
