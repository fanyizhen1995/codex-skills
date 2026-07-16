---
source_id: sglang-github-closed-issues-prs
title: '[Test] Add unit tests for msgspec_utils'
canonical_url: https://github.com/sgl-project/sglang/pull/31102
captured_at: '2026-07-14T23:40:21.685072+00:00'
content_hash: 3b0d2591c3dcc3a206f67e3944be47bfc1d5d0c4aa9bebc3a6e9a4f548467b29
---
# [Test] Add unit tests for msgspec_utils

URL: https://github.com/sgl-project/sglang/pull/31102
State: closed
Labels: 
Closed at: 2026-07-14T03:34:12Z
Merged at: 

## Summary

- add CPU-only unit tests for `python/sglang/srt/utils/msgspec_utils.py`
- cover base64 decoding, malformed input, nested containers, and serialized tensor payloads
- cover recursive `msgspec.Struct` conversion across dictionaries, lists, tuples, sets, and primitive values
- cover required fields, defaults, independent default factories, Python/JSON validation, existing instances, ignored extra fields, type errors, and generated JSON schema

Related to #20865.

## Testing

The focused test was run on Windows with Python 3.12. The source tree was added to `PYTHONPATH`; a local Windows import bootstrap avoided SGLang's Unix-only top-level `resource` import. The committed test continues to use the repository's normal `CustomTestCase` import.

```powershell
$env:SGLANG_REPO_ROOT = $PWD
$env:PYTHONPATH = "$env:TEMP\sglang-msgspec-test-bootstrap;$(Join-Path $PWD 'python')"
python -m pytest test/registered/unit/utils/test_msgspec_utils.py -v
```

```text
============================= test session starts =============================
platform win32 -- Python 3.12.13, pytest-9.0.2, pluggy-1.6.0 -- D:\apps\miniforge\envs\work312\python.exe
cachedir: .pytest_cache
rootdir: D:\project\git_code\sglang_issue_20865\test
configfile: pytest.ini
plugins: anyio-4.13.0, cov-7.1.0
collecting ... collected 14 items

test\registered\unit\utils\test_msgspec_utils.py::TestBase64Bytes::test_decodes_multiple_serialized_tensor_values_from_json PASSED [  7%]
test\registered\unit\utils\test_msgspec_utils.py::TestBase64Bytes::test_decodes_scalar_and_list_values PASSED [ 14%]
test\registered\unit\utils\test_msgspec_utils.py::TestBase64Bytes::test_preserves_python_bytes PASSED [ 21%]
test\registered\unit\utils\test_msgspec_utils.py::TestBase64Bytes::test_recurses_through_nested_lists_and_tuples PASSED [ 28%]
test\registered\unit\utils\test_msgspec_utils.py::TestBase64Bytes::test_rejects_malformed_base64 PASSED [ 35%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecToBuiltins::test_preserves_dict_keys_and_primitive_leaves PASSED [ 42%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecToBuiltins::test_recursively_converts_realistic_nested_struct PASSED [ 50%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecStructPydanticCoreSchema::test_defaults_and_default_factory_are_applied_independently PASSED [ 57%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecStructPydanticCoreSchema::test_existing_instance_is_preserved_by_python_path PASSED [ 64%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecStructPydanticCoreSchema::test_extra_fields_are_ignored PASSED [ 71%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecStructPydanticCoreSchema::test_json_schema_marks_required_and_default_fields PASSED [ 78%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecStructPydanticCoreSchema::test_python_dict_and_json_build_structs PASSED [ 85%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecStructPydanticCoreSchema::test_required_field_rejects_missing_input PASSED [ 92%]
test\registered\unit\utils\test_msgspec_utils.py::TestMsgspecStructPydanticCoreSchema::test_wrong_field_type_fails_validation PASSED [100%]

============================== warnings summary ===============================
..\..\..\apps\miniforge\envs\work312\Lib\site-packages\_pytest\config\__init__.py:1428
  D:\apps\miniforge\envs\work312\Lib\site-packages\_pytest\config\__init__.py:1428: PytestConfigWarning: Unknown config option: asyncio_mode

    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============== 14 passed, 1 warning, 2 subtests passed in 0.46s ===============
```

Additional checks:

```powershell
python scripts/ci/check_registered_tests.py
# exit code 0, no output

python -m pytest test/registered/unit/utils/test_msgspec_utils.py test/registered/unit/utils/test_field_validators.py -v
# 32 passed, 1 warning, 15 subtests passed in 0.42s

python -m pytest test/registered/unit/utils/test_msgspec_utils.py --cov --cov-config=.coveragerc --cov-report=term-missing -v
# python\sglang\srt\utils\msgspec_utils.py: 48 statements, 0 missed, 100% coverage
# 14 passed, 1 warning, 2 subtests passed in 4.73s
```







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29301551121](https://github.com/sgl-project/sglang/actions/runs/29301551121)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29301550932](https://github.com/sgl-project/sglang/actions/runs/29301550932)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
