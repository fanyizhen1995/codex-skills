---
source_id: sglang-github-closed-issues-prs
title: '[PD][NIXL] Handle decode abort notifications'
canonical_url: https://github.com/sgl-project/sglang/pull/30301
captured_at: '2026-07-10T23:37:20.328312+00:00'
content_hash: 937d945d0db2a87dd954d44897105b3d1ec4644e74a25fe597f03814f471b485
---
# [PD][NIXL] Handle decode abort notifications

URL: https://github.com/sgl-project/sglang/pull/30301
State: closed
Labels: 
Closed at: 2026-07-10T05:16:41Z
Merged at: 

## Motivation

`CommonKVReceiver` sends an `ABORT` control message when a decode request is cancelled or times out. The NIXL prefill bootstrap loop previously treated that message as foreign traffic and exited on its guard assertion, preventing subsequent bootstrap traffic from being processed.

## Changes

- validate and handle decode-side `ABORT` notifications in the NIXL bootstrap loop
- mark active rooms as failed while leaving terminal or unknown rooms unchanged
- cover active, terminal, unknown, and malformed notifications

## Related work

#30352 covers the same abort path and adds sticky failed-state handling. Synchronized transfer-worker cleanup and prefill failure propagation are handled separately by #30329.
