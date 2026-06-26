---
source_id: nccl-github-releases
title: NCCL v2.30.7-1 Release
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/v2.30.7-1
captured_at: '2026-06-26T02:01:31.913875+00:00'
content_hash: c8db8da49efd6ccce29e7c9d51f28fa6b7594330d5bdf33de894149ec0dba3a6
---
# NCCL v2.30.7-1 Release

URL: https://github.com/NVIDIA/nccl/releases/tag/v2.30.7-1

RSS Summary:
<h2>Zero-SM Collectives</h2>
<ul>
<li>Adds hierarchical zero-SM collectives (AllGather and All2all) that use RMA CPU proxy for inter-node communication and Copy Engines for intra-node communication.</li>
<li>Enables better overlap of compute and communication.</li>
<li>Enable hierarchical zero-SM collectives with <code>NCCL_CTA_POLICY_ZERO</code> flag.</li>
</ul>
<h2>GIN Enhancements</h2>
<ul>
<li>Adds new experimental GPU Push Interface (GPI) backend for GIN.</li>
<li>Adds explicit signal semantics with Strong and Weak signals.</li>
<li>Adds proper <code>ncclGinFenceLevel</code> semantics for barriers.</li>
<li>Adds separate <code>NCCL_GIN_IB_TC</code> toggle to control traffic class used by GIN.</li>
<li>Adds <code>NCCL_GIN_RESOURCE_SHARING_THREAD</code> to enable more optimizations.</li>
<li>Optimizes QP overhead, including GDAKI mode when counters are not used.</li>
<li>Ensures GIN is usable when NIC fusion is enabled.</li>
<li>Adds GIN plugin example in <code>plugins/gin/example</code>.</li>
</ul>
<h2>Symmetric Memory Improvements</h2>
<ul>
<li>Restructures RMA plugin architecture.</li>
<li>Adds support for asymmetric buffer sizes during window registration.</li>
<li>Optimizes ReduceScatter symmetric kernel performance.</li>
<li>Optimizes performance for RMA operations using CE.</li>
<li>Adds batched CE operations to improve performance in the RMA CE put/wait path.</li>
<li>Adds support for window registration during CUDA graph capture.</li>
</ul>
<h2>MPS with MLOPart Support (Experimental)</h2>
<ul>
<li>NCCL now leverages CUDA feature Memory Locality Optimized Partition (MLOPart).</li>
<li>Supports up to 2 ranks per physical GPU with MPS+mlopart.</li>
</ul>
<h2>Other Improvements</h2>
<ul>
<li>Adds support for IB ports that require global route headers (GRH).</li>
<li>Adds logic to <code>gin.flush</code> to ensure all prior gets are visible.</li>
<li>Adds makefile support to compile python wheels from source.</li>
<li>Adds <code>NCCL_RMA_DISABLE</code> env to enable/disable RMA (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2151">#2151</a>).</li>
<li>Implements reset-without-zeroing for signals and counters in GIN (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2155">#2155</a>).</li>
<li>Pins GIN proxy thread to NUMA-local CPU set (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2182">#2182</a>).</li>
<li>Adds optimized weight transfer APIs in <code>contrib/nccl_xfer</code>.</li>
<li>Adds custom kernels in <code>contrib/custom_algos</code> for alltoall and allreduce using NCCL Device API.</li>
<li>Adds examples of Root Mean Square Normalization (RMSNorm), demonstrating the fusion of computation and communication using the device API.</li>
<li>Unifies coding style by using clang-format. Please see <code>docs/dev_guide/nccl_coding_style.md</code> for more details.</li>
<li>Drops support for v11 and v12 GIN plugin APIs.</li>
</ul>
<h2>Bug Fixes</h2>
<ul>
<li>Fixes a deadlock caused by cuda stream allocation under PXN when memseting a buffer at runtime.</li>
<li>Reintroduce <code>cudaGridDependencySynchronize</code> in built-in symmetric kernels, ensuring that newly launched kernels cannot access memory modified by prior kernels before it reaches point of coherency.</li>
<li>Ignores system headers in include/header processing, thereby avoiding excessive realpath calls in some builds (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/1806">#1806</a>).</li>
<li>Improves QP load balancing on systems configured with RoCE LAG with the round-robin queue affinity policy (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2150">#2150</a>).</li>
<li>Fixes issue when receiving an external TCP request causes the proxy thread's <code>ncclProxyService</code> to hang (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/1834">#1834</a>).</li>
<li>Fixes <code>rma_proxy</code> MR registration type for host-NUMA <code>cpuAccessSignals</code>, which ensures that the net plugin does not reject the registration due to wrong memory type (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2187">#2187</a>).</li>
<li>Fixes GIN init context leak (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/2179">#2179</a>).</li>
<li>Fixes issue with one-sided host APIs when a custom GIN plugin is used.</li>
<li>Fixes one-sided host API issue where requests are dropped at a high message rate (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/2119">#2119</a>).</li>
</ul>
<h2>Acknowledgements</h2>
<p>We thank the following contributors for their work on this release:</p>
<p><a class="user-mention notranslate" href="https://github.com/andrewjcg">@andrewjcg</a>, <a class="user-mention notranslate" href="https://github.com/baymaxhuang">@baymaxhuang</a>, <a class="user-mention notranslate" href="https://github.com/bhasunit">@bhasunit</a>, <a class="user-mention notranslate" href="https://github.com/fishautumn">@fishautumn</a>, <a class="user-mention notranslate" href="https://github.com/mozarhua">@mozarhua</a>, <a class="user-mention notranslate" href="https://github.com/ngoyal2707">@ngoyal2707</a>, <a class="user-mention notranslate" href="https://github.com/wanglei875">@wanglei875</a> for your PRs.</p>
<p>We also thank the community for issue reports, testing, and feedback.</p>
<h2>Known Issues</h2>
<ul>
<li>NCCL one-sided host RMA APIs, e.g., <code>ncclPutSignal</code>, require every rank to call the API as a one-time initialization warm-up. This will be fixed in an upcoming release.</li>
<li>NCCL one-sided RMA operations have a possible corruption issue when multiple symmetric windows are carved from the same backing memory allocation. See <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/2198">#2198</a>. This has been fixed on dev branch.</li>
</ul>

Article Body:
