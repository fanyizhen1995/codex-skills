---
source_id: nccl-github-releases
title: NCCL v2.30.3-1 Release
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/v2.30.3-1
captured_at: '2026-06-26T02:01:31.914684+00:00'
content_hash: 032b28fd94a1c4f7eb7dfdd4e1993ab59db7bda275900751987e0048ab13a862
---
# NCCL v2.30.3-1 Release

URL: https://github.com/NVIDIA/nccl/releases/tag/v2.30.3-1

RSS Summary:
<h2>Device API and GIN Enhancements</h2>
<ul>
<li>GIN contexts are no longer shared between device communicators backed by the same host communicator.</li>
<li>Adds per-context resource sharing modes for GIN, allowing GPU-scope or CTA-scoped resource sharing.</li>
<li>Adds TrafficClass support to device communicator.</li>
<li>Adds versioning to ncclDevComm.</li>
<li>Adds timeout support to the device APIs.</li>
<li>Adds max_rd_atomic and max_dest_rd_atomic support in GIN.</li>
<li>Upgrades doca-gpunetio to v2.0.2-rc1</li>
</ul>
<h2>Elastic Buffers (LSA support)</h2>
<ul>
<li>Support new use cases where large tensors are split into multi-segment windows, with the active region in GPU memory and the remainder in host memory.</li>
<li>Enables larger effective models and reduces memory pressure during spilling.</li>
<li>Elastic buffers will support GIN in a future release.</li>
</ul>
<h2>gin.get with Nonblocking Flush (Experimental)</h2>
<ul>
<li>Support GPU‑initiated gets and check completion without stalling.</li>
<li>It currently only works with GDAKI (not with CPU proxy) and doesn't work on directNIC and Ampere.</li>
</ul>
<h2>Symmetric Memory Improvements</h2>
<ul>
<li>Adds AVG operator to ReduceScatter Symmetric kernels.</li>
<li>Enable dynamic memory offload with group support for single-process, multi-GPU scenarios.</li>
<li>Adds support for GPU-only multi-segment registration for symmetric windows.</li>
<li>Adds CUDA graph capture and replay support for ncclPutSignal and ncclWaitSignal APIs.</li>
<li>One-sided RMA can now use an external network plugin.</li>
</ul>
<h2>Tensor Memory Accelerator (TMA) Support</h2>
<ul>
<li>Adds TMA support in select built-in symmetric kernels to offload bulk peer‑to‑peer copies and reductions, improving NVLink bandwidth and latency.</li>
<li>Can be enabled with NCCL_SYM_TMA_ENABLE=1.</li>
</ul>
<h2>DDP Support</h2>
<ul>
<li>Enables Dynamic Direct Path (DDP) so that NCCL can take advantage of hardware multipath and out‑of‑order receive for higher network performance on supported systems.</li>
<li>Can be enabled with NCCL_IB_OOO_RQ=1.</li>
</ul>
<h2>Port Recovery</h2>
<ul>
<li>Adds support for IB port recovery in NCCL.</li>
<li>Improves NCCL’s ability to recover from transient network issues so communicators can continue operating without full re‑initialization.</li>
<li>Can be enabled with NCCL_IB_RESILIENCY_PORT_RECOVERY=1.</li>
</ul>
<h2>Cross Clique Support</h2>
<ul>
<li>Add support for treating multiple cliques as the same NVLINK domain.</li>
<li>Can be enabled with NCCL_MNNVL_CROSS_CLIQUE=1</li>
</ul>
<h2>NCCL Parameter Infrastructure</h2>
<ul>
<li>Adds new C APIs to support querying NCCL parameters.</li>
<li>Introduces ncclParamGetAllParameterKeys,ncclParamDumpAll, ncclParamGet and ncclParamGetParameter APIs.</li>
</ul>
<h2>NCCL4PY v0.2.0</h2>
<ul>
<li>Adds new APIs from NCCL 2.29 release.</li>
<li>Add devcomm create/destroy APIs to prepare for device API.</li>
<li>Enables Freethreading support.</li>
</ul>
<h2>Other Improvements</h2>
<ul>
<li>Adds NCCL Inspector P2P event support.</li>
<li>ncclGinBarrierSession can now be created directly for the world team without manual resource allocation.</li>
<li>GIN proxy GFD size increased to 128 bytes with version field added.</li>
<li>GIN proxy CQ polling (ginProgress) moved to per-context to improve performance.</li>
<li>ncclBarrierSession no longer shares resources with ncclLsaBarrierSession or ncclGinBarrierSession.</li>
<li>Redundant NCCL_DEBUG=INFO log volume reduced significantly.</li>
<li>NVLSTree tuning that improves performance for various Blackwell systems.</li>
<li>Adds p2pMaxPeers to communicator to achieve better tuning for send/recv vs. all2all.</li>
<li>Enables LL128 protocol in heterogeneous scenarios for Hopper and later GPUs.</li>
<li>Adds checks for mismatched Net and CollNet counts across communicators.</li>
<li>Adds Graphana template for NCCL inspector dashboard rendering using Prometheus data.</li>
<li>Removes unused members nccl_id, comm, nccl_unique_id, and thread_ranks in the examples (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/1989">#1989</a>).</li>
<li>Adds NCCL_LIBIBVERBS_SO environment variable to specify an absolute path for libibverbs (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2043">#2043</a>).</li>
<li>Extends suspend memory offload to channel device allocations (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2060">#2060</a>).</li>
</ul>
<h2>Bug Fixes</h2>
<ul>
<li>Fixes implicit CUDA synchronization in <code>putSignal</code> and <code>CE collectives</code> caused by pageable CPU stack memcpy.</li>
<li>Fixes a hang when using CE collectives and cuda graph under an edge case.</li>
<li>Fixes NULL access issue during finalize when RMA and GIN plugins are both initialized.</li>
<li>Fixes race conditions in all2all GIN/Hybrid examples with more than one CTA.</li>
<li>Fixes <code>ncclGinType_t</code> uint8_t enum compatibility issue in nccl4py.</li>
<li>Fixes several memory leaks in communicator create/destroy code paths.</li>
<li>Fixes a bug in plugin compat layer for v11 related to lazy initialization.</li>
<li>Fixes data corruption in symmetric LL kernels with unaligned buffer.</li>
<li>Fixes plugin name being cleared after communicator destroy (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/1978">#1978</a>).</li>
<li>Fixes deadlock and use-after-free in the inspector plugin (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/2000">#2000</a>).</li>
<li>Fixes incorrect network interface selection caused by inverted boolean logic in matchSubnet (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2047">#2047</a>).</li>
<li>Fixes regression from 2.29.2 where CPU affinity mask is not restored in initTransportsRank (Github issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/2033">#2033</a>)</li>
</ul>
<h2>Known Limitations</h2>
<ul>
<li>Applications that use GIN APIs need to be recompiled with 2.30.3 to work with 2.30.3 runtime.</li>
<li>gin.get requires GDAKI and is not supported on Ampere or directNIC platforms.</li>
</ul>
<h2>Acknowledgments</h2>
<p>We thank the following contributors for their work on this release:</p>
<ul>
<li><a class="user-mention notranslate" href="https://github.com/chenhengqi">@chenhengqi</a>, <a class="user-mention notranslate" href="https://github.com/liangxs">@liangxs</a>, <a class="user-mention notranslate" href="https://github.com/phu0ngng">@phu0ngng</a>, <a class="user-mention notranslate" href="https://github.com/SreevatsaAnantharamu">@SreevatsaAnantharamu</a>, <a class="user-mention notranslate" href="https://github.com/SongXiaoXi">@SongXiaoXi</a> for your PRs.</li>
<li><a class="user-mention notranslate" href="https://github.com/sphish">@sphish</a>, <a class="user-mention notranslate" href="https://github.com/LyricZhao">@LyricZhao</a> for continued contribution on improving the NCCL device API.</li>
</ul>
<p>We also thank the community for issue reports, testing, and feedback.</p>

Article Body:
