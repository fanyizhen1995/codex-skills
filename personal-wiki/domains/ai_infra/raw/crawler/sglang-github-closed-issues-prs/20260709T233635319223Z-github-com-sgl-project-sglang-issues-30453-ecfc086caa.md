---
source_id: sglang-github-closed-issues-prs
title: '[Bug] GLM-Image AR SRT server hits Ascend AICore timeout on Ascend A3 after
  multiple 1280x1280 image generations'
canonical_url: https://github.com/sgl-project/sglang/issues/30453
captured_at: '2026-07-09T23:36:35.319223+00:00'
content_hash: ecfc086caad946e7d5732cd1ffe0568b9c0fb40cda2172d656d370fbb4689e03
---
# [Bug] GLM-Image AR SRT server hits Ascend AICore timeout on Ascend A3 after multiple 1280x1280 image generations

URL: https://github.com/sgl-project/sglang/issues/30453
State: closed
Labels: 
Closed at: 2026-07-09T09:24:24Z
Merged at: 

### Checklist

- [x] I searched related issues but found no solution.
- [x] The bug persists in the latest version.
- [x] Issues without environment info and a minimal reproducible demo are hard to resolve and may receive no feedback.
- [x] If this is not a bug report but a general question, please start a discussion at https://github.com/sgl-project/sglang/discussions. Otherwise, it will be closed.
- [x] Please use English. Otherwise, it will be closed.

### Describe the bug

When use pr #25381 and running GLM-Image image generation with a separated AR SRT backend and DiT service on Ascend A3 (4 GPU), the AR SRT server may fail after processing around 30+ image generation requests. But work normal in 910B3 .

The DiT service reports:

```text
requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

start command
```
1. ar server start command

export HCCL_IF_BASE_PORT=23000
export HCCL_HOST_SOCKET_PORT_RANGE="23000-23199"
export HCCL_NPU_SOCKET_PORT_RANGE="23200-23399"

nohup sglang serve \
--model-path /nas/disk1/GLM-Image/vision_language_encoder/ \
--tokenizer-path /nas/disk1/GLM-Image/processor/ \
--port 8764 \
--log-level debug \
--base-gpu-id 0 \
--tp-size 2 \
--enable-multimodal --cuda-graph-bs-decode 1 --device npu --attention-backend ascend --mem-fraction-static 0.5  --disable-fast-image-processor \
--host 0.0.0.0 > ar_server.log 2>&1 &

tail -f ar_server.log



2. dit server  start command

export HCCL_IF_BASE_PORT=24000
export HCCL_HOST_SOCKET_PORT_RANGE="24000-24199"
export HCCL_NPU_SOCKET_PORT_RANGE="24200-24399"

nohup sglang serve \
  --model-path /nas/disk1/GLM-Image/ \
  --srt-encoder-url http://127.0.0.1:8764 \
  --port 8898 \
  --warmup-mode off \
  --log-level debug \
  --tp-size 2 \
  --num-gpus 2 \
  --base-gpu-id 2 \
  --host 0.0.0.0 > diffusion_server.log 2>&1 &

tail -f diffusion_server.log
```


Detail log:
AR SERVER：
```
[2026-07-07 07:11:00 TP0] Decode batch, #running-req: 1, #token: 2048, token usage: 0.00, npu graph: False, gen throughput (token/s): 18.60, #queue-req: 0
[2026-07-07 07:11:02 TP0] Decode batch, #running-req: 1, #token: 2048, token usage: 0.00, npu graph: False, gen throughput (token/s): 18.77, #queue-req: 0
[2026-07-07 07:11:03] INFO:     127.0.0.1:45272 - "POST /generate HTTP/1.1" 200 OK
[2026-07-07 07:20:43 TP1] Scheduler hit an exception: Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4270, in run_scheduler_process
    scheduler.run_event_loop()
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 1487, in run_event_loop
    dispatch_event_loop(self)
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 4135, in dispatch_event_loop
    scheduler.event_loop_overlap()
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch/utils/_contextlib.py", line 120, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 1571, in event_loop_overlap
    batch_result = self.run_batch(batch)
                   ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/utils/nvtx_utils.py", line 109, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py", line 3232, in run_batch
    batch_result = self.model_worker.forward_batch_generation(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/managers/tp_worker.py", line 495, in forward_batch_generation
    forward_batch = ForwardBatch.init_new(batch, self.model_runner)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/forward_batch_info.py", line 849, in init_new
    ret._compute_mrope_positions(model_runner, batch)
  File "/sgl-workspace/sglang/python/sglang/srt/model_executor/forward_batch_info.py", line 1106, in _compute_mrope_positions
    ).to(dtype=torch.int64, device=model_runner.device, non_blocking=True)
      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch_npu/contrib/transfer_to_npu.py", line 182, in decorated
    return fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^
RuntimeError: The Inner error is reported as above. The process exits for this inner error, and the current copy params are srclen=24, dstlen=24, kind=1.
Since the operator is called asynchronously, the stacktrace may be inaccurate. If you want to get the accurate stacktrace, please set the environment variable ASCEND_LAUNCH_BLOCKING=1.
Note: ASCEND_LAUNCH_BLOCKING=1 will force ops to run in synchronous mode, resulting in performance degradation. Please unset ASCEND_LAUNCH_BLOCKING in time after debugging.
[ERROR] 2026-07-07-07:20:43 (PID:163686, Device:1, RankID:-1) ERR00100 PTA call acl api failed.
EZ9999: Inner Error!
EZ9999[PID: 163686] 2026-07-07-07:20:43.817.613 (EZ9999):  Kernel task happen error, retCode=0x25, [aicore timeout].[FUNC:PreCheckTaskErr][FILE:davinci_kernel_task.cc][LINE:1493]
        TraceBack (most recent call last):
       rtMemcpyAsync execution failed, reason=aicore timeout[FUNC:FuncErrorReason][FILE:error_message_manage.cc][LINE:61]
       [Call][Rts]call rts api [rtMemcpyAsync] failed, retCode is 507014[FUNC:ReportCallError][FILE:log_inner.cpp][LINE:148]


[2026-07-07 07:20:43] SIGQUIT received. signum=None, frame=None. It usually means one child failed.
[2026-07-07 07:20:43] Sleeping 5 seconds before crash diagnostics to let GPU activity settle.
[163686] [2026-07-07 07:20:43:938] torch.distributed: [ERROR] [164517] Find exception when finishedNPUExecutionInternal, query:build/CMakeFiles/torch_npu.dir/compiler_depend.ts:61 NPU function error: acl::AclQueryEventRecordedStatus(event_, &currStatus), error code is 507014
[ERROR] 2026-07-07-07:20:43 (PID:163686, Device:1, RankID:-1) ERR00100 PTA call acl api failed
[Error]: The aicore execution times out.
        Rectify the fault based on the error information in the ascend log.
EE9999: Inner Error!
EE9999[PID: 163686] 2026-07-07-07:20:43.937.475 (EE9999):  rtEventQueryStatus execution failed, reason=aicore timeout[FUNC:FuncErrorReason][FILE:error_message_manage.cc][LINE:61]
        TraceBack (most recent call last):
       [Query][Status]query event recorded status failed, runtime result = 507014[FUNC:ReportCallError][FILE:log_inner.cpp][LINE:148]   

Exception raised from query at build/CMakeFiles/torch_npu.dir/compiler_depend.ts:61 (most recent call first):
frame #0: c10::Error::Error(c10::SourceLocation, std::__cxx11::basic_string<char, std::char_traits<char>, std::alloca
[rank1]:[E707 07:20:43.220330280 compiler_depend.ts:1693] [Rank 1] HCCL watchdog thread terminated with exception:
[ERROR] 2026-07-07-07:20:43 (PID:163686, Device:1, RankID:-1) ERR02005 DIST internal error
terminate called after throwing an instance of 'std::runtime_error'
  what():  [Rank 1] HCCL watchdog thread terminated with exception:
[ERROR] 2026-07-07-07:20:43 (PID:163686, Device:1, RankID:-1) ERR02005 DIST internal error
Fatal Python error: Aborted

Thread 0x0000fff8d7fff120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff8e3fff120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff8effff120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff8fbfff120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff907fff120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff910e2f120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff914e3f120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff918e4f120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 327 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/queues.py", line 231 in _feed
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff94bfff120 (most recent call first):
  File "/sgl-workspace/sglang/python/sglang/srt/utils/watchdog.py", line 147 in _watchdog_once
  File "/sgl-workspace/sglang/python/sglang/srt/utils/watchdog.py", line 127 in _watchdog_thread
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fff93ffff120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 331 in wait
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 629 in wait
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/tqdm/_monitor.py", line 60 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000fffcc3fff120 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch/_inductor/compile_worker/subproc_pool.py", line 61 in _recv_msg     
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch/_inductor/compile_worker/subproc_pool.py", line 195 in _read_thread 
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 982 in run
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1045 in _bootstrap_inner
  File "/usr/local/python3.11.14/lib/python3.11/threading.py", line 1002 in _bootstrap

Thread 0x0000ffff7f6ad060 (most recent call first):
  File "/usr/local/python3.11.14/lib/python3.11/selectors.py", line 415 in select
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/connection.py", line 948 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/popen_fork.py", line 40 in wait
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/process.py", line 149 in join
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/managers.py", line 676 in _finalize_manager
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/util.py", line 227 in __call__
  File "/usr/local/Ascend/cann-8.5.0/python/site-packages/tbe/common/repository_manager/utils/multiprocess_util.py", line 63 in finalize  File "/usr/local/Ascend/cann-8.5.0/python/site-packages/tbe/common/repository_manager/route.py", line 219 in finalize
  File "/usr/local/Ascend/cann-8.5.0/python/site-packages/tbe/common/repository_manager/route.py", line 54 in wrapper
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/util.py", line 227 in __call__
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/util.py", line 303 in _run_finalizers
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/util.py", line 337 in _exit_function
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/process.py", line 317 in _bootstrap
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/spawn.py", line 135 in _main
  File "/usr/local/python3.11.14/lib/python3.11/multiprocessing/spawn.py", line 122 in spawn_main
  File "<string>", line 1 in <module>


[2026-07-07 07:20:50] Pyspy dump for PID 163685 (py-spy dump --native --pid 163685):
Process 163685: sglang::scheduler_TP0
Python v3.11.14 (/usr/local/python3.11.14/bin/python3.11)

Thread 163685 (idle): "MainThread"
    read (libc.so.6)
    eventfd_read (libc.so.6)
    0xfffcfedd3074 (libtorch_npu.so)
    c10_npu::NPUStream::stream (libtorch_npu.so)
    0xfffcfed25adc (libtorch_npu.so)
    0xfffcfed265ac (libtorch_npu.so)
    0xfffcfeca682c (libtorch_npu.so)
    0xfffcfeca7f88 (libtorch_npu.so)
    0xfffcfeca8a94 (libtorch_npu.so)
    0xfffcfeca9c20 (libtorch_npu.so)
    0xfffcfe93aeec (libtorch_npu.so)
    at::_ops::copy_::call (libtorch_cpu.so)
    0xfffcfec94b98 (libtorch_npu.so)
    0xfffcfe9e2438 (libtorch_npu.so)
    0xfffcfe9e2660 (libtorch_npu.so)
    at::_ops::_to_copy::redispatch (libtorch_cpu.so)
    c10::impl::wrap_kernel_functor_unboxed_<c10::impl::detail::WrapFunctionIntoFunctor_<c10::CompileTimeFunctionPointer<at::Tensor(at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat>), &at::(anonymous namespace)::_to_copy(at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat>)>, at::Tensor, c10::guts::typelist::typelist<at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat> > >, at::Tensor(at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat>)>::call (libtorch_cpu.so)
    at::_ops::_to_copy::redispatch (libtorch_cpu.so)
    torch::autograd::VariableType::(anonymous namespace)::_to_copy (libtorch_cpu.so)
    c10::impl::wrap_kernel_functor_unboxed_<c10::impl::detail::WrapFunctionIntoFunctor_<c10::CompileTimeFunctionPointer<at::Tensor(c10::DispatchKeySet, at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat>), &torch::autograd::VariableType::(anonymous namespace)::_to_copy(c10::DispatchKeySet, at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat>)>, at::Tensor, c10::guts::typelist::typelist<c10::DispatchKeySet, at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat> > >, at::Tensor(c10::DispatchKeySet, at::Tensor const&, std::optional<c10::ScalarType>, std::optional<c10::Layout>, std::optional<c10::Device>, std::optional<bool>, bool, std::optional<c10::MemoryFormat>)>::call (libtorch_cpu.so)
    at::_ops::_to_copy::call (libtorch_cpu.so)
    at::native::to (libtorch_cpu.so)
    c10::impl::wrap_kernel_functor_unboxed_<c10::impl::detail::WrapFunctionIntoFunctor_<c10::CompileTimeFunctionPointer<at::Tensor(at::Tensor const&, c10::Device, c10::ScalarType, bool, bool, std::optional<c10::MemoryFormat>), &at::(anonymous namespace)::(anonymous namespace)::wrapper_CompositeImplicitAutograd_device_to(at::Tensor const&, c10::Device, c10::ScalarType, bool, bool, std::optional<c10::MemoryFormat>)>, at::Tensor, c10::guts::typelist::typelist<at::Tensor const&, c10::Device, c10::ScalarType, bool, bool, std::optional<c10::MemoryFormat> > >, at::Tensor(at::Tensor const&, c10::Device, c10::ScalarType, bool, bool, std::optional<c10::MemoryFormat>)>::call (libtorch_cpu.so)
    at::_ops::to_device::call (libtorch_cpu.so)
    torch::autograd::THPVariable_to (libtorch_python.so)
    decorated (torch_npu/contrib/transfer_to_npu.py:182)
    _compute_mrope_positions (forward_batch_info.py:1106)
    init_new (forward_batch_info.py:849)
    forward_batch_generation (tp_worker.py:495)
    run_batch (scheduler.py:3232)
    wrapper (utils/nvtx_utils.py:109)
    event_loop_overlap (scheduler.py:1571)
    decorate_context (torch/utils/_contextlib.py:120)
    dispatch_event_loop (scheduler.py:4135)
    run_event_loop (scheduler.py:1487)
    run_scheduler_process (scheduler.py:4270)
    run (multiprocessing/process.py:108)
    _bootstrap (multiprocessing/process.py:314)
    _main (multiprocessing/spawn.py:135)
    spawn_main (multiprocessing/spawn.py:122)
    <module> (<string>:1)
    0xffff9cbf7400 (libc.so.6)
Thread 163887 (idle): "Thread-1 (_read_thread)"
    read (libc.so.6)
    _recv_msg (torch/_inductor/compile_worker/subproc_pool.py:61)
    _read_thread (torch/_inductor/compile_worker/subproc_pool.py:195)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 164569 (idle): "Thread-2"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc57b38 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:331)
    wait (threading.py:629)
    run (tqdm/_monitor.py:60)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 164570 (idle): "Thread-3 (_watchdog_thread)"
    clock_nanosleep (libc.so.6)
    time_sleep (libpython3.11.so.1.0)
    _watchdog_once (utils/watchdog.py:147)
    _watchdog_thread (utils/watchdog.py:127)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 164985 (idle): "Thread-4"
    read (libc.so.6)
    os_read (libpython3.11.so.1.0)
    _recv (multiprocessing/connection.py:395)
    _recv_bytes (multiprocessing/connection.py:430)
    recv (multiprocessing/connection.py:250)
    _callmethod (multiprocessing/managers.py:822)
    get (<string>:2)
    run (tbe/common/repository_manager/utils/multiprocess_util.py:68)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165128 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165129 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165130 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165131 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165132 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165133 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165134 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)
Thread 165135 (idle): "QueueFeederThread"
    0xffff9cc4cb78 (libc.so.6)
    0xffff9cc588c4 (libc.so.6)
    PyThread_acquire_lock_timed (libpython3.11.so.1.0)
    lock_PyThread_acquire_lock (libpython3.11.so.1.0)
    wait (threading.py:327)
    _feed (multiprocessing/queues.py:231)
    run (threading.py:982)
    _bootstrap_inner (threading.py:1045)
    _bootstrap (threading.py:1002)
    thread_run (libpython3.11.so.1.0)
    0xffff9cc50398 (libc.so.6)
    0xffff9ccb9e9c (libc.so.6)

[2026-07-07 07:21:06] Pyspy failed (py-spy dump --native --pid 163686). Error: Error: Failed to get stack traces

Caused by:
    0: UNW_EBADREG: bad register number
    1: UNW_EBADREG: bad register number

[2026-07-07 07:21:06] Pyspy failed (py-spy dump  --pid 163686). Error: Error: Failed to get process executable name. Check that the process is running.

Caused by:
    0: No such file or directory (os error 2)
    1: No such file or directory (os error 2)

[2026-07-07 07:21:06] All pyspy dump attempts failed for PID 163686.
[2026-07-07 07:21:06] CUDA user-triggered coredump is not enabled. Set CUDA_ENABLE_USER_TRIGGERED_COREDUMP=1 before CUDA initialization.[2026-07-07 07:21:06] CUDA coredump pipe not found for PID 163685: /home/aiuser/corepipe.cuda.main-a3-it011793-n-2-7d-5b6c6c4b65-xc7tq.163685. Ensure CUDA_ENABLE_USER_TRIGGERED_COREDUMP=1 was set before this process initialized CUDA.
[2026-07-07 07:21:06] Waiting 60.0 seconds for CUDA coredumps before exiting.
[2026-07-07 07:22:06] kill_process_tree called: parent_pid=163411, include_parent=True, pid=163411
```

Dit server log:
```
[2026-07-07 07:11:27] INFO:     172.61.10.88:19003 - "GET /v1/images/9fe0a09e-9060-4e72-a309-5d1d5e753ee9/content HTTP/1.1" 200 OK      
[07-07 07:11:27] Setting `num_frames` to 1 for image generation model
[07-07 07:11:27] Sampling params:
                       width: 1280
                      height: 1280
                  num_frames: 1
                         fps: 24
                      prompt: 一个充满活力的未来城市夜景栩栩如生，高耸入云的摩天大楼上装饰着复杂的霓虹灯、发光标识和动态全息影像，璀璨光
芒照亮整座城市。在繁忙的视野中心，一座巨大的数字广告牌横跨着中央建筑的闪亮外墙，以绚丽的色彩和流畅迷人的动画吸引着居民和游客。广告牌上醒
目而充满活力的字体大胆地宣告着：“欢迎来到梦想成真之地”，其发光的未来感字体立即吸引眼球。正下方，较小的字体优雅地滚动着清晰的优雅字体：“ 
现在体验未来”，邀请路人进一步探索这个令人兴奋的目的地。令人着迷的文字周围是引人入胜的动态画面，描绘着流线型飞行汽车穿梭于闪烁的城市景观 
、霓虹灯光波在建筑间脉动，以及以生动全息影像展示的未来科技产品。先进的科技嗡鸣声与远处的节奏音乐交织，营造出沉浸式氛围，完美展现了霓虹城
充满活力、令人兴奋且富有远见的魅力。
                  neg_prompt: Bright tones, overexposed, static, blurred details, subtitles, style, works, paintings, images, static, overall gray, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, still picture, messy background, three legs, many people in the background, walking backwards
                        seed: 42
                 infer_steps: 30
      num_outputs_per_prompt: 1
              guidance_scale: 1.5
     embedded_guidance_scale: 6.0
                    n_tokens: None
                  flow_shift: None
                  image_path: None
                 save_output: True
            output_file_path: outputs/eba101e7-6520-4133-bfe9-04e462e612c7.jpg

