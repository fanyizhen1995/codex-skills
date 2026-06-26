---
source_id: nccl-github-releases
title: NCCL v2.29.2-1 Release
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/v2.29.2-1
captured_at: '2026-06-26T02:01:31.915699+00:00'
content_hash: 8cad9c13c0efb6752181bda242f2507ac0cace9215b9aaf953f25064572b769d
---
# NCCL v2.29.2-1 Release

URL: https://github.com/NVIDIA/nccl/releases/tag/v2.29.2-1

RSS Summary:
<h2>Device API Improvements</h2>
<ul>
<li>Supports Device API struct versioning for backwards compatibility with future versions.</li>
<li>Adds ncclCommQueryProperties to allow Device API users to check supported features before creating a DevComm.</li>
<li>Adds host-accessible device pointer functions from symmetric registered ncclWindows.</li>
<li>Adds improved GIN documentation to clarify the support matrix.</li>
</ul>
<h2>New One-Sided Host APIs</h2>
<ul>
<li>Adds new host APIs (ncclPutSignal, ncclWaitSignal, etc) for both network and NVL using zero-SM.</li>
<li>One-sided communication operation writes data from the local buffer to a remote peer’s registered memory window without explicit participation from the target process.</li>
<li>Utilizes CopyEngine for NVL transfer and CPU proxy for network.</li>
<li>Requires CUDA 12.5 or greater.</li>
</ul>
<h2>New Experimental Python language binding (NCCL4Py)</h2>
<ul>
<li>Pythonic NCCL API for Python applications - native collectives, P2P and other NCCL operations.</li>
<li>Interoperable with CUDA Python ecosystem: DLPack/CUDA Array Interface, and special support for PyTorch and CuPy.</li>
<li>Automatic cleanup of NCCL-managed resources (GPU buffers, registered buffers/windows, custom reduction operations).</li>
</ul>
<h2>New LLVM intermediate representation (IR) support</h2>
<ul>
<li>Exposes NCCL Device APIs through LLVM IR to enable consumption by diverse code generation systems.</li>
<li>Example usages include high-level languages, Just-In-Time (JIT) compilers, and domain-specific languages (DSL).</li>
<li>Build with EMIT_LLVM_IR=1 to generate LLVM IR bitcode.</li>
<li>Requires CUDA 12 and Clang 21.</li>
</ul>
<h2>Built-in hybrid (LSA+GIN) symmetric kernel for AllGather</h2>
<ul>
<li>Adds a new hierarchical kernel using MCRing (NVLS multicast + Ring) to improve performance and scalability of AllGather.</li>
<li>Requires symmetric memory registration and GIN.</li>
</ul>
<h2>New ncclCommGrow API</h2>
<ul>
<li>Adds the ability to dynamically and efficiently add ranks to an existing NCCL communicator.</li>
<li>Use ncclCommGrow with ncclCommShrink to adjust membership of communicators in response to failing and recovering nodes.</li>
<li>Also addresses the need for elastic applications to expand a running job by integrating new ranks.</li>
</ul>
<h2>Multi-segment registration</h2>
<ul>
<li>Expands buffer registration to support multiple segments of physical memory mapped to one contiguous VA space for the p2p, ib and nvls transports.</li>
<li>Enables support for expandable segments in PyTorch.</li>
</ul>
<h2>Improves scalability of AllGatherV pattern</h2>
<ul>
<li>Adds support for a scalable allgatherv pattern (group of broadcasts).</li>
<li>Adds new scheduler path and new kernels to improve performance at large scale.</li>
</ul>
<h2>Debuggability &amp; Observability Improvements</h2>
<ul>
<li>RAS supports realtime monitoring to continuously track peer status changes.</li>
<li>Inspector adds support for Prometheus format output (with NCCL_INSPECTOR_PROM_DUMP=1), in addition to the existing JSON format.</li>
<li>Adds profiler support for CopyEngine(CE) based collectives.</li>
</ul>
<h2>Community Engagement</h2>
<ul>
<li>Adds contribution guide: <a href="https://github.com/NVIDIA/nccl/blob/master/CONTRIBUTING.md">https://github.com/NVIDIA/nccl/blob/master/CONTRIBUTING.md</a></li>
<li>Adds NCCL_SOCKET_POLL_TIMEOUT_MSEC which allows waiting instead of spinning during bootstrap in order to reduce CPU usage. (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/1759">#1759</a>)</li>
<li>Fixes segfault in ncclGin initialization that can happen if ncclGinIbGdaki.devices() fails after init() succeeds. (Github PR <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/pull/1881">#1881</a>)</li>
<li>Fixes crash that can happen when calling p2p and then collectives while using the same user buffer. (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/1859">#1859</a>)</li>
<li>Fixes bug that was lowering performance on some sm80 or earlier machines with one NIC per GPU. (Github Issue <a class="issue-link js-issue-link" href="https://github.com/NVIDIA/nccl/issues/1876">#1876</a>)</li>
<li>Clears non-fatal CUDA errors so they do not propagate. (<a href="https://github.com/pytorch/pytorch/issues/164402">Pytorch Issue #164402</a>)</li>
</ul>
<h2>Other Improvements</h2>
<ul>
<li>Improves performance of large-size AllGather operations using symmetric memory buffers on Blackwell by transparently switching to CE collectives.</li>
<li>Improves the default number of channels per net peer for all-to-all, send, and recv to achieve better performance.</li>
<li>Improves performance tuning of 256M-512M message sizes on Blackwell for AllReduce.</li>
<li>Enables built-in symmetric kernels only on fully connected nvlink systems, as PCIE systems do not perform as well.</li>
<li>Prints git branch and commit checksum at the INFO level during NCCL initialization.</li>
<li>Improves support for symmetric window registrations on CUDA versions prior to 12.1.</li>
<li>Relaxes symmetric buffer registration requirements for collectives so that users can leverage the symmetric kernels with only one of the buffers being registered, when possible.</li>
<li>All2all, send, recv now obey NCCL_NETDEVS_POLICY. For these operations, NCCL will now by default use a subset of available network devices as dictated by the Network Device Policy.</li>
<li>Fixes a hang on GB200/300 + CX8 when the user disables GDR.</li>
<li>Fixes a bug that could cause AllReduce on ncclFloat8e4m3 to yield “no algorithm/protocol available”.</li>
<li>ncclCommWindowRegister will now return a NULL window if the system does not support window registration.</li>
<li>More prominent error when cuMulticastBind fails and NCCL_NVLS_ENABLE=2.</li>
<li>Upgrades to doca gpunetio v1.1.</li>
</ul>
<h2>Known Limitations</h2>
<ul>
<li>Since Device API was experimental in 2.28.x, applications that use the Device API in v2.28 may need modifications to work with v2.29.</li>
<li>One-sided host APIs (e.g. ncclPutSignal) currently do not support graph capture. Future releases will add cuda graph support.</li>
<li>The improved AllGatherV support breaks the NCCL profiler support for ncclBroadcast operations, limiting visibility to API events. NCCL_ALLGATHERV_ENABLE=0 can be used as a workaround until it is fixed in a future release.</li>
<li>NCCL4Py (experimental) has a known issue with cuda.core 0.5.0. We currently recommend using cuda.core 0.4.1 with nccl4py.</li>
</ul>

Article Body:
