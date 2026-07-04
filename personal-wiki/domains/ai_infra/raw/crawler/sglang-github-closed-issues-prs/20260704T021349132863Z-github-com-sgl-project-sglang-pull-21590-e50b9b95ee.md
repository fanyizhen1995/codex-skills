---
source_id: sglang-github-closed-issues-prs
title: Fix llava next video model
canonical_url: https://github.com/sgl-project/sglang/pull/21590
captured_at: '2026-07-04T02:13:49.132863+00:00'
content_hash: e50b9b95ee8f6e861e77bb1f8dfd6a4a7f500f9233ad33d4801afb5e3ad13403
---
# Fix llava next video model

URL: https://github.com/sgl-project/sglang/pull/21590
State: closed
Labels: 
Closed at: 2026-07-03T12:33:31Z
Merged at: 

<!-- Thank you for your contribution! Please follow these guidelines to enhance your pull request. If anything is unclear, submit your PR and reach out to maintainers for assistance. Join our Slack community at https://slack.sglang.io to discuss further. -->

## Motivation
 The llava-next-video model is currently broken. Specifically, the model relies on offsets to insert image embeddings into the input embeddings. Currently, the code retrieves these offsets from MultimodalDataItem, but LlavaImageProcessor does not pass the offsets when constructing MultimodalDataItem. The fix restores the behavior to obtain image_offsets from MultimodalInputs.
Additionally, according to the documentation, this model expects video inputs wrapped using the SglVideo primitive in the language frontend, but the corresponding video processing logic was removed. This PR reintroduces the necessary video data handling logic.

Here is the error encountered when running examples/frontend_language/usage/llava_video/srt_example_llava_v.py. without modifying load_image, the error is:

> Traceback (most recent call last):
  File "/sglang/python/sglang/srt/multimodal/processors/llava.py", line 53, in _process_single_image_task
    image, image_size = load_image(url, False)
  File "/sglang/python/sglang/srt/utils/common.py", line 925, in load_image
    image = _load_image(image_file=image_file, gpu_image_decode=gpu_image_decode)
  File "/sglang/python/sglang/srt/utils/common.py", line 796, in load_image
    image_bytes = get_image_bytes(image_file)
  File "/sglang/python/sglang/srt/utils/common.py", line 951, in get_image_bytes
    return pybase64.b64decode(image_file, validate=True)
binascii.Error: Non-base64 digit found

After modifying load_image but without modifying the offsets, the error is:

> File "/sglang/python/sglang/srt/model_executor/model_runner.py", line 2571, in forward_extend
    self.model.forward(
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch/utils/_contextlib.py", line 120, in decorate_context
    return func(*args, **kwargs)
  File "sglang/python/sglang/srt/models/llavavid.py", line 197, in forward
    if image_offset < prefix_len:
TypeError: '<' not supported between instances of 'NoneType' and 'int'
<!-- Describe the purpose and goals of this pull request. -->

## Modifications
1.get image_offsets from MultimodalInputs, rather than from MultimodalDataItem.
2.when querying it with the sgl.video() clips, use decode_video_base64 func to load video data.
<!-- Detail the changes made in this pull request. -->

## Accuracy Tests
python examples/frontend_language/usage/llava_video/srt_example_llava_v.py

the result is:

> target_frames: 16
 In the video, we see a man standing in a room with a dark background. He is holding a white object in his right hand, which appears to be a smartphone. The man is dressed in a black shirt and jeans, and he is looking directly at the camera. His expression is serious, and he seems to be in the middle of a conversation or presentation.
The room is dimly lit, with the man being the only source of light. The walls are painted in a dark color, and there are no other objects or people visible in the frame. The man's position in the room and his direct gaze at the camera suggest that he is the main subject of the video.
The white object he is holding could be a smartphone, given the context of the video. However, without more information, it's difficult to determine the exact nature of the object. The man's serious expression and the way he is holding the object suggest that he is engaged in a serious conversation or presentation.
Overall, the video seems to be a simple yet effective portrayal of a man in a serious conversation or presentation, with a focus on his expression and the object he is holding. The dark background and dim lighting add to the serious tone of the video, emphasizing the man's importance in the scene.
Average processing time per video: 10.52 seconds

<!-- If this pull request affects model outputs (e.g., changes to the kernel or model forward code), provide accuracy test results. -->


## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests).
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed).
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).

## Review and Merge Process

1. Ping Merge Oncalls to start the process. See the [PR Merge Process](https://github.com/sgl-project/sglang/blob/main/.github/MAINTAINER.md#pull-request-merge-process).
2. Get approvals from [CODEOWNERS](https://github.com/sgl-project/sglang/blob/main/.github/CODEOWNERS) and other reviewers.
3. Trigger CI tests with [comments](https://docs.sglang.io/developer_guide/contribution_guide.html#how-to-trigger-ci-tests) or contact authorized users to do so.
   - Common commands include `/tag-and-rerun-ci`, `/tag-run-ci-label`, `/rerun-failed-ci`
4. After green CI and required approvals, ask Merge Oncalls or people with Write permission to merge the PR.
