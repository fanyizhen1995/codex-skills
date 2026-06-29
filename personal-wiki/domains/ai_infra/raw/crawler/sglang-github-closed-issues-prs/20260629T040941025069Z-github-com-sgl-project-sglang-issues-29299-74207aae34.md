---
source_id: sglang-github-closed-issues-prs
title: 【求助】zmq send 对应的recv逻辑在哪里呢？
canonical_url: https://github.com/sgl-project/sglang/issues/29299
captured_at: '2026-06-29T04:09:41.025069+00:00'
content_hash: 74207aae34e714cb72cac6ff2d7f84e7121d39994f3176e77bf198fb21adbb74
---
# 【求助】zmq send 对应的recv逻辑在哪里呢？

URL: https://github.com/sgl-project/sglang/issues/29299
State: closed
Labels: 
Closed at: 2026-06-28T06:04:08Z
Merged at: 

我的程序在跟新权重的时候出现了atu error，经过排查发现在sglang/srt/managers/communicator.py中FanOutCommunicator类调用queueing_call的时候，
https://github.com/sgl-project/sglang/blob/5a15cde858ea09b77116212a39356f2fc51b8584/python/sglang/srt/managers/communicator.py#L44
zmq.send_pyobj后出现了atu，想要进一步排查，所以想知道这个代码逻辑是在做什么？从代码上来看应该是zmq使用ipc通信，我怀疑引发atu的位置在recv端的接受请求后的动作，但是我找不到这个recv端在哪里。。。