[07-07 07:11:27] Running pipeline stages: ['glm_image_ar', 'glm_image_before_denoising_stage', 'DenoisingStage', 'decoding_stage']      
[07-07 07:11:27] [GlmImageAR] started... (7.51 GB left)
[07-07 07:16:27] Setting `num_frames` to 1 for image generation model
[07-07 07:21:27] Setting `num_frames` to 1 for image generation model
[07-07 07:22:06] [GlmImageAR] Error during execution after 639108.9182 ms: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
Traceback (most recent call last):
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 788, in urlopen
    response = self._make_request(
               ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 534, in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connection.py", line 571, in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 1395, in getresponse
    response.begin()
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 325, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 294, in _read_status
    raise RemoteDisconnected("Remote end closed connection without"
http.client.RemoteDisconnected: Remote end closed connection without response

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/adapters.py", line 696, in send
    resp = conn.urlopen(
           ^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 842, in urlopen
    retries = retries.increment(
              ^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/util/retry.py", line 498, in increment
    raise reraise(type(error), error, _stacktrace)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/util/util.py", line 38, in reraise
    raise value.with_traceback(tb)
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 788, in urlopen
    response = self._make_request(
               ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 534, in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connection.py", line 571, in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 1395, in getresponse
    response.begin()
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 325, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 294, in _read_status
    raise RemoteDisconnected("Remote end closed connection without"
urllib3.exceptions.ProtocolError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/stages/base.py", line 370, in __call__
    result = self.forward(batch, server_args)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch/utils/_contextlib.py", line 120, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/stages/model_specific_stages/glm_image.py", line 338, 
in forward
    prior_token_id, prior_token_image_ids = self.generate_prior_tokens(
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/stages/model_specific_stages/glm_image.py", line 279, 
in generate_prior_tokens
    response = requests.post(
               ^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/api.py", line 134, in post
    return request("post", url, data=data, json=json, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/api.py", line 71, in request
    return session.request(method=method, url=url, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/sessions.py", line 651, in request
    resp = self.send(prep, **send_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/sessions.py", line 784, in send
    r = adapter.send(request, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/adapters.py", line 711, in send
    raise ConnectionError(err, request=request)
requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))       
[07-07 07:22:06] Error executing request eba101e7-6520-4133-bfe9-04e462e612c7: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
Traceback (most recent call last):
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 788, in urlopen
    response = self._make_request(
               ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 534, in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connection.py", line 571, in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 1395, in getresponse
    response.begin()
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 325, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 294, in _read_status
    raise RemoteDisconnected("Remote end closed connection without"
http.client.RemoteDisconnected: Remote end closed connection without response

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/adapters.py", line 696, in send
    resp = conn.urlopen(
           ^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 842, in urlopen
    retries = retries.increment(
              ^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/util/retry.py", line 498, in increment
    raise reraise(type(error), error, _stacktrace)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/util/util.py", line 38, in reraise
    raise value.with_traceback(tb)
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 788, in urlopen
    response = self._make_request(
               ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connectionpool.py", line 534, in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/urllib3/connection.py", line 571, in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 1395, in getresponse
    response.begin()
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 325, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/http/client.py", line 294, in _read_status
    raise RemoteDisconnected("Remote end closed connection without"
urllib3.exceptions.ProtocolError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/managers/gpu_worker.py", line 387, in _execute_forward_common        
    result = forward_fn()
             ^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/managers/gpu_worker.py", line 324, in <lambda>
    forward_fn=lambda: self.pipeline.forward(req, self.server_args),
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch/utils/_contextlib.py", line 120, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/composed_pipeline_base.py", line 993, in forward      
    return self.executor.execute_with_profiling(self.stages, batch, server_args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/executors/pipeline_executor.py", line 135, in execute_with_profiling
    batch = self.execute(stages, batch, server_args)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/executors/parallel_executor.py", line 130, in execute 
    return self._execute_stages(
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/executors/parallel_executor.py", line 104, in _execute_stages
    batch = self._run_stage_with_executor_hooks(
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/executors/pipeline_executor.py", line 115, in _run_stage_with_executor_hooks
    payload = self.run_stage_with_context(
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/executors/pipeline_executor.py", line 206, in run_stage_with_context
    return run_stage(stage, payload)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/executors/parallel_executor.py", line 134, in <lambda>    lambda stage, current: stage(current, server_args),
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/stages/base.py", line 370, in __call__
    result = self.forward(batch, server_args)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/torch/utils/_contextlib.py", line 120, in decorate_context
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/stages/model_specific_stages/glm_image.py", line 338, 
in forward
    prior_token_id, prior_token_image_ids = self.generate_prior_tokens(
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/pipelines_core/stages/model_specific_stages/glm_image.py", line 279, 
in generate_prior_tokens
    response = requests.post(
               ^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/api.py", line 134, in post
    return request("post", url, data=data, json=json, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/api.py", line 71, in request
    return session.request(method=method, url=url, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/sessions.py", line 651, in request
    resp = self.send(prep, **send_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/sessions.py", line 784, in send
    r = adapter.send(request, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/python3.11.14/lib/python3.11/site-packages/requests/adapters.py", line 711, in send
    raise ConnectionError(err, request=request)
requests.exceptions.ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))       
[07-07 07:22:06] Failed to generate output for prompt: Model generation returned no output. Error from scheduler: Error executing request eba101e7-6520-4133-bfe9-04e462e612c7: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))    
Traceback (most recent call last):
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/utils/logging_utils.py", line 628, in log_generation_timer
    yield timer
  File "/sgl-workspace/sglang/python/sglang/multimodal_gen/runtime/entrypoints/openai/utils.py", line 355, in process_generation_batch  
    raise RuntimeError(
RuntimeError: Model generation returned no output. Error from scheduler: Error executing request eba101e7-6520-4133-bfe9-04e462e612c7: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

### Reproduction

Use bug report start command and run about 30 times generation:
Note: If this problem can be resolve in any image version is OK.
Can run this script to replay this problem:
[longtext-bench.zip](https://github.com/user-attachments/files/29779516/longtext-bench.zip)

Client report: 
<img width="1890" height="1362" alt="Image" src="https://github.com/user-attachments/assets/79794027-4745-48af-81e4-66d39735acc0" />



### Environment

root@main-a3-it011793-n-2-7d-5b6c6c4b65-4wjmg:/home/aiuser# python3 -m sglang.check_env
Python: 3.11.14 (main, Jan 19 2026, 06:28:35) [GCC 11.4.0]
NPU available: True
NPU 0,1: Ascend910_9362
CANN_HOME: /usr/local/Ascend/cann-8.5.0
CANN: Not Available
BiSheng: 2026-01-13T09:46:36+08:00 clang version 15.0.5 (clang-5c68a1cb1231 flang-5c68a1cb1231)
Ascend Driver Version: Not Available
PyTorch: 2.8.0+cpu
sglang: 0.5.12
sglang-kernel: Module Not Found
flashinfer_python: Module Not Found
flashinfer_cubin: Module Not Found
flashinfer_jit_cache: Module Not Found
triton: Module Not Found
transformers: 5.6.0
torchao: 0.9.0
numpy: 2.3.5
aiohttp: 3.13.5
fastapi: 0.136.1
huggingface_hub: 1.15.0
interegular: 0.3.3
modelscope: 1.37.0
orjson: 3.11.9
outlines: 0.1.11
packaging: 26.2
psutil: 7.2.2
pydantic: 2.13.4
python-multipart: 0.0.28
pyzmq: 27.1.0
uvicorn: 0.47.0
uvloop: 0.22.1
vllm: Module Not Found
xgrammar: 0.2.0
openai: 2.6.1
tiktoken: 0.13.0
anthropic: 0.102.0
litellm: Module Not Found
torchcodec: Module Not Found
torch_npu: 2.8.0.post2
sgl-kernel-npu: 2026.5.1
deep_ep: 1.0.0+775c4204.cann.8.5.0.b232
Ascend Topology:
           Phy-ID12   Phy-ID13
Phy-ID12   X          SIO
Phy-ID13   SIO        X

Legend:

  X    = Self
  SYS  = Path traversing PCIe and NUMA nodes. Nodes are connected through SMP, such as QPI, UPI.
  PHB  = Path traversing PCIe and the PCIe host bridge of a CPU.
  PIX  = Path traversing a single PCIe switch
  PXB  = Path traversing multipul PCIe switches
  HCCS = Connection traversing HCCS.
  SIO  = Path traversing the SIO bus
  HCCS_SW = Connection traversing HCCS through a switch
  NA   = Unknown relationship.

ulimit soft: 1048576
