---
source_id: nccl-github-releases
title: NCCL EP v0.1.0 Release
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/nccl-ep-v0.1.0
captured_at: '2026-06-26T02:01:31.913529+00:00'
content_hash: 86841701c730e5665067adf8ba8a3b7c1685aada3e56630930dc83cef0086913
---
# NCCL EP v0.1.0 Release

URL: https://github.com/NVIDIA/nccl/releases/tag/nccl-ep-v0.1.0

RSS Summary:
<p>NCCL EP is a high-performance NCCL API extension for efficient Mixture-of-Experts (MoE) communication. It provides optimized dispatch and combine primitives for Expert Parallelism (EP) across distributed GPU systems implemented on top of NCCL Device API: Load-Store Accessible (LSA) and GPU-Initiated Networking (GIN) operations.</p>
<h2>API Improvements and Extensions</h2>
<ul>
<li>Refactor the API signatures to improve user experience and support backward compatibility.</li>
<li>Change the device memory ownership for EP Tensor data. The user is now responsible for device memory allocations for EP Tensors.</li>
<li>Refactor the EP tensor data structure management for the host-side NCCL EP Tensor object. EP tensor now supports both dynamic allocation for long-term storage and static on-stack allocation for malloc-free usage on the data path.</li>
<li>Add lightweight and CUDA Graph-compatible EP Handle management on the data path. <code>ncclEpCreateHandle</code> is split into <code>ncclEpInitHandle</code>, which is a control-path operation that may allocate device memory and may be collective, and <code>ncclEpUpdateHandle</code>, which updates the Handle's routing information before calling the Dispatch operation.</li>
<li>Allow users to set the number of SMs used by NCCL EP.</li>
<li>Extend the API to associate an NCCL EP Tensor with an NCCL Window to enable zero-copy optimizations.</li>
<li>Add flexible Dispatch output layout configurations:
<ul>
<li>HT mode supports Flat and Expert-major layouts.</li>
<li>Enable users to provide expert padding to align with GEMM requirements.</li>
<li>LL mode supports Expert- and Rank-major layouts.</li>
</ul>
</li>
<li>Add active rank mask support to identify failed ranks and exclude them from future communication, allowing operation to continue instead of aborting the process.</li>
<li>Introduce an explicit Forward/Backward pass selector in Dispatch and Combine operations.</li>
<li>Drop top-K indices from the Dispatch operation signature and use the tensor provided to the Handle update.</li>
</ul>
<h2>Implementation Improvements</h2>
<ul>
<li>Migrate to Just-In-Time (JIT) compilation for HT mode. This addresses performance issues and a number of limitations. LL migration to JIT is planned in the next release.</li>
<li>Add full Multi-node-NVLINK (MNNVL) support.</li>
<li>Remove limitations on the number of ranks in an LSA team. This has been tested on NVLink72.</li>
<li>Fully migrate to NCCL infrastructure. All CUDA IPC references are removed and the code only depends on NCCL.</li>
<li>Enable CUDA Graph support through EP handle management API changes and implementation changes.</li>
<li>Support MoE and prefill workloads by enabling a variable number of tokens per sender on Dispatch.</li>
</ul>
<h2>Performance Optimizations</h2>
<ul>
<li>Improve the performance of Dispatch for HT mode by leveraging NCCL Device API extensions available starting from NCCL v2.30.</li>
<li>Improve the performance of the Combine operation in HT mode by leveraging JIT compilation.</li>
<li>Enable zero-copy flows for HT mode.</li>
<li>Optimize LL performance for NVLink-only configurations by avoiding the send-side staging buffer.</li>
<li>Update <code>ep_bench</code> to measure kernel-only performance.</li>
<li>Introduce <code>ncclTeamRail</code> in HT mode instead of a split communicator.</li>
<li>Improve Dispatch/recv and Combine/send parallelization in LL mode.</li>
</ul>
<h2>Memory Footprint Optimizations</h2>
<ul>
<li>Optimize the Dispatch staging buffer in LL mode. Use per-rank token deduplication and rank-major layout to reduce the staging buffer size by a factor of experts per rank.</li>
<li>Expose rank-major layout at the API level in LL mode. Rank-major mode reduces the memory footprint by a factor of the number of experts per rank.</li>
<li>Optimize HT mode handle memory usage by moving the global routing map buffer from the handle to the group scope. This allows different handles to share the buffer.</li>
</ul>
<h2>Python Bindings</h2>
<ul>
<li>Expose NCCL EP through <code>nccl4py</code>.</li>
<li>Make Python bindings more pythonic compared to the original 1-to-1 C-Python mapping.</li>
</ul>
<h2>Performance Benchmark (<code>ep_bench</code>)</h2>
<ul>
<li>Report kernel-only performance metrics through CUPTI, if available.</li>
<li>Extend the number of settings: number of SMs, number of experts, and layout selection.</li>
<li>Add sophisticated validation for Dispatch and Combine phases to detect memory corruption and routing issues.</li>
</ul>
<h2>Bug Fixes</h2>
<ul>
<li>Fix the bug in HT mode preventing launches on more than 8 nodes.</li>
<li>Fix HT mode inter-node flags sizing that would cause overflow for 9 or more nodes.</li>
<li>Clean the API and tools from quantization-related code. Quantization support is planned to be re-enabled in the following release.</li>
<li>Fix memory ordering in Dispatch/Combine grid barriers.</li>
<li>Fix a bug causing crashes in LL mode for batch sizes.</li>
<li>Fix integer overflow in inter-node N2N warp at 8 or more nodes. Thanks to Mozar Huang.</li>
</ul>
<h2>Known Issues and Limitations</h2>
<ul>
<li>The number of RDMA domains, or NCCL LSA Teams, in HT mode is limited to 32 due to algorithmic limitations.</li>
<li><code>nccl4py</code> 0.3 wheel is shipped with <code>libnccl_ep.so</code> built with CUDA 13. To use CUDA 12, users have to build <code>libnccl_ep.so</code> from source and specify the <code>.so</code> file path using <code>LD_PRELOAD</code> or <code>LD_LIBRARY_PATH</code>. In addition, <code>NCCL_EP_HOME</code> needs to be set to point to the corresponding <code>nccl_ep</code> installation directory.</li>
<li>NCCL EP v0.1 does not support quantization. While the API has appearances of quantization-related parameters, such as the scales tensor, the implementation was not tested and is not guaranteed to work. Elements of quantization support are expected to be introduced in the next release.</li>
<li>The Dispatch operation has resource limitations associated with the amount of available shared on-chip memory. Consumption is impacted by two factors:
<ul>
<li>The hidden dimension of the token.</li>
<li>LSA team size, which is the size of the NVLink domain.</li>
</ul>
</li>
<li>If a job launch is aborted due to shared memory overflow, try to reduce the current stage or pipeline settings. In v0.1, this can only be done statically at build time: reduce the <code>HYBRIDEP_DISPATCH_NUM_OF_STAGES</code> and/or <code>HYBRIDEP_DISPATCH_NUM_OF_PIPELINES_PER_BLOCK</code> macro values in <code>hybridep_configs.cuh</code>, rebuild, and retry.</li>
</ul>
<h3>LL Mode Limitations</h3>
<ul>
<li>Maximum top-K: 9.</li>
<li>Hidden dimensions: 2048, 2560, 4096, 5120, 6144, 7168, and 8192.</li>
</ul>
<h2>Known Bugs</h2>
<ul>
<li>In LL mode, <code>ep_bench</code> reports Combine verification failure when a batch size of 1 token is used.</li>
<li>In LL mode, <code>ep_bench</code> reports Combine verification failures on 16 nodes and 64 GPUs for the batch size of 8K tokens.</li>
</ul>

Article Body:
