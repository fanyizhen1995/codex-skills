---
source_id: sglang-github-closed-issues-prs
title: Introduce WeightUpdater and WeightExporter components
canonical_url: https://github.com/sgl-project/sglang/pull/31148
captured_at: '2026-07-14T23:40:21.679320+00:00'
content_hash: 6aa6328cbaf5b4fe79d07b4eef6e12b704ea038274ed7f7f099b75d43fecf0fe
---
# Introduce WeightUpdater and WeightExporter components

URL: https://github.com/sgl-project/sglang/pull/31148
State: closed
Labels: 
Closed at: 2026-07-14T07:53:33Z
Merged at: 2026-07-14T07:53:33Z

### mrc-weight-update-export(weight-updater-skeleton-prep,non_mechanical_provable): Introduce empty WeightUpdater skeleton, swap the field, rewire remaining refs and tp_worker callers in place

### mrc-weight-update-export(weight-updater-methods-move,mechanical_provable): Move init/destroy weights_update_group onto WeightUpdater (cut+paste)

### mrc-weight-update-export(wu-move-from-disk-prep,non_mechanical_provable): Prep update_weights_from_disk for move onto WeightUpdater

### mrc-weight-update-export(wu-move-from-disk-move,mechanical_provable): Move update_weights_from_disk onto WeightUpdater (cut+paste)

### mrc-weight-update-export(wu-move-from-distributed-prep,non_mechanical_provable): Prep update_weights_from_distributed for move onto WeightUpdater

### mrc-weight-update-export(wu-move-from-distributed-move,mechanical_provable): Move update_weights_from_distributed onto WeightUpdater (cut+paste)

### mrc-weight-update-export(wu-move-from-tensor-prep,non_mechanical_provable): Prep update_weights_from_tensor for move onto WeightUpdater

### mrc-weight-update-export(wu-from-tensor-callers-prep,non_mechanical_provable): Route eagle update_weights_from_tensor callers through the class-qualified staticmethod form

### mrc-weight-update-export(wu-move-from-tensor-move,mechanical_provable): Move update_weights_from_tensor + helpers onto WeightUpdater (cut+paste)

### mrc-weight-update-export(wu-move-from-ipc-prep,non_mechanical_provable): Prep update_weights_from_ipc for move onto WeightUpdater

### mrc-weight-update-export(wu-move-from-ipc-move,mechanical_provable): Move update_weights_from_ipc onto WeightUpdater, leaving a forwarding delegate (cut+paste)

### mrc-weight-update-export(wu-from-ipc-callers-postpare,non_mechanical_provable): Drop the update_weights_from_ipc delegate and route draft-runner weight updates through weight_updater

### mrc-weight-update-export(mr-add-update-model-fields,non_mechanical_provable): Add ModelRunner.update_model_fields + wire WeightUpdater

Add a post-load commit hook on ModelRunner that writes back the new
model ref, model_path, load_format, and load_config. Wire WeightUpdater
.update_weights_from_disk to call it in place of the 4 direct
self._mr.X = ... writes (god-class reach).

### mrc-weight-update-export(update-model-fields-override,non_mechanical_provable): Route update_model_fields writes through server_args.override

Forward-port adaptation for latest upstream/main: post-load model-field writes go
through the frozen server_args.override entry point; black-format dflash_worker_v2.

### mrc-weight-update-export(wu-narrow-ctor,non_mechanical_provable): Narrow WeightUpdater + convert to @dataclass(frozen, slots, kw_only)

Refactor WeightUpdater away from the model_runner_ref god-class reference
(R4 violation cleanup) and convert it to a strict frozen dataclass in one
go:

  @dataclass(frozen=True, slots=True, kw_only=True)
  class WeightUpdater:
      tp_rank: int
      device: str
      gpu_id: int
      model_config: ModelConfig
      custom_weight_loaders: dict
      get_model: Callable[[], Any]
      update_model_fields: Callable[..., None]
      recapture_cuda_graph: Callable[[], None]
      get_model_runner: Callable[[], ModelRunner]
      _model_update_group: dict = field(default_factory=dict)

All remaining self._mr.X accesses are routed through the new narrow
fields / callables:

  self._mr.device              -> self.device
  self._mr.gpu_id              -> self.gpu_id
  self._mr.model_config        -> self.model_config  (incl. direct write
                                  of model_config.model_path pre-load)
  self._mr.server_args.custom_weight_loader -> self.custom_weight_loaders
  self._mr.model.load_weights(...)          -> self.get_model().load_weights(...)
  self._mr.model (read)        -> self.get_model()
  SGLangCheckpointEngineWorkerExtensionImpl(self._mr)
                               -> SGLangCheckpointEngineWorkerExtensionImpl(self.get_model_runner())

The rollback no-op assignment `self._mr.model = model_load_weights(...)`
drops the assignment (the in-place load_weights side effect is what
mattered).

frozen=True only blocks attribute reassignment, not dict-content mutation
on _model_update_group; per-key insert / pop still work.

ModelRunner.__init__ wires the new narrow construction via a new
init_weight_updater method (parallel to the existing init_weight_exporter
pattern); __init__ just calls self.init_weight_updater() +
self.init_weight_exporter().

R4 verification: 0 self._mr references in weight_updater.py.

### mrc-weight-update-export(weight-exporter-skeleton-prep,non_mechanical_provable): Introduce empty WeightExporter skeleton, de-self the send-group methods in place, swap the field and rewire callers

### mrc-weight-update-export(weight-exporter-methods-move,mechanical_provable): Move the weights send group methods onto WeightExporter (cut+paste)

# Conflicts:
#	python/sglang/srt/model_executor/model_runner.py

### mrc-weight-update-export(we-move-save-get-prep,non_mechanical_provable): Prep weight save / get_weights_by_name for move onto WeightExporter

### mrc-weight-update-export(we-move-save-get-move,mechanical_provable): Move weight save / get_weights_by_name onto WeightExporter (cut+paste)

PR-Title: Introduce WeightUpdater and WeightExporter components

### mrc-weight-update-export(narrow-weight-exporter,non_mechanical_provable): Narrow WeightExporter to flat fields instead of the whole ModelRunner







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316065159](https://github.com/sgl-project/sglang/actions/runs/29316065159)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29316064884](https://github.com/sgl-project/sglang/actions/runs/29316064884)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
