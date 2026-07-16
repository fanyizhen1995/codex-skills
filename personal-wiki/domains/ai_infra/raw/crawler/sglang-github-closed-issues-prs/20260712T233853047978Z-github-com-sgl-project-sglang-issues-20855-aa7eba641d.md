---
source_id: sglang-github-closed-issues-prs
title: '[Bug] NCCL collective timeout when using TP=16 + DP=8 (works fine with TP=16
  only)'
canonical_url: https://github.com/sgl-project/sglang/issues/20855
captured_at: '2026-07-12T23:38:53.047978+00:00'
content_hash: aa7eba641d8ee4044d9c93074d99c8af4c88a459917cd6983c24b882a8f8fa35
---
# [Bug] NCCL collective timeout when using TP=16 + DP=8 (works fine with TP=16 only)

URL: https://github.com/sgl-project/sglang/issues/20855
State: closed
Labels: inactive
Closed at: 2026-07-12T00:35:46Z
Merged at: 

### Checklist

- [ ] I searched related issues but found no solution.
- [ ] The bug persists in the latest version.
- [ ] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [ ] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [ ] Please use English. Otherwise, it will be closed.

### Describe the bug

I encountered an NCCL timeout issue when running SGLang with both tensor parallelism (TP) and data parallelism (DP) enabled.
• TP=16 only → works fine
• TP=16 + DP=8 → consistently triggers NCCL timeout during DeepGEMM warmup
This suggests the issue may be related to multi-node / multi-group communication when DP is introduced
when GLM-5-FP8 or DeepSeek-V3/v3.2 on 2Node*8*H100
the error iinfo is:
```
DeepGEMM warmup:  45%|████▍     | 7297/16384 [05:39<06:03, 25.01it/s]
DeepGEMM warmup:  45%|████▍     | 7361/16384 [05:43<06:50, 21.99it/s][rank9]:[E318 08:49:08.965796097 ProcessGroupNCCL.cpp:744] [Rank 1] Some NCCL operations have failed or timed out. Due to the asynchronous nature of CUDA kernels, subsequent GPU operations might run on corrupted/incomplete data.
[rank9]:[E318 08:49:08.965849361 ProcessGroupNCCL.cpp:758] [Rank 1] To avoid data inconsistency, we are taking the entire process down.
[rank9]:[E318 08:49:08.969150748 ProcessGroupNCCL.cpp:2057] [PG ID 4 PG GUID 45 Rank 1] Process group watchdog thread terminated with exception: [Rank 1] Watchdog caught collective operation timeout: WorkNCCL(SeqNum=2, OpType=_REDUCE_SCATTER_BASE, NumelIn=1179648, NumelOut=589824, Timeout(ms)=600000) ran for 600001 milliseconds before timing out.
Exception raised from checkTimeout at /pytorch/torch/csrc/distributed/c10d/ProcessGroupNCCL.cpp:686 (most recent call first):
frame #0: c10::Error::Error(c10::SourceLocation, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >) + 0x80 (0x7f8b1257cb80 in /usr/local/lib/python3.12/dist-packages/torch/lib/libc10.so)
frame #1: c10d::ProcessGroupNCCL::WorkNCCL::checkTimeout(std::optional<std::chrono::duration<long, std::ratio<1l, 1000l> > >) + 0x247 (0x7f8a990a29d7 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #2: c10d::ProcessGroupNCCL::Watchdog::runLoop() + 0x1691 (0x7f8a990a75e1 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #3: c10d::ProcessGroupNCCL::Watchdog::run() + 0xdf (0x7f8a990a882f in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #4: <unknown function> + 0xecdb4 (0x7f8c920bfdb4 in /usr/lib/x86_64-linux-gnu/libstdc++.so.6)
frame #5: <unknown function> + 0x9caa4 (0x7f8c94c69aa4 in /usr/lib/x86_64-linux-gnu/libc.so.6)
frame #6: <unknown function> + 0x129c6c (0x7f8c94cf6c6c in /usr/lib/x86_64-linux-gnu/libc.so.6)

terminate called after throwing an instance of 'c10::DistBackendError'
  what():  [PG ID 4 PG GUID 45 Rank 1] Process group watchdog thread terminated with exception: [Rank 1] Watchdog caught collective operation timeout: WorkNCCL(SeqNum=2, OpType=_REDUCE_SCATTER_BASE, NumelIn=1179648, NumelOut=589824, Timeout(ms)=600000) ran for 600001 milliseconds before timing out.
Exception raised from checkTimeout at /pytorch/torch/csrc/distributed/c10d/ProcessGroupNCCL.cpp:686 (most recent call first):
frame #0: c10::Error::Error(c10::SourceLocation, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >) + 0x80 (0x7f8b1257cb80 in /usr/local/lib/python3.12/dist-packages/torch/lib/libc10.so)
frame #1: c10d::ProcessGroupNCCL::WorkNCCL::checkTimeout(std::optional<std::chrono::duration<long, std::ratio<1l, 1000l> > >) + 0x247 (0x7f8a990a29d7 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #2: c10d::ProcessGroupNCCL::Watchdog::runLoop() + 0x1691 (0x7f8a990a75e1 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #3: c10d::ProcessGroupNCCL::Watchdog::run() + 0xdf (0x7f8a990a882f in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #4: <unknown function> + 0xecdb4 (0x7f8c920bfdb4 in /usr/lib/x86_64-linux-gnu/libstdc++.so.6)
frame #5: <unknown function> + 0x9caa4 (0x7f8c94c69aa4 in /usr/lib/x86_64-linux-gnu/libc.so.6)
frame #6: <unknown function> + 0x129c6c (0x7f8c94cf6c6c in /usr/lib/x86_64-linux-gnu/libc.so.6)

Exception raised from run at /pytorch/torch/csrc/distributed/c10d/ProcessGroupNCCL.cpp:2063 (most recent call first):
frame #0: c10::Error::Error(c10::SourceLocation, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >) + 0x80 (0x7f8b1257cb80 in /usr/local/lib/python3.12/dist-packages/torch/lib/libc10.so)
frame #1: <unknown function> + 0xe69b51 (0x7f8a9907eb51 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #2: <unknown function> + 0x951271 (0x7f8a98b66271 in /usr/local/lib/python3.12/dist-packages/torch/lib/libtorch_cuda.so)
frame #3: <unknown function> + 0xecdb4 (0x7f8c920bfdb4 in /usr/lib/x86_64-linux-gnu/libstdc++.so.6)
frame #4: <unknown function> + 0x9caa4 (0x7f8c94c69aa4 in /usr/lib/x86_64-linux-gnu/libc.so.6)
frame #5: <unknown function> + 0x129c6c (0x7f8c94cf6c6c in /usr/lib/x86_64-linux-gnu/libc.so.6)

Fatal Python error: Aborted

Thread 0x00007f6f89fff6c0 (most recent call first):
  File "/usr/lib/python3.12/threading.py", line 359 in wait
  File "/usr/lib/python3.12/threading.py", line 655 in wait
  File "/usr/local/lib/python3.12/dist-packages/tqdm/_monitor.py", line 60 in run
  File "/usr/lib/python3.12/threading.py", line 1073 in _bootstrap_inner
  File "/usr/lib/python3.12/threading.py", line 1030 in _bootstrap

Thread 0x00007f7507fff6c0 (most recent call first):
  File "/usr/local/lib/python3.12/dist-packages/torch/_inductor/compile_worker/subproc_pool.py", line 73 in _recv_msg
  File "/usr/local/lib/python3.12/dist-packages/torch/_inductor/compile_worker/subproc_pool.py", line 228 in _read_thread
  File "/usr/lib/python3.12/threading.py", line 1010 in run
  File "/usr/lib/python3.12/threading.py", line 1073 in _bootstrap_inner
  File "/usr/lib/python3.12/threading.py", line 1030 in _bootstrap

Thread 0x00007f75c7fff6c0 (most recent call first):
  File "/usr/lib/python3.12/threading.py", line 359 in wait
  File "/usr/lib/python3.12/threading.py", line 655 in wait
  File "/usr/local/lib/python3.12/dist-packages/tqdm/_monitor.py", line 60 in run
  File "/usr/lib/python3.12/threading.py", line 1073 in _bootstrap_inner
  File "/usr/lib/python3.12/threading.py", line 1030 in _bootstrap

Thread 0x00007f8c94bcc300 (most recent call first):
  File "/usr/local/lib/python3.12/dist-packages/triton/compiler/compiler.py", line 473 in _init_handles
  File "/usr/local/lib/python3.12/dist-packages/triton/compiler/compiler.py", line 490 in launch_metadata
  File "/usr/local/lib/python3.12/dist-packages/triton/runtime/jit.py", line 756 in run
  File "/usr/local/lib/python3.12/dist-packages/triton/runtime/jit.py", line 419 in <lambda>
  File "/sgl-workspace/sglang/python/sglang/srt/layers/dp_attention.py", line 433 in memcpy_triton
  File "/sgl-workspace/sglang/python/sglang/srt/layers/dp_attention.py", line 540 in dp_scatter
  File "/sgl-workspace/sglang/python/sglang/srt/layers/communicator.py", line 806 in _gather_hidden_states_and_residual
  File "/sgl-workspace/sglang/python/sglang/srt/layers/communicator.py", line 546 in prepare_mlp
  File "/sgl-workspace/sglang/python/sglang/srt/models/deepseek_v2.py", line 2403 in forward
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1786 in _call_impl
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1775 in _wrapped_call_impl
  File "/sgl-workspace/sglang/python/sglang/srt/models/deepseek_v2.py", line 2730 in forward
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1786 in _call_impl
  File "/usr/local/lib/python3.12/dist-packages/torch/nn/modules/module.py", line 1775 in _wrapped_call_impl
  File "/sgl-workspace/sglang/python/sglang/srt/models/deepseek_v2.py", line 2919 in forward
  File "/usr/local/lib/python3.12/dist-packages/torch/utils/_contextlib.py", line 120 in decorate_context
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 719 in run_once
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 732 in capture_one_batch_size
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 513 in _capture_one_stream
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 526 in capture
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/cuda_graph_runner.py", line 370 in __init__
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 2156 in init_device_graphs
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 609 in initialize
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/model_runner.py", line 413 in __init__
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 330 in _init_model_runner
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 247 in __init__
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 522 in init_tp_model_worker
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 564 in init_model_worker
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 368 in __init__
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3130 in run_scheduler_process
  File "/usr/lib/python3.12/multiprocessing/process.py", line 108 in run
  File "/usr/lib/python3.12/multiprocessing/process.py", line 314 in _bootstrap
  File "/usr/lib/python3.12/multiprocessing/spawn.py", line 135 in _main
  File "/usr/lib/python3.12/multiprocessing/spawn.py", line 122 in spawn_main
  File "<string>", line 1 in <module>

Extension modules: numpy._core._multiarray_umath, numpy.linalg._umath_linalg, pybase64._pybase64, charset_normalizer.md, requests.packages.charset_normalizer.md, requests.packages.chardet.md, multidict._multidict, yarl._quoting_c, propcache._helpers_c, aiohttp._http_writer, aiohttp._http_parser, aiohttp._websocket.mask, aiohttp._websocket.reader_c, frozenlist._frozenlist, torch._C, torch._C._dynamo.autograd_compiler, torch._C._dynamo.eval_frame, torch._C._dynamo.guards, torch._C._dynamo.utils, torch._C._fft, torch._C._linalg, torch._C._nested, torch._C._nn, torch._C._sparse, torch._C._special, psutil._psutil_linux, zmq.backend.cython._zmq, PIL._imaging, sentencepiece._sentencepiece, regex._regex, yaml._yaml, markupsafe._speedups, cuda_utils, PIL._imagingft, numpy.random._common, numpy.random.bit_generator, numpy.random._bounded_integers, numpy.random._pcg64, numpy.random._generator, numpy.random._mt19937, numpy.random._philox, numpy.random._sfc64, numpy.random.mtrand, _cffi_backend, _cyutility, scipy._cyutility, scipy._lib._ccallback_c, scipy.linalg._fblas, scipy.linalg._flapack, scipy.linalg.cython_lapack, scipy.linalg._cythonized_array_utils, scipy.linalg._solve_toeplitz, scipy.linalg._batched_linalg, scipy.linalg._decomp_lu_cython, scipy.linalg._matfuncs_schur_sqrtm, scipy.linalg._matfuncs_expm, scipy.linalg._linalg_pythran, scipy.linalg.cython_blas, scipy.linalg._decomp_update, scipy.sparse._sparsetools, _csparsetools, scipy.sparse._csparsetools, scipy.sparse.linalg._dsolve._superlu, scipy.sparse.linalg._eigen.arpack._arpacklib, scipy.sparse.linalg._propack, scipy.optimize._group_columns, scipy._lib.messagestream, scipy.optimize._trlib._trlib, scipy.optimize._lbfgsb, _moduleTNC, scipy.optimize._moduleTNC, scipy.optimize._slsqplib, scipy.optimize._minpack, scipy.optimize._lsq.givens_elimination, scipy.optimize._zeros, scipy._lib._uarray._uarray, scipy.special._ufuncs_cxx, scipy.special._ellip_harm_2, scipy.special._special_ufuncs, scipy.special._gufuncs, scipy.special._ufuncs, scipy.special._specfun, scipy.special._comb, scipy.linalg._decomp_interpolative, scipy.optimize._bglu_dense, scipy.optimize._lsap, scipy.spatial._ckdtree, scipy.spatial._qhull, scipy.spatial._voronoi, scipy.spatial._hausdorff, scipy.spatial._distance_wrap, scipy.spatial.transform._rotation_cy, scipy.spatial.transform._rigid_transform_cy, scipy.optimize._direct, setproctitle._setproctitle, cuda.bindings._bindings.cydriver, cuda.bindings.cydriver, cuda.bindings.driver, tvm_ffi.core, cuda.bindings._bindings.cyruntime_ptds, cuda.bindings._bindings.cyruntime, cuda.bindings.cyruntime, cuda.bindings.runtime, cuda.bindings._bindings.cynvrtc, cuda.bindings.cynvrtc, cuda.bindings.nvrtc, msgspec._core, grpc._cython.cygrpc, google._upb._message, cuda.cudart, cuda.nvrtc, __triton_launcher (total: 112)

```

### Reproduction


```
apiVersion: leaderworkerset.x-k8s.io/v1
kind: LeaderWorkerSet
metadata:
  name: sglang
  # namespace: llmops-assets
spec:
  replicas: 1 # The number of pods.
  startupPolicy: LeaderCreated
  rolloutStrategy:
    type: RollingUpdate
    rollingUpdateConfiguration:
      maxSurge: 0
      maxUnavailable: 2 # Enable the MaxUnavailableStatefulSet feature gate.
  leaderWorkerTemplate:
    size: 2
    restartPolicy: RecreateGroupOnPodRestart
    leaderTemplate:
      metadata:
        labels:
          role: leader
      spec:
        nodeSelector:
          kubernetes.io/hostname: llm27
        containers:
          - name: sglang-head
            image: x.x.x.x:5000/aip/sglang:v0.5.9-0318
            imagePullPolicy: IfNotPresent
            env:
              - name: NCCL_DEBUG
                value: "INFO"
              - name: CUDA_DISABLE_CONTROL
                value: "true"
              - name: UNBALANCED_MODEL_LOADING_TIMEOUT_S
                value: "72000"
              - name: USE_VLLM
                value: "1"
              - name: BASE_MODEL
                value: /models/DeepSeek-V3.2-Exp
              - name: ENABLE_EP
                value: "1"
              - name: ENABLE_DP
                value: "0"
              - name: SGLANG_SET_CPU_AFFINITY
                value: "true"
              - name: NVSHMEM_HCA_PE_MAPPING
                # should modify according your rdma env
                value: "mlx5_0:0:1,mlx5_2:1:1,mlx5_4:2:1,mlx5_6:3:1,mlx5_1:4:1,mlx5_3:5:1,mlx5_5:6:1,mlx5_7:7:1"
              - name: NCCL_IB_HCA
                value: ^=mlx5_0,mlx5_4
              - name: NVSHMEM_IB_TRAFFIC_CLASS
                value: "16"
              - name: NVSHMEM_IB_GID_INDEX
                value: "3"
              - name: NVSHMEM_ENABLE_NIC_PE_MAPPING
                value: "1"
              - name: CUDA_LAUNCH_BLOCKING
                value: "0"
              - name: SGLANG_MOONCAKE_TRANS_THREAD
                value: "8"
              - name: SGLANG_ENABLE_JIT_DEEPGEMM
                value: "1"
              - name: SGLANG_CHUNKED_PREFIX_CACHE_THRESHOLD
                value: "0"
              - name: NCCL_IB_QPS_PER_CONNECTION
                value: "8"
              - name: NCCL_IB_SPLIT_DATA_ON_QPS
                value: "1"
              - name: NCCL_NET_PLUGIN
                value: none
              - name: NCCL_IB_TC
                value: "136"
              - name: NCCL_MIN_NCHANNELS
                value: "4"
              - name: MC_TE_METRIC
                value: "true"
              - name: NCCL_IB_SL
                value: "5"
              - name: MOONCAKE_MASTER
                value: "mooncake-master:50051"
              - name: MOONCAKE_TE_META_DATA_SERVER
                value: "http://mooncake-master:8080/metadata"
              - name: MOONCAKE_PROTOCOL
                value: "rdma"
              - name: MOONCAKE_DEVICE
                value: "mlx5_0"
              - name: MOONCAKE_GLOBAL_SEGMENT_SIZE
                value: "10gb" #Configure the cache size per replica on demand.
              - name: MOONCAKE_LOCAL_BUFFER_SIZE
                value: "4294967296"
              - name: MC_MS_AUTO_DISC
                value: "1"
            command:
            - bash
            - -c
            args:
            - |
              python3 -m sglang.launch_server \
              --model /models/GLM-5-FP8  \
              --dist-init-addr $LWS_LEADER_ADDRESS:20000 \
              --tensor-parallel-size 16 \
              --nnodes $LWS_GROUP_SIZE  \
              --node-rank $LWS_WORKER_INDEX \
              --trust-remote-code \
              --host 0.0.0.0 \
              --port 8000 \
              --dist-timeout 7200 \
              --enable-metrics \
              --reasoning-parser glm45 \
              --tool-call-parser glm47 \
              --speculative-algorithm EAGLE \
              --speculative-num-steps 3 \
              --speculative-eagle-topk 1 \
              --speculative-num-draft-tokens 4 \
              --mem-fraction-static 0.80 \
              --log-requests --log-requests-leve 1 \
              --kv-cache-dtype fp8_e4m3 \
               --enable-dp-attention \
               -dp 8
            ports:
            - containerPort: 8000
              name: http
              protocol: TCP
            - containerPort: 20000
              name: distributed
              protocol: TCP
            resources:
              limits:
                nvidia.com/gpu: "8"
                rdma/hca_shared_devices_a: 1
                memory: 250Gi
                #vke.volcengine.com/infiniband-rdma: "8"  # Use this parameter for H100's InfiniBand RDMA.
              requests:
                nvidia.com/gpu: "8"
                rdma/hca_shared_devices_a: 1
                cpu: 95
                #vke.volcengine.com/infiniband-rdma: "8"  # Use this parameter for H100's InfiniBand RDMA.
            securityContext:
              capabilities:
                add:
                - IPC_LOCK
            terminationMessagePath: /dev/termination-log
            terminationMessagePolicy: File
            # volumeMounts:
            # - mountPath: /models/deepseek
            #   name: models
            # - mountPath: /dev/shm
            #   name: shared-mem
            # readinessProbe:
            #   tcpSocket:
            #     port: 8080
            #   initialDelaySeconds: 15
            #   periodSeconds: 10
            volumeMounts:
              - mountPath: /dev/shm
                name: dshm
              - name: models-vol
                mountPath: /models
        volumes:
        - name: dshm
          emptyDir:
            medium: Memory
            sizeLimit: 50Gi
        - name: models-vol
          hostPath:
            path: /mnt/disk1/models
            type: Directory
        
    workerTemplate:
      metadata:
        # annotations:
        #   nvidia.com/use-gpuuuid: "GPU-0f95da43-eab5-e7f3-252e-39f9353f7bb2"
      spec:
        nodeSelector:
          kubernetes.io/hostname: llm25
        containers:
          - name: sglang-worker
            image: x.x.x.x:5000/aip/sglang:v0.5.9-0318
            imagePullPolicy: IfNotPresent
            # workingDir: /sgl-workspace
            command:
            - bash
            - -c
            # In the command below, set NCCL_IB_GID_INDEX=3 only for H20 GPU. H100 GPU does not require this configuration.
            args:
            - |
              python3 -m sglang.launch_server \
              --model /models/GLM-5-FP8  \
              --dist-init-addr $LWS_LEADER_ADDRESS:20000 \
              --tensor-parallel-size 16 \
              --nnodes $LWS_GROUP_SIZE  \
              --node-rank $LWS_WORKER_INDEX \
              --trust-remote-code \
              --host 0.0.0.0 \
              --port 8000 \
              --dist-timeout 7200 \
              --enable-metrics \
              --reasoning-parser glm45 \
              --tool-call-parser glm47 \
              --speculative-algorithm EAGLE \
              --speculative-num-steps 3 \
              --speculative-eagle-topk 1 \
              --speculative-num-draft-tokens 4 \
              --mem-fraction-static 0.80 \
              --log-requests --log-requests-leve 1 \
              --kv-cache-dtype fp8_e4m3 \
               --enable-dp-attention \
               -dp 8
            env:
              - name: CUDA_DISABLE_CONTROL
                value: "true"
              - name: UNBALANCED_MODEL_LOADING_TIMEOUT_S
                value: "72000"
              - name: USE_VLLM
                value: "1"
              - name: BASE_MODEL
                value: /models/DeepSeek-V3.2-Exp
              - name: ENABLE_EP
                value: "1"
              - name: ENABLE_DP
                value: "0"
              - name: SGLANG_SET_CPU_AFFINITY
                value: "true"
              - name: NVSHMEM_HCA_PE_MAPPING
                # should modify according your rdma env
                value: "mlx5_0:0:1,mlx5_2:1:1,mlx5_4:2:1,mlx5_6:3:1,mlx5_1:4:1,mlx5_3:5:1,mlx5_5:6:1,mlx5_7:7:1"
              - name: NCCL_IB_HCA
                value: ^=mlx5_0,mlx5_4
              - name: NVSHMEM_IB_TRAFFIC_CLASS
                value: "16"
              - name: NVSHMEM_IB_GID_INDEX
                value: "3"
              - name: NVSHMEM_ENABLE_NIC_PE_MAPPING
                value: "1"
              - name: CUDA_LAUNCH_BLOCKING
                value: "0"
              - name: SGLANG_MOONCAKE_TRANS_THREAD
                value: "8"
              - name: SGLANG_ENABLE_JIT_DEEPGEMM
                value: "1"
              - name: SGLANG_CHUNKED_PREFIX_CACHE_THRESHOLD
                value: "0"
              - name: NCCL_IB_QPS_PER_CONNECTION
                value: "8"
              - name: NCCL_IB_SPLIT_DATA_ON_QPS
                value: "1"
              - name: NCCL_NET_PLUGIN
                value: none
              - name: NCCL_IB_TC
                value: "136"
              - name: NCCL_MIN_NCHANNELS
                value: "4"
              - name: MC_TE_METRIC
                value: "true"
              - name: NCCL_IB_SL
                value: "5"
              - name: MOONCAKE_MASTER
                value: "mooncake-master:50051"
              - name: MOONCAKE_TE_META_DATA_SERVER
                value: "http://mooncake-master:8080/metadata"
              - name: MOONCAKE_PROTOCOL
                value: "rdma"
              - name: MOONCAKE_DEVICE
                value: "mlx5_0"
              - name: MOONCAKE_GLOBAL_SEGMENT_SIZE
                value: "10gb" #Configure the cache size per replica on demand.
              - name: MOONCAKE_LOCAL_BUFFER_SIZE
                value: "4294967296"
              - name: MC_MS_AUTO_DISC
                value: "1"
              # - name: MEM_FRACTION_STATIC
              #   value: "0.88"
              # - name: "EXTRA_CMD"
              #   value: "--dist-timeout 7200 --watchdog-timeout 36000  --cuda-graph-max-bs 16 --torch-compile-max-bs 8  --attention-backend fa3  --context-length 163840  --max-running-requests 128 --mem-fraction-static 0.78"
            ports:
            - containerPort: 8000
              name: http
              protocol: TCP
            resources:
              limits:
                nvidia.com/gpu: "8"
                rdma/hca_shared_devices_a: 1
                memory: 250Gi
                # cpu: 5
                #vke.volcengine.com/infiniband-rdma: "8"  # Use this parameter for H100's InfiniBand RDMA.
              requests:
                nvidia.com/gpu: "8"
                rdma/hca_shared_devices_a: 1
                cpu: 95
                #vke.volcengine.com/infiniband-rdma: "8"  # Use this parameter for H100's InfiniBand RDMA.
            securityContext:
              capabilities:
                add: ["IPC_LOCK"]
            volumeMounts:
              - mountPath: /dev/shm
                name: dshm
              - name: nfs-vol
                mountPath: /models
        # dnsPolicy: ClusterFirst
        volumes:
        - name: dshm
          emptyDir:
            medium: Memory
            sizeLimit: 50Gi
        - name: nfs-vol
          nfs:
            server: x.x.x.x      # ← 这里换成你的 NFS 服务器 IP
            path: /mnt/disk2/models           # ← 这里换成你 NFS 上共享的目录
            readOnly: false
---
apiVersion: v1
kind: Service
metadata:
  name: sglang-leader
spec:
  type: NodePort
  selector:
    leaderworkerset.sigs.k8s.io/name: sglang
    role: leader
  ports:
  - name: serving
    port: 8000
    targetPort: 8000
    nodePort: 30567
  - name: metrics
    port: 8080
    targetPort: 8080

```

