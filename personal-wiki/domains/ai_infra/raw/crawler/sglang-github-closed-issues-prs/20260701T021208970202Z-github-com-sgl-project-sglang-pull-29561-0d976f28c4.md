---
source_id: sglang-github-closed-issues-prs
title: Move easydict to optional remote-models extra
canonical_url: https://github.com/sgl-project/sglang/pull/29561
captured_at: '2026-07-01T02:12:08.970202+00:00'
content_hash: 0d976f28c40f4990a1b0b404fae4651d7bbd304dada8c718061a99c703cac9aa
---
# Move easydict to optional remote-models extra

URL: https://github.com/sgl-project/sglang/pull/29561
State: closed
Labels: documentation, dependencies, deepseek, npu
Closed at: 2026-06-30T00:04:25Z
Merged at: 

## Motivation

Fixes #29177.

`easydict` is currently published as an unconditional SGLang dependency, so it
appears in the default `Requires-Dist` metadata even for deployments that never
load model repos requiring it. That creates avoidable LGPL-3.0 license-compliance
friction downstream.

The dependency appears to be needed by some remote model code loaded through
`--trust-remote-code` (for example DeepSeek-OCR), not by SGLang's default runtime
path. Making it opt-in keeps those models supported without forcing every SGLang
installation to pull in `easydict`.

## Modifications

- Move `easydict` from default dependencies to a new `remote-models` optional
  extra in all pyproject variants.
- Include the new extra in the platform `all` extras so broad/dev installs keep
  the previous convenience behavior.
- Document `uv pip install "sglang[remote-models]"` in the install guide and
  DeepSeek-OCR docs for remote-code model repos that need `easydict`.

## Accuracy Tests

N/A. This is a packaging/docs-only change and does not touch model execution or
outputs.

## Speed Tests and Profiling

N/A. This change does not touch runtime execution paths.

## Validation

```bash
git diff --check
```

```bash
python3 - <<'PY'
import pathlib, tomllib
files = [
    pathlib.Path('python/pyproject.toml'),
    pathlib.Path('python/pyproject_cpu.toml'),
    pathlib.Path('python/pyproject_npu.toml'),
    pathlib.Path('python/pyproject_other.toml'),
    pathlib.Path('python/pyproject_xpu.toml'),
]
for path in files:
    data = tomllib.loads(path.read_text())
    deps = data['project']['dependencies']
    optional = data['project']['optional-dependencies']
    assert not any(dep.split(';', 1)[0].strip().split()[0].lower() == 'easydict' for dep in deps), path
    assert optional.get('remote-models') == ['easydict'], (path, optional.get('remote-models'))
print('ok: easydict is only in remote-models extra for all pyproject variants')
PY
```

```bash
python -m pip install --dry-run --no-deps -e python
```

```bash
pre-commit run --files \
  docs/basic_usage/deepseek_ocr.md \
  docs/get_started/install.md \
  docs_new/cookbook/autoregressive/DeepSeek/DeepSeek-OCR-2.mdx \
  docs_new/cookbook/autoregressive/DeepSeek/DeepSeek-OCR.mdx \
  docs_new/docs/get-started/install.mdx \
  python/pyproject.toml \
  python/pyproject_cpu.toml \
  python/pyproject_npu.toml \
  python/pyproject_other.toml \
  python/pyproject_xpu.toml
```

The pip dry-run and pre-commit checks were run in a disposable venv and
completed successfully. I did not run GPU/server validation because this change
is packaging metadata and docs only.

## Checklist

- [x] Format your code according to the [Format code with pre-commit](https://docs.sglang.io/developer_guide/contribution_guide.html#format-code-with-pre-commit).
- [x] Add unit tests according to the [Run and add unit tests](https://docs.sglang.io/developer_guide/contribution_guide.html#run-and-add-unit-tests). N/A: packaging/docs metadata only.
- [x] Update documentation according to [Write documentations](https://docs.sglang.io/developer_guide/contribution_guide.html#write-documentations).
- [x] Provide accuracy and speed benchmark results according to [Test the accuracy](https://docs.sglang.io/developer_guide/contribution_guide.html#test-the-accuracy) and [Benchmark the speed](https://docs.sglang.io/developer_guide/contribution_guide.html#benchmark-the-speed). N/A: no runtime/output path changes.
- [x] Follow the SGLang code style [guidance](https://docs.sglang.io/developer_guide/contribution_guide.html#code-style-guidance).























<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28346456410](https://github.com/sgl-project/sglang/actions/runs/28346456410)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28346456360](https://github.com/sgl-project/sglang/actions/runs/28346456360)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
