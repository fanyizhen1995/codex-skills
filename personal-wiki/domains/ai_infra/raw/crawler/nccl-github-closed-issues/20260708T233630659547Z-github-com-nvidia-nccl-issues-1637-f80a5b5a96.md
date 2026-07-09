---
source_id: nccl-github-closed-issues
title: NCCL P2P issue using two RTX 5090
canonical_url: https://github.com/NVIDIA/nccl/issues/1637
captured_at: '2026-07-08T23:36:30.659547+00:00'
content_hash: f80a5b5a96887f0b652cbd73698988c3892105aba84c39e1927f98abeab93643
---
# NCCL P2P issue using two RTX 5090

URL: https://github.com/NVIDIA/nccl/issues/1637
State: closed
Labels: bug, duplicate, fixed
Closed at: 2025-06-19T05:16:36Z
Merged at: 

Greetings to all,

I’m trying to run various LLM inference engines (vLLM, TensorRT-LLM) on a machine with two RTX 5090 GPUs, specifically using tensor parallelism with a size of 2. Inference on a single GPU works fine, but I’m having trouble with two GPUs. Forcing NCCL_P2P_DISABLE=1 did not help to resolve the issue.

Could someone confirm whether  NCCL P2P communication is supported by the RTX 5090?

Thanks in advance!

My setup:
```
PyTorch version: 2.7.0a0+ecf3bae40a.nv25.02
Is debug build: False
CUDA used to build PyTorch: 12.8
ROCM used to build PyTorch: N/A

OS: Ubuntu 24.04.1 LTS (x86_64)
GCC version: (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0
Clang version: 18.1.3 (1ubuntu1)
CMake version: version 3.31.6
Libc version: glibc-2.39

Python version: 3.12.3 (main, Feb  4 2025, 14:48:35) [GCC 13.3.0] (64-bit runtime)
Python platform: Linux-5.14.0-503.29.1.el9_5.x86_64-x86_64-with-glibc2.39
Is CUDA available: True
CUDA runtime version: 12.8.61
CUDA_MODULE_LOADING set to: LAZY
GPU models and configuration:
GPU 0: NVIDIA GeForce RTX 5090
GPU 1: NVIDIA GeForce RTX 5090

Nvidia driver version: 570.124.06
cuDNN version: Probably one of the following:
/usr/lib/x86_64-linux-gnu/libcudnn.so.9.7.1
/usr/lib/x86_64-linux-gnu/libcudnn_adv.so.9.7.1
/usr/lib/x86_64-linux-gnu/libcudnn_cnn.so.9.7.1
/usr/lib/x86_64-linux-gnu/libcudnn_engines_precompiled.so.9.7.1
/usr/lib/x86_64-linux-gnu/libcudnn_engines_runtime_compiled.so.9.7.1
/usr/lib/x86_64-linux-gnu/libcudnn_graph.so.9.7.1
/usr/lib/x86_64-linux-gnu/libcudnn_heuristic.so.9.7.1
/usr/lib/x86_64-linux-gnu/libcudnn_ops.so.9.7.1
HIP runtime version: N/A
MIOpen runtime version: N/A
Is XNNPACK available: True

CPU:
Architecture:                         x86_64
CPU op-mode(s):                       32-bit, 64-bit
Address sizes:                        52 bits physical, 57 bits virtual
Byte Order:                           Little Endian
CPU(s):                               48
On-line CPU(s) list:                  0-47
Vendor ID:                            AuthenticAMD
Model name:                           AMD Ryzen Threadripper 7960X 24-Cores
CPU family:                           25
Model:                                24
Thread(s) per core:                   2
Core(s) per socket:                   24
Socket(s):                            1
Stepping:                             1
CPU(s) scaling MHz:                   17%
CPU max MHz:                          5665.0000
CPU min MHz:                          545.0000
BogoMIPS:                             8387.55
Flags:                                fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx mmxext fxsr_opt pdpe1gb rdtscp lm constant_tsc rep_good amd_lbr_v2 nopl nonstop_tsc cpuid extd_apicid aperfmperf rapl pni pclmulqdq monitor ssse3 fma cx16 pcid sse4_1 sse4_2 movbe popcnt aes xsave avx f16c rdrand lahf_lm cmp_legacy svm extapic cr8_legacy abm sse4a misalignsse 3dnowprefetch osvw ibs skinit wdt tce topoext perfctr_core perfctr_nb bpext perfctr_llc mwaitx cpb cat_l3 cdp_l3 hw_pstate ssbd mba perfmon_v2 ibrs ibpb stibp ibrs_enhanced vmmcall fsgsbase bmi1 avx2 smep bmi2 erms invpcid cqm rdt_a avx512f avx512dq rdseed adx smap avx512ifma clflushopt clwb avx512cd sha_ni avx512bw avx512vl xsaveopt xsavec xgetbv1 xsaves cqm_llc cqm_occup_llc cqm_mbm_total cqm_mbm_local avx512_bf16 clzero irperf xsaveerptr rdpru wbnoinvd amd_ppin cppc arat npt lbrv svm_lock nrip_save tsc_scale vmcb_clean flushbyasid decodeassists pausefilter pfthreshold avic v_vmsave_vmload vgif x2avic v_spec_ctrl vnmi avx512vbmi umip pku ospke avx512_vbmi2 gfni vaes vpclmulqdq avx512_vnni avx512_bitalg avx512_vpopcntdq la57 rdpid overflow_recov succor smca fsrm flush_l1d debug_swap
Virtualization:                       AMD-V
L1d cache:                            768 KiB (24 instances)
L1i cache:                            768 KiB (24 instances)
L2 cache:                             24 MiB (24 instances)
L3 cache:                             128 MiB (4 instances)
NUMA node(s):                         1
NUMA node0 CPU(s):                    0-47
Vulnerability Gather data sampling:   Not affected
Vulnerability Itlb multihit:          Not affected
Vulnerability L1tf:                   Not affected
Vulnerability Mds:                    Not affected
Vulnerability Meltdown:               Not affected
Vulnerability Mmio stale data:        Not affected
Vulnerability Reg file data sampling: Not affected
Vulnerability Retbleed:               Not affected
Vulnerability Spec rstack overflow:   Mitigation; Safe RET
Vulnerability Spec store bypass:      Mitigation; Speculative Store Bypass disabled via prctl
Vulnerability Spectre v1:             Mitigation; usercopy/swapgs barriers and __user pointer sanitization
Vulnerability Spectre v2:             Mitigation; Enhanced / Automatic IBRS; IBPB conditional; STIBP always-on; RSB filling; PBRSB-eIBRS Not affected; BHI Not affected
Vulnerability Srbds:                  Not affected
Vulnerability Tsx async abort:        Not affected

Versions of relevant libraries:
[pip3] numpy==1.26.4
[pip3] nvidia-ml-py==12.570.86
[pip3] pytorch-triton==3.1.0+cf34004b8.internal
[pip3] pyzmq==26.2.1
[pip3] torch==2.7.0a0+ecf3bae40a.nv25.2
[pip3] torchvision==0.22.0a0+ecf3bae40a.nv25.2
[pip3] transformers==4.49.0
[pip3] triton2==3.2.0
[pip3] tritonfrontend==2.55.0
[pip3] tritonserver==0.0.0
[conda] Could not collect
ROCM Version: Could not collect
Neuron SDK Version: N/A
vLLM Version: 0.7.4.dev254+ged6ea065.d20250311
vLLM Build Flags:
CUDA Archs: Not Set; ROCm: Disabled; Neuron: Disabled
GPU Topology:
GPU0    GPU1    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NODE    0-47    0               N/A
GPU1    NODE     X      0-47    0               N/A

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

NVIDIA_VISIBLE_DEVICES=all
CUBLAS_VERSION=12.8.3.14
NCCL_P2P_DISABLE=1
NVIDIA_REQUIRE_CUDA=cuda>=9.0
CUDA_CACHE_DISABLE=1
NCCL_VERSION=2.25.1
NVIDIA_DRIVER_CAPABILITIES=compute,utility,video
NVIDIA_PRODUCT_NAME=Triton Server
CUDA_VERSION=12.8.0.038
CUDNN_FRONTEND_VERSION=1.10.0
CUDNN_VERSION=9.7.1.26
NVIDIA_TRITON_SERVER_VERSION=25.02
LD_LIBRARY_PATH=/usr/local/lib/python3.12/dist-packages/cv2/../../lib64:/usr/local/lib:/usr/local/lib/python3.12/dist-packages/torch/lib:/usr/local/cuda/compat/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64
NVIDIA_BUILD_ID=143749533
CUDA_DRIVER_VERSION=570.86.10
NVIDIA_REQUIRE_JETPACK_HOST_MOUNTS=
VLLM_USE_V1=1
TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor_root
NCCL_CUMEM_ENABLE=0
TORCHINDUCTOR_COMPILE_THREADS=1
CUDA_MODULE_LOADING=LAZY


```
