---
source_id: sglang-github-closed-issues-prs
title: Empty `_REQ_TYPES_WITH_OPAQUE_FIELDS` on the msgpack IPC path (#29465 Task
  4)
canonical_url: https://github.com/sgl-project/sglang/pull/30182
captured_at: '2026-07-15T23:40:28.352416+00:00'
content_hash: ada0fc7dcf2b5c993574268c30d30fdac55060610556e4516ef85652ed0019f1
---
# Empty `_REQ_TYPES_WITH_OPAQUE_FIELDS` on the msgpack IPC path (#29465 Task 4)

URL: https://github.com/sgl-project/sglang/pull/30182
State: closed
Labels: run-ci
Closed at: 2026-07-15T21:55:06Z
Merged at: 2026-07-15T21:55:06Z

## What this does

Closes Task 4 of #29465. The 13 IPC structs in `_REQ_TYPES_WITH_OPAQUE_FIELDS` had
`Dict[str, Any]` / `List[Any]` fields, so on the msgpack path (`SGLANG_USE_PICKLE_IPC=0`)
`_maybe_wrap_pickle` whole-struct-pickled them inside a `PickleWrapper` frame. This PR tightens each
field to a precise msgspec-native type (or deletes a dead type), then removes the registry and its
`_maybe_wrap_pickle` branch. End state: the tuple no longer exists and every IPC struct encodes
natively.

Acceptance criterion (`_REQ_TYPES_WITH_OPAQUE_FIELDS` is empty) is met — the symbol is deleted.

## Per-type changes

12 types tightened, 1 deleted:

| Type | Change |
|---|---|
| `UpdateWeightFromDiskReqInput` | `manifest` documented as JSON-native; annotation unchanged |
| `VertexGenerateReqInput` | `instances`/`parameters` documented as JSON-native; annotation unchanged |
| `DumperControlReqInput` | `body` documented; `isinstance(body, dict)` guard added at the `/dumper` endpoint |
| `DumperControlReqOutput` | `response` documented as a JSON-native `List[Dict]` |
| `GetWeightsByNameReqOutput` | `parameter` → `Optional[List[Union[float, List[float]]]]` (element-level union) |
| `SetInternalStateReq` | `server_args` → `Dict[str, Union[int, float]]` |
| `RpcReqInput` | `parameters` → `Optional[Dict[str, Union[bool, int, float, str, None]]]` |
| `LoadLoRAAdapterFromTensorsReqInput` | `added_tokens_config` → `Optional[Dict[str, int]]`; `config_dict` kept `Dict[str, Any]` (see note) |
| `GetInternalStateReqOutput` | `internal_state` kept `Dict[str, Any]`; producer sanitizes via `msgspec_to_builtins` |
| `SetInternalStateReqOutput` | dead `server_args` field removed (only `.updated` is read) |
| `BackupDramReq` | `weight_pointer_map` → `Dict[str, ExpertWeightPointer]` (payload narrowed — see below) |
| `CheckWeightsReqOutput` | `payload` → `Optional[List[ChecksumInfo]]` (new mirror structs) |
| `SetInjectDumpMetadataReqInput` | deleted — no producer or consumer in-tree |

Supporting changes:
- `msgspec_to_builtins` now also converts dataclasses (→ dict), so the live `CudaGraphConfig`
  dataclass in the `vars(ServerArgs)` dump sanitizes consistently on both transports instead of
  only on the msgpack path. `get_internal_state` also drops `custom_sigquit_handler` from the
  dump — it can hold a bound signal handler and has no reader.
- `CheckWeightsReqOutput`: `ParallelismInfo`/`ChecksumInfo` msgspec mirrors added in `io_struct.py`
  (the pydantic models in `weight_checker.py` stay as the checker's source of truth). The producer
  normalizes the `tp>1` `all_gather_object` list and the `tp==1` case to a uniform
  `List[ChecksumInfo]`; the consumer reads struct attributes and converts back to builtins, so the
  `/weights_checker` HTTP response shape is unchanged.
- `config_dict` on `LoadLoRAAdapterFromTensorsReqInput` stays `Dict[str, Any]`: it is the PEFT
  `adapter_config.json`, already JSON on both paths, and a tighter type would only add decode
  strictness on out-of-tree callers with no consumer benefit.

## Deployment / compatibility

These structs cross every sglang zmq socket. Under `SGLANG_USE_PICKLE_IPC=0` the wire format changes,
so **all nodes and processes must run the same version with the same setting** (DP inter-node TCP
handshake, PD pairs, routers, elastic-EP). `SGLANG_USE_PICKLE_IPC=1` is a kill-switch **for framing
only**.

Three types change the payload on the **pickle** path too, so the kill-switch restores framing but
not compatibility — **revert is the mitigation** for these:
- `SetInternalStateReqOutput` — the `server_args` field is gone; an old-code peer fails to
  reconstruct the output.
- `CheckWeightsReqOutput` — the payload is `ChecksumInfo` structs instead of dicts.
- `BackupDramReq` — the payload is narrowed (see below).

`BackupDramReq` payload narrowing: `ExpertWeightPointer` carries only `weight_ptr` and `byte_size`.
The producer previously sent five more keys per entry — `name`, `shape`, `numel`, `dtype`,
`element_size` — none of which the consumer reads (it derives those from the local parameter tensor,
and gets the name from the map key). Because `BackupDramReq` only travels during an elastic-EP weight
refresh, a mixed-version fleet looks healthy until the first refresh, then fails at weight-update
time.

## Validation

- New unit test `test/registered/unit/managers/test_msgpack_ipc_roundtrip.py` (`register_cpu_ci`,
  `base-c-test-cpu`): per-type native round-trip and double-hop re-encode for all 12 types, the
  registry-empty assertion, the `ExpertWeightPointer` narrowing, field-parity between the
  `CheckWeightsReqOutput` mirrors and the pydantic models, a `tp>1`-shaped payload, and the
  `GetInternalStateReqOutput` dataclass sanitization (materializing `CudaGraphConfig`).
- Existing `test_io_struct.py` passes unchanged.

**`BackupDramReq` needs manual validation before merge.** CI has no elastic-EP path, so the wire
change is only unit-covered. TODO before merge: run an elastic-EP backup→refresh cycle on a 2-node
mooncake setup with `SGLANG_USE_PICKLE_IPC=0`, confirm weights transfer and inference stays correct,
and record the result here. If that environment is unavailable at merge time, land types 1 and 3–13
in this PR (registry down to `(BackupDramReq,)`, machinery not yet deleted) and finish `BackupDramReq`
plus the deletion in an immediate fast-follow.

## Notes

- The tightened annotations are the wire contract the Rust pre-scheduler (#29799, @rainj-me) will
  mirror.
- `SetInjectDumpMetadataReqInput` was added via internal-sync and never wired in-tree; the deletion
  needs internal-sync parity. Out-of-tree failure is loud (`ImportError` / `pickle.loads`
  `AttributeError`; the kill-switch does not help, since unpickling needs the class).
- Merge-conflict watch: #29656 (Task 1) rewrites the `enc_hook`/`dec_hook` region and runs context
  into `_maybe_wrap_pickle`; expect a small conflict on the registry-branch hunk whichever lands
  second — keep both changes. #30005 / #29952 / #29553 are line-number drift only; none touch the
  tuple.

## Out of scope (separate follow-ups)

- `continuous_buffer=None` crash when a node holds no expert weights
  (`expert_backup_manager.py`).
- `engine.py` base64-encode fix for `load_format='flattened_bucket'` (out-of-tree Engine callers
  passing raw `bytes`).
- Deleting the orphaned `SetInjectDumpMetadataReqOutput` / `LazyDumpTensors` pair.
- The five wrong `-> Optional[torch.Tensor]` return annotations in model files.
- `save_sharded_state.py` `--max-file-size type=str` bug.



























































































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29377658530](https://github.com/sgl-project/sglang/actions/runs/29377658530)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29377658496](https://github.com/sgl-project/sglang/actions/runs/29377658496)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
