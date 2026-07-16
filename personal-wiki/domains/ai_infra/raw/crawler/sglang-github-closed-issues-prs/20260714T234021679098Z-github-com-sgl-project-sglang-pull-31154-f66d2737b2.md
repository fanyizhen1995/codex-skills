---
source_id: sglang-github-closed-issues-prs
title: Introduce NgramEmbeddingManager component
canonical_url: https://github.com/sgl-project/sglang/pull/31154
captured_at: '2026-07-14T23:40:21.679098+00:00'
content_hash: f66d2737b2ec28e2f30da111178bf822c7a80a5ca98191d7bc48e1887608cac7
---
# Introduce NgramEmbeddingManager component

URL: https://github.com/sgl-project/sglang/pull/31154
State: closed
Labels: apple-silicon
Closed at: 2026-07-14T07:58:09Z
Merged at: 2026-07-14T07:58:09Z

### mrc-ngram-embedding-manager(introduce-ngram-embedding-mgr,non_mechanical_provable): Introduce NgramEmbeddingManager (PR 1/3 of ngram embedding migration)

### mrc-ngram-embedding-manager(nem-migrate-maybe-prepare-prep,non_mechanical_provable): Prep _maybe_prepare_ngram_embedding for move onto NgramEmbeddingManager

### mrc-ngram-embedding-manager(nem-migrate-maybe-prepare-move,non_mechanical_provable): Move prepare_for_forward onto NgramEmbeddingManager (cut+paste)

### mrc-ngram-embedding-manager(drop-legacy-ngram-double-track-fields-read-via-n,non_mechanical_provable): Drop legacy ngram double-track fields; read via ngram_embedding_manager

init_ngram_embedding_manager kept legacy self.use_ngram_embedding / self.token_table mirrors of the manager state for Scheduler / decode CUDA graph runner / forward_batch_info. Migrate those four consumers to read model_runner.ngram_embedding_manager.enabled / .table directly (all token_table reads are already guarded by enabled, so equivalent) and drop the mirror fields.







<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:no_entry_sign: [Run #29316349924](https://github.com/sgl-project/sglang/actions/runs/29316349924)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:no_entry_sign: [Run #29316349870](https://github.com/sgl-project/sglang/actions/runs/29316349870)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
