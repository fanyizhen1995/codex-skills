---
source_id: nccl-github-releases
title: nccl4py v0.2.0 Release
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/nccl4py-v0.2.0
captured_at: '2026-06-26T02:01:31.914168+00:00'
content_hash: 5c4e9fd0c66c922333a59dbb8f9611c84575480fd5857e88b2711c7169f1016d
---
# nccl4py v0.2.0 Release

URL: https://github.com/NVIDIA/nccl/releases/tag/nccl4py-v0.2.0

RSS Summary:
<h1>Release Notes — nccl4py 0.2.0</h1>
<p>This release adds Python bindings for the new NCCL 2.30 one-sided RMA, Device API (GIN), and elastic communicator features, along with substantially more control over communicator configuration.</p>
<h2>Highlights</h2>
<ul>
<li><strong>One-sided RMA (point-to-point)</strong> — New <code>Communicator.put_signal()</code>, <code>Communicator.signal()</code>, and <code>Communicator.wait_signal()</code> methods, plus a <code>WaitSignalDesc</code> helper for describing signal values and match operations.</li>
<li><strong>NCCL Device API host side setup</strong> — New <code>Communicator.create_dev_comm()</code> that produces a <code>DevCommResource</code> for use with device-side NCCL kernels. Configure the device communicator through the new <code>NCCLDevCommRequirements</code> class, and introspect support via <code>device_api_support</code>, <code>gin_type</code>, <code>railed_gin_type</code>, <code>host_rma_support</code>, and <code>n_lsa_teams</code> properties.</li>
<li><strong>Device pointer access for registered windows</strong> — <code>RegisteredWindowHandle</code> now exposes <code>user_ptr</code>, <code>get_lsa_device_pointer()</code>, <code>get_lsa_multimem_device_pointer()</code>, and <code>get_peer_device_pointer()</code> for direct access to LSA, multimem, and peer mappings.</li>
<li><strong>Elastic and fault-tolerant communicators</strong> — New <code>Communicator.grow()</code>, <code>revoke()</code>, <code>suspend()</code>, and <code>resume()</code> methods to support elastic topology changes and error-handling flows. <code>CommSuspendFlag</code> added alongside existing <code>CommShrinkFlag</code>.</li>
<li><strong>More flexible construction</strong> — In addition to <code>init()</code>, communicators can now be created with class method <code>init_all()</code> and instance method <code>initialize()</code>. <code>Communicator.get_mem_stat()</code> reports per-communicator memory statistics.</li>
</ul>
<h2>Configuration</h2>
<p>New tuning knobs on <code>NCCLConfig</code>:</p>
<ul>
<li><code>graph_usage_mode</code>, <code>num_rma_ctx</code>, <code>max_p2p_peers</code>.</li>
</ul>
<p><code>NCCLDevCommRequirements</code> — passed to <code>Communicator.create_dev_comm()</code> to describe the resources and capabilities a device communicator needs:</p>
<ul>
<li>LSA: <code>lsa_multimem</code>, <code>barrier_count</code>, <code>lsa_barrier_count</code>, <code>rail_gin_barrier_count</code>, <code>world_gin_barrier_count</code>, <code>lsa_ll_a2a_block_count</code>, <code>lsa_ll_a2a_slot_count</code>.</li>
<li>GIN: <code>gin_force_enable</code>, <code>gin_context_count</code>, <code>gin_signal_count</code>, <code>gin_counter_count</code>, <code>gin_queue_depth</code>, <code>gin_connection_type</code>, <code>gin_exclusive_contexts</code>.</li>
</ul>
<h2>Device / topology introspection</h2>
<p>New <code>Communicator</code> properties: <code>cuda_dev</code>, <code>nvml_dev</code>, <code>device_api_support</code>, <code>multimem_support</code>, <code>gin_type</code>, <code>railed_gin_type</code>, <code>n_lsa_teams</code>, <code>host_rma_support</code>.</p>
<h2>Other changes</h2>
<ul>
<li><code>CTAPolicy</code> is now an <code>IntFlag</code> (was <code>IntEnum</code>) so multiple policies can be combined.</li>
<li>Interop submodules <code>nccl.core.cupy</code> and <code>nccl.core.torch</code> are now lazy-loaded via <code>__getattr__</code> and only imported on first attribute access, so <code>import nccl.core</code> no longer pulls in CuPy or PyTorch.</li>
</ul>

Article Body:
