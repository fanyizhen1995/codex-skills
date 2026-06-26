---
source_id: nccl-github-releases
title: NCCL4py v0.3.1 Release
canonical_url: https://github.com/NVIDIA/nccl/releases/tag/nccl4py-v0.3.1
captured_at: '2026-06-26T02:01:31.912766+00:00'
content_hash: eae7888a466b021fb03a2137695bb3e67078475ec967d835bb0725a4458fe3b7
---
# NCCL4py v0.3.1 Release

URL: https://github.com/NVIDIA/nccl/releases/tag/nccl4py-v0.3.1

RSS Summary:
<h2>Highlights</h2>
<ul>
<li>Added <code>nccl.ep</code>, a Pythonic interface to <code>libnccl_ep.so</code> for expert<br />
parallel dispatch/combine workflows. The package exposes <code>Group</code>, <code>Handle</code>,<br />
<code>Tensor</code>, typed config dataclasses, <code>Algorithm</code>, <code>Layout</code>, <code>PassDir</code>, and the<br />
named input/output structs used by the NCCL EP API.</li>
<li>Added <code>nccl.core.device.cute</code>, enabling CuTeDSL kernels to call NCCL device<br />
APIs.</li>
<li>Added top-level stack diagnostics with <code>nccl.get_version()</code> and<br />
<code>nccl.show_versions()</code>, reporting <code>nccl4py</code>, <code>libnccl.so</code>, and<br />
<code>libnccl_ep.so</code> versions, CUDA build variants, and loaded shared-library<br />
paths.</li>
<li>Added free-threaded CPython support.</li>
</ul>
<h2>New Features</h2>
<h3>NCCL EP Python API</h3>
<ul>
<li>New <code>nccl.ep</code> package provides Pythonic access to the NCCL EP extension<br />
library.</li>
<li><code>Group.create()</code> creates EP groups from a <code>Communicator</code> and <code>GroupConfig</code>;<br />
<code>Group.create_handle()</code> creates handles with an explicit <code>Layout</code>.</li>
<li><code>Handle</code> supports <code>update()</code>, <code>dispatch()</code>, <code>combine()</code>, <code>complete()</code>, and<br />
<code>destroy()</code>.</li>
<li><code>DispatchInputs</code>, <code>DispatchOutputs</code>, <code>CombineInputs</code>, <code>CombineOutputs</code>, and<br />
<code>LayoutInfo</code> provide named containers for the tensors and metadata used by<br />
dispatch, combine, and handle setup.</li>
<li><code>Tensor</code> resolves Python buffers into <code>ncclEpTensor_t</code> descriptors.</li>
<li><code>GroupConfig</code>, <code>HandleConfig</code>, <code>DispatchConfig</code>, <code>CombineConfig</code>, and<br />
<code>AllocConfig</code> expose typed configuration objects.</li>
<li><code>AllocFn</code> and <code>FreeFn</code> expose caller-controlled EP allocation hooks.</li>
<li><code>nccl.ep.interop.torch.get_nccl_comm_from_group()</code> provides PyTorch interop<br />
for creating an NCCL communicator from a PyTorch process group's rank and<br />
world-size information.</li>
<li>Importing <code>nccl.ep</code> sets default <code>NCCL_EP_HOME</code> when bundled EP JIT headers<br />
are present, and <code>NCCL_HOME</code> when NCCL public headers are available from the<br />
installed <code>nvidia.nccl</code> package.</li>
<li><code>nccl.ep</code> checks that the loaded <code>libnccl.so</code> and <code>libnccl_ep.so</code> were built<br />
with the same CUDA major version. CUDA minor differences are accepted.</li>
</ul>
<h3>Communicator Configuration</h3>
<ul>
<li>Added <code>graph_stream_ordering</code> to <code>NCCLConfig</code>.</li>
</ul>
<h3>Device API and CuTe DSL</h3>
<ul>
<li>New <code>nccl.core.device.cute</code> module exposes the NCCL device API to CuTeDSL<br />
kernels, including communicator/window access, GIN primitives, barrier<br />
operations, and typed structs.</li>
<li>Added <code>bindings/nccl4py/examples/cute/main.py</code>, a GIN put/wait example with<br />
host-side validation.</li>
<li>Added <code>gin_strong_signals_required</code> and <code>gin_va_signals_required</code> to<br />
<code>NCCLDevCommRequirements</code> for configuring device communicator requirements.</li>
<li>Added <code>NcclGinType.GPI</code> for the GPU-Push Interface transport.</li>
</ul>
<h3>Version and Diagnostics API</h3>
<ul>
<li>Top-level <code>nccl.get_version()</code> returns a <code>VersionInfo</code> dataclass containing<br />
the <code>nccl4py</code> package version plus <code>LibraryInfo</code> entries for the loaded<br />
<code>libnccl.so</code> and, when available, <code>libnccl_ep.so</code>.</li>
<li>Top-level <code>nccl.show_versions()</code> prints the same stack information in a<br />
human-readable version block.</li>
<li>Direct library probes are available for each native library:<br />
<code>nccl.core.get_lib_version()</code> and <code>nccl.core.get_lib_path()</code> report the<br />
loaded <code>libnccl.so</code>; <code>nccl.ep.get_lib_version()</code> and<br />
<code>nccl.ep.get_lib_path()</code> report the loaded <code>libnccl_ep.so</code>.</li>
<li>Each <code>LibraryInfo</code> includes release version, CUDA build variant, and loaded<br />
shared-library path.</li>
</ul>
<h3>Installation and Packaging</h3>
<ul>
<li>CuTeDSL support can be installed through the CUDA-specific extras:<br />
<code>nccl4py[cu12]</code> installs <code>nvidia-cutlass-dsl&gt;=4.5.2,&lt;5.0</code>, and<br />
<code>nccl4py[cu13]</code> installs <code>nvidia-cutlass-dsl[cu13]&gt;=4.5.2,&lt;5.0</code>.</li>
<li>Wheels include package data for <code>nccl/ep/lib/libnccl_ep.so</code> plus EP JIT<br />
headers. The bundled <code>libnccl_ep.so</code> is built with CUDA 13, regardless of<br />
whether the <code>cu12</code> or <code>cu13</code> extra is installed. Users who want to use a<br />
CUDA 12 build of <code>libnccl_ep.so</code> must provide that library themselves, for<br />
example through <code>LD_PRELOAD</code> or <code>LD_LIBRARY_PATH</code>.</li>
<li>Wheels are available for free-threaded CPython 3.14t.</li>
</ul>
<h3>Examples and Documentation</h3>
<ul>
<li>Added Python examples for:
<ul>
<li>multiple devices in one process:<br />
<code>docs/examples/01_communicators/01_multiple_devices_single_process/python/</code>;</li>
<li>one device per MPI process:<br />
<code>docs/examples/01_communicators/03_one_device_per_process_mpi/python/</code>;</li>
<li>point-to-point ring pattern:<br />
<code>docs/examples/02_point_to_point/01_ring_pattern/python/</code>;</li>
<li>allreduce: <code>docs/examples/03_collectives/01_allreduce/python/</code>;</li>
<li>user-buffer allreduce:<br />
<code>docs/examples/04_user_buffer_registration/01_allreduce/python/</code>;</li>
<li>symmetric-memory allreduce:<br />
<code>docs/examples/05_symmetric_memory/01_allreduce/python/</code>;</li>
<li>symmetric-memory allgather:<br />
<code>docs/examples/05_symmetric_memory/02_allgather/python/</code>.</li>
</ul>
</li>
<li>Added nccl4py documentation under <code>docs/userguide/source/nccl4py/</code>, with the<br />
main entry point at <code>docs/userguide/source/nccl4py.rst</code>.</li>
</ul>
<h2>Breaking Changes</h2>
<h3>Removed APIs</h3>
<ul>
<li>
<p><code>nccl.core.group_simulate_end()</code> has been removed. Use<br />
<code>nccl.core.group_end(simulate=True)</code>:</p>
<div class="highlight highlight-source-python notranslate position-relative overflow-auto"><pre><span class="pl-k">from</span> <span class="pl-s1">nccl</span>.<span class="pl-s1">core</span> <span class="pl-k">import</span> <span class="pl-s1">group_end</span>, <span class="pl-s1">group_start</span>

<span class="pl-en">group_start</span>()
<span class="pl-c"># enqueue operations</span>
<span class="pl-s1">info</span> <span class="pl-c1">=</span> <span class="pl-en">group_end</span>(<span class="pl-s1">simulate</span><span class="pl-c1">=</span><span class="pl-c1">True</span>)</pre></div>
</li>
<li>
<p><code>NCCL_SPLIT_NOCOLOR</code> has been removed from the public constants. Use<br />
<code>color=None</code> when a rank should opt out of <code>Communicator.split()</code>.</p>
</li>
</ul>
<h3>Deprecated APIs</h3>
<ul>
<li><code>nccl.core.get_version()</code> remains available, but is deprecated. Use top-level<br />
<code>nccl.get_version()</code> for structured version information, or<br />
<code>nccl.show_versions()</code> for human-readable output.</li>
</ul>
<h3>Other Compatibility Notes</h3>
<ul>
<li>Public NCCL enum wrappers are pure-Python <code>IntEnum</code> or <code>IntFlag</code> classes.<br />
Integer compatibility is preserved, and dtype conversion remains supported.<br />
Code that depends on binding-backed enum class identity from earlier releases<br />
may need updates.</li>
<li>Enum members now follow the Python enum convention of <code>UPPER_SNAKE_CASE</code><br />
names, such as <code>CTAPolicy.DEFAULT</code>, <code>CommShrinkFlag.ABORT</code>,<br />
<code>WindowFlag.COLL_SYMMETRIC</code>, and <code>NcclCommMemStat.GPU_MEM_TOTAL</code>. The<br />
previous PascalCase/camelCase aliases, such as <code>CTAPolicy.Default</code> and<br />
<code>NcclCommMemStat.GpuMemTotal</code>, still work in 0.3.1 for compatibility, but<br />
will be removed in a future release. New code should use the uppercase names.</li>
</ul>
<h2>Fixes and Enhancements</h2>
<ul>
<li>Fixed pointer lifetime handling for non-blocking communicator and window<br />
initialization.</li>
<li>Torch interop covers <code>torch.uint32</code> and <code>torch.uint64</code> when those dtypes are<br />
available.</li>
</ul>
<h2>API Stability</h2>
<ul>
<li><code>nccl.ep</code> and <code>nccl.core.device.cute</code> are initial API support. Their public<br />
interfaces may change in future releases as the NCCL EP and CuTeDSL device<br />
API integration matures.</li>
</ul>

Article Body:
