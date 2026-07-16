---
source_id: sglang-github-closed-issues-prs
title: '[PD] Stride KV token->page indices on device before D2H copy'
canonical_url: https://github.com/sgl-project/sglang/pull/31173
captured_at: '2026-07-14T23:40:21.667804+00:00'
content_hash: fbfa7a777380c22ea782440c55f246cfe52eb02a5694c226478c07031652d33b
---
# [PD] Stride KV token->page indices on device before D2H copy

URL: https://github.com/sgl-project/sglang/pull/31173
State: closed
Labels: run-ci
Closed at: 2026-07-14T17:08:31Z
Merged at: 2026-07-14T17:08:31Z

## Problem

`kv_to_page_indices` copies every KV token index to host (`.cpu().numpy()`) and
then strides on CPU. As a result the D2H traffic on each PD `send_kv_chunk` /
`send_metadata` scales with the number of tokens.

## Fix

Stride and divide on the device tensor first, then copy only the resulting
~`num_pages` indices to host — roughly `page_size`x less D2H per send. The
resulting page indices are identical, so behavior is unchanged.

Applies to the main KV send path and the SWA / DSA state payloads on both the
prefill and decode sides.















<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #29319625804](https://github.com/sgl-project/sglang/actions/runs/29319625804)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #29319625632](https://github.com/sgl-project/sglang/actions/runs/29319625632)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
