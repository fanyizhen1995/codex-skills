---
source_id: sglang-github-closed-issues-prs
title: '[Bug] deploy glm-5-w4a8，there is a problem with the accuracy.'
canonical_url: https://github.com/sgl-project/sglang/issues/20420
captured_at: '2026-07-14T23:40:21.663230+00:00'
content_hash: bc204fbb41a74c0ea686d5ff6ca8ee100b579760ed474aa076249b4399cdf51d
---
# [Bug] deploy glm-5-w4a8，there is a problem with the accuracy.

URL: https://github.com/sgl-project/sglang/issues/20420
State: closed
Labels: 
Closed at: 2026-03-13T08:16:37Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug

curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
-d '{
    "model": "glm-5",
    "messages": [
      {
        "role": "user",
        "content": "who are you"
      }
    ],
    "max_tokens": 50,
    "temperature": 0.0
  }'


response：
{"id":"5452ff68933f495eae483fee82ddc4f9","object":"chat.completion","created":1773299760,"model":"glm-5","choices":[{"index":0,"message":{"role":"assistant","content":"<think>也有所创>顿in\n\n��A 3出现在性
的\n\n��A 3出现在性的\n\n��Xiv:蛟 3 3出现在性的\n\n��A 3出现在性的\n\n��Posts\n也有所创\n\n��A 3出现在性的","reasoning_content":null,"tool_calls":null},"logprobs":null,"finish_reason":"length","matched_sto
p":null}],"usage":{"prompt_tokens":42,"total_tokens":92,"completion_tokens":50,"prompt_tokens_details":null,"reasoning_tokens":0},"metadata":{"weight_version":"default"}}




### Reproduction

unset ASCEND_LAUNCH_BLOCKING
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /usr/local/Ascend/nnal/atb/set_env.sh

export PYTORCH_NPU_ALLOC_CONF=expandable_segments:True
export HCCL_OP_EXPANSION_MODE=AIV
export OMP_PROC_BIND=false
export TASK_QUEUE_ENABLE=1

python3 -m sglang.launch_server \
--model-path $MODEL_PATH \
--attention-backend ascend \
--device npu \
--tp-size 8 \
--trust-remote-code \
--host 0.0.0.0 \
--mem-fraction-static 0.9 \
--port 8000 \
--served-model-name glm-5 \
--quantization modelslim \
--disable-cuda-graph \
--disable-custom-all-reduce 

### Environment

Hardware: Ascend 910B4 (Atlas 800I A2)
HDK: 25.2.3
CANN: 8.5.0
sgl_kernel_npu：2026.2.1
sglang：0.5.9
sglang-router：0.3.2
Python： 3.11.14
torch：2.8.0+cpu
torch_npu：2.8.0.post2
triton-ascend：3.2.0


Model: GLM-5-w4a8 （ https://modelscope.cn/models/Eco-Tech/GLM-5-w4a8/）
image：quay.io/ascend/sglang:v0.5.9-cann8.5.0-910b （imageID： cf2b5a22e9b4）
