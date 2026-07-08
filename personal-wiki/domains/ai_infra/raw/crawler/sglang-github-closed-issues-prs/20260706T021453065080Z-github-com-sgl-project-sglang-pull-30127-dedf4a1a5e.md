---
source_id: sglang-github-closed-issues-prs
title: '[refactor] Migrate the disable_overlap_schedule writers and the mamba radix
  cache resolution to the pipeline (stack 1/10)'
canonical_url: https://github.com/sgl-project/sglang/pull/30127
captured_at: '2026-07-06T02:14:53.065080+00:00'
content_hash: dedf4a1a5e870e64decfe67e13953ca1b47b14d4c3992e3a29242039ba616b06
---
# [refactor] Migrate the disable_overlap_schedule writers and the mamba radix cache resolution to the pipeline (stack 1/10)

URL: https://github.com/sgl-project/sglang/pull/30127
State: closed
Labels: 
Closed at: 2026-07-05T07:00:33Z
Merged at: 

Unit 1 of a 10-PR stack continuing the config-resolution pipeline refactor (previous stack: #30063–#30077).

The three post-monolith writers of disable_overlap_schedule become
slot-preserving post-process passes (embeddings sparse head, pipeline
parallelism, diffusion-LLM inference), and the field joins the resolvable
whitelist with a flat flag leaf — earlier writers stay imperative and remain
visible to the passes through the live view.

On top of that, the field resolution of _handle_mamba_radix_cache becomes a
pure post-process pass (_mamba_radix_cache_resolution) invoked at the legacy
call slots; its arch guard replicates the union of the legacy call-site
guards (including the Granite layer_types probe and the hybrid-spec
registry), so the per-branch call sites collapse into one self-guarded call
after the arch chain — for non-mamba archs the pass declares nothing and the
handler returns before validation. The pre-dispatch hybrid-spec call keeps
its position, so those archs still resolve against the pristine page_size;
the post-chain re-invocation is an idempotent no-op plus validation.
uses_mamba_radix_cache becomes a real (derived, no-CLI) ServerArgs field;
both mamba fields join the resolvable whitelist; pure-mamba branches
dissolve while Lfm2 keeps its backend assert.

🤖 Generated with [Claude Code](https://claude.com/claude-code)













































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28721910483](https://github.com/sgl-project/sglang/actions/runs/28721910483)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28721910430](https://github.com/sgl-project/sglang/actions/runs/28721910430)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
