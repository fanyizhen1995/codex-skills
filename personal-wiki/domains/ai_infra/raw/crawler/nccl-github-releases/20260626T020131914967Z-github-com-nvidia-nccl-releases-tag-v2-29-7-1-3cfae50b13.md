---
source_id: nccl-github-releases
title: NCCL v2.29.7 Release
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/v2.29.7-1
captured_at: '2026-06-26T02:01:31.914967+00:00'
content_hash: 3cfae50b1313f5f43d3a19a49dec84374271394bea5dcdc908065e8be1bbc6c8
---
# NCCL v2.29.7 Release

URL: https://github.com/NVIDIA/nccl/releases/tag/v2.29.7-1

RSS Summary:
<h2>Device API &amp; GIN Enhancements</h2>
<ul>
<li>Adds multi-context support for GIN with the option to request for exclusive GIN contexts.</li>
<li>Adds VA-based GIN signals plus strict window ordering.</li>
<li>Adds advanced queue control for GIN, including queue depth, manual credit management and aggregation.</li>
<li>Adds GIN support for platforms with no cross rail connectivity.</li>
<li>Adds nLsaTeams to ncclCommQueryProperties.</li>
<li>Decouples GIN from NET plugin and topology.</li>
</ul>
<h2>New device APIs for convenience</h2>
<ul>
<li>Adds new device APIs for various device side operations.</li>
<li>Introduces Copy, ReduceCopy, ReduceSum with various data types and ops.</li>
</ul>
<h2>Dynamic Memory Offload</h2>
<ul>
<li>Adds ncclCommSuspend() / ncclCommResume() for releasing/restoring communicator memory.</li>
<li>Adds basic memory overhead tracking infrastructure.</li>
</ul>
<h2>Built-in hybrid (LSA+GIN) symmetric kernel for ReduceScatter:</h2>
<ul>
<li>Adds new hierarchical kernels to improve performance and scalability of ReduceScatter.</li>
<li>Requires symmetric memory registration and GIN support.</li>
<li>Symmetric GIN kernels can be disabled with NCCL_SYM_GIN_KERNELS_ENABLE=0.</li>
</ul>
<h2>Add support for Port Failover</h2>
<ul>
<li>Allows internal IB/RoCE plugin to continue working transparently when network errors occur.</li>
<li>Adds automatic port failover for GPUs having multiple local IB/RoCE ports/devices.</li>
<li>Can be enabled by setting NCCL_IB_RESILIENCY_PORT_FAILOVER=1.</li>
</ul>
<h2>Symmetric memory improvements</h2>
<ul>
<li>Adds support for abort in symmetric kernels.</li>
<li>Adds NCCL_CHECK_MODE=DEBUG to validate symmetric buffers registration.</li>
</ul>
<h2>Project layout reorganization</h2>
<ul>
<li>The <code>ext-*</code> directories are moved to <code>plugins</code> (e.g. <code>ext-net</code> → <code>plugins/net</code>).</li>
<li><code>ir</code> and <code>nccl4py</code> are now under <code>bindings</code>.</li>
<li><code>examples</code> is now <code>docs/examples</code>.</li>
</ul>
<h2>Other Improvements</h2>
<ul>
<li>Uses different signals for different peers in the GIN barrier.</li>
<li>Adds NCCL_NO_CACHE to force NCCL to always re-read selected env vars.</li>
<li>Adds CMake install and find_package support.</li>
<li>Adds CMake for NCCL4Py build and updates Cybind integration.</li>
<li>Adds preliminary backwards compatibility support to enable running LSA kernels compiled with NCCL 2.29.2/3 on NCCL 2.29.7. This is not supported for GIN yet.</li>
</ul>
<h2>Bug fixes</h2>
<ul>
<li>Fix problems related to the introduction of git_version.h. (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/1960">#1960</a>)</li>
<li>Fix oneRankReduce when the number of elements is not a multiple of block number. (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/1950">#1950</a>)</li>
<li>Improve GIN handling in ncclCommGetAsyncError. (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/2019">#2019</a>)</li>
<li>Fix memory initialization in P2P transport. (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/1962">#1962</a>)</li>
<li>Fix hang issue in send/receive scheduling of repeated sparse patterns.</li>
<li>Fall back to cudaMemcpyAsync API when null/default stream is used for CE-based collective operations.</li>
<li>Free symmetric window objects automatically during commFree.</li>
<li>Fix a 16-bit overflow of signal and counter ids with GIN proxy.</li>
<li>Reset GIN counters and signals upon ncclDevCommDestroy.</li>
<li>Fix local data calculation during ncclGinIbP2PBarrier.</li>
</ul>
<h2>Other</h2>
<ul>
<li>Update license to Apache 2.0.</li>
</ul>
<h2>Known Limitations</h2>
<ul>
<li>Applications that use GIN APIs need to be recompiled with 2.29.7 to work with 2.29.7 runtime.</li>
<li>The Profiler Inspector example does not currently compile under CMake. This will be fixed soon.</li>
</ul>
<h2>Acknowledgments</h2>
<p>We thank the following contributors for their work on this release:</p>
<ul>
<li><a class="user-mention notranslate" href="https://github.com/sphish">@sphish</a>, <a class="user-mention notranslate" href="https://github.com/LyricZhao">@LyricZhao</a> for their contribution on improving the NCCL device API.</li>
<li><a class="user-mention notranslate" href="https://github.com/ruizhang1230">@ruizhang1230</a>, <a class="user-mention notranslate" href="https://github.com/Zhaojp-Frank">@Zhaojp-Frank</a>, <a class="user-mention notranslate" href="https://github.com/guoyuhong">@guoyuhong</a>, <a class="user-mention notranslate" href="https://github.com/argentea">@argentea</a> and the Amem project (<a href="https://github.com/inclusionAI/asystem-amem">https://github.com/inclusionAI/asystem-amem</a>) for their contribution on dynamic memory offload.</li>
</ul>
<p>We also thank the community for issue reports, testing, and feedback.</p>

Article Body:
