---
source_id: sglang-github-closed-issues-prs
title: Fix arm64 CI test dependencies
canonical_url: https://github.com/sgl-project/sglang/pull/29618
captured_at: '2026-07-01T02:12:08.969739+00:00'
content_hash: f5faae4d5fe688e5833f0be2aea19c45e70b28db83ef61423cbfc52389621092
---
# Fix arm64 CI test dependencies

URL: https://github.com/sgl-project/sglang/pull/29618
State: closed
Labels: 
Closed at: 2026-06-30T00:04:30Z
Merged at: 

## Summary

- install `pytest` in the arm64 CI Docker image before running the registered CPU suite
- keep the change scoped to the test runner dependency instead of pulling the full `.[test]` extra into the arm64 image

## Why

Recent arm64 `build-test` jobs are failing before any CPU kernel test runs:

```text
python3 /sglang-checkout/test/registered/cpu/test_activation.py
ModuleNotFoundError: No module named 'pytest'
```

I saw the same failure pattern on at least PR #28715 and PR #29613. The arm64 workflow builds `docker/arm64.Dockerfile`, runs the sanity import successfully, and then invokes `test/run_suite.py --suite base-b-test-cpu-arm64`. That suite includes `test_activation.py`, which imports `pytest` and calls `pytest.main(...)` when run as a script.

The Dockerfile currently installs `sglang-cpu` and `sglang-kernel-cpu`, but not the test runner dependency. Installing `pytest` in that environment lets the existing suite entrypoint get past import/collection and report real test failures if any remain.

## Testing

- `git diff --check`

I did not run the full arm64 Docker workflow locally because this environment is not the GitHub `ubuntu-24.04-arm` runner. The change targets the exact missing module shown in the upstream arm64 CI logs.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:white_check_mark: [Run #28349113014](https://github.com/sgl-project/sglang/actions/runs/28349113014)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28349112901](https://github.com/sgl-project/sglang/actions/runs/28349112901)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