### Environment

```
root@sglang-0:/sgl-workspace/sglang# python3 -m sglang.check_env
Python: 3.12.3 (main, Jan 22 2026, 20:57:42) [GCC 13.3.0]
CUDA available: True
GPU 0,1,2,3,4,5,6,7: NVIDIA H100 80GB HBM3
GPU 0,1,2,3,4,5,6,7 Compute Capability: 9.0
CUDA_HOME: /usr/local/cuda
NVCC: Cuda compilation tools, release 12.9, V12.9.86
CUDA Driver Version: 570.124.06
PyTorch: 2.9.1+cu129
sglang: 0.5.9
sgl_kernel: 0.3.21
flashinfer_python: 0.6.3
flashinfer_cubin: 0.6.3
flashinfer_jit_cache: 0.6.3+cu129
triton: 3.5.1
transformers: 5.2.0
torchao: 0.9.0
numpy: 2.4.2
aiohttp: 3.13.3
fastapi: 0.131.0
hf_transfer: 0.1.9
huggingface_hub: 1.5.0
interegular: 0.3.3
modelscope: 1.34.0
orjson: 3.11.7
outlines: 0.1.11
packaging: 26.0
psutil: 7.2.2
pydantic: 2.12.5
python-multipart: 0.0.22
pyzmq: 27.1.0
uvicorn: 0.41.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.1.27
openai: 2.6.1
tiktoken: 0.12.0
anthropic: 0.83.0
litellm: Module Not Found
decord2: 3.0.0
NVIDIA Topology: 
        GPU0    GPU1    GPU2    GPU3    GPU4    GPU5    GPU6    GPU7    NIC0    NIC1    NIC2    NIC3  NIC4     NIC5    NIC6    NIC7    CPU Affinity    NUMA Affinity   GPU NUMA ID
GPU0     X      NV18    NV18    NV18    NV18    NV18    NV18    NV18    PIX     PIX     NODE    NODE  SYS      SYS     SYS     SYS     0-47,96-143     0               N/A
GPU1    NV18     X      NV18    NV18    NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE  SYS      SYS     SYS     SYS     0-47,96-143     0               N/A
GPU2    NV18    NV18     X      NV18    NV18    NV18    NV18    NV18    NODE    NODE    PIX     PIX   SYS      SYS     SYS     SYS     0-47,96-143     0               N/A
GPU3    NV18    NV18    NV18     X      NV18    NV18    NV18    NV18    NODE    NODE    NODE    NODE  SYS      SYS     SYS     SYS     0-47,96-143     0               N/A
GPU4    NV18    NV18    NV18    NV18     X      NV18    NV18    NV18    SYS     SYS     SYS     SYS   PIX      PIX     NODE    NODE    48-95,144-191   1               N/A
GPU5    NV18    NV18    NV18    NV18    NV18     X      NV18    NV18    SYS     SYS     SYS     SYS   NODE     NODE    NODE    NODE    48-95,144-191   1               N/A
GPU6    NV18    NV18    NV18    NV18    NV18    NV18     X      NV18    SYS     SYS     SYS     SYS   NODE     NODE    PIX     PIX     48-95,144-191   1               N/A
GPU7    NV18    NV18    NV18    NV18    NV18    NV18    NV18     X      SYS     SYS     SYS     SYS   NODE     NODE    NODE    NODE    48-95,144-191   1               N/A
NIC0    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS      X      PIX     NODE    NODE  SYS      SYS     SYS     SYS
NIC1    PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS     PIX      X      NODE    NODE  SYS      SYS     SYS     SYS
NIC2    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE     X      PIX   SYS      SYS     SYS     SYS
NIC3    NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS     NODE    NODE    PIX      X    SYS      SYS     SYS     SYS
NIC4    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS    X       PIX     NODE    NODE
NIC5    SYS     SYS     SYS     SYS     PIX     NODE    NODE    NODE    SYS     SYS     SYS     SYS   PIX       X      NODE    NODE
NIC6    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS   NODE     NODE     X      PIX
NIC7    SYS     SYS     SYS     SYS     NODE    NODE    PIX     NODE    SYS     SYS     SYS     SYS   NODE     NODE    PIX      X 

Legend:

  X    = Self
  SYS  = Connection traversing PCIe as well as the SMP interconnect between NUMA nodes (e.g., QPI/UPI)
  NODE = Connection traversing PCIe as well as the interconnect between PCIe Host Bridges within a NUMA node
  PHB  = Connection traversing PCIe as well as a PCIe Host Bridge (typically the CPU)
  PXB  = Connection traversing multiple PCIe bridges (without traversing the PCIe Host Bridge)
  PIX  = Connection traversing at most a single PCIe bridge
  NV#  = Connection traversing a bonded set of # NVLinks

NIC Legend:

  NIC0: mlx5_0
  NIC1: mlx5_1
  NIC2: mlx5_2
  NIC3: mlx5_3
  NIC4: mlx5_4
  NIC5: mlx5_5
  NIC6: mlx5_6
  NIC7: mlx5_7


ulimit soft: 1048576
```
