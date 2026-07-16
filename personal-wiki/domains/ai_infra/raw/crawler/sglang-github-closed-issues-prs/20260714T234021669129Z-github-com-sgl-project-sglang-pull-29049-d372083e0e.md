---
source_id: sglang-github-closed-issues-prs
title: '[PoC] HiCache L1-L2-Boundary write policy'
canonical_url: https://github.com/sgl-project/sglang/pull/29049
captured_at: '2026-07-14T23:40:21.669129+00:00'
content_hash: d372083e0e70e53364d9809a13ca83307745354cbf516d61bc6bb2c1f48bdd65
---
# [PoC] HiCache L1-L2-Boundary write policy

URL: https://github.com/sgl-project/sglang/pull/29049
State: closed
Labels: hicache
Closed at: 2026-07-14T15:41:44Z
Merged at: 

PoC of one of the options for achieving the ability to effectively use L2 size < L1 as part of the movement towards effective utilization of L3 cache.

Emulating the current main strategy and the proposed one on MoonCake Traces:

L2 = 2 L1 (default hicache ratio)
```
policy              requests  pages   l1_hit    l1+l2_hit  D     H      D+H   unique  failed_H
------------------  --------  ------  --------  ---------  ----  -----  ----  ------  --------
main_write_through  23608     409356    40.95%    47.39%   6000  12000  6000  12000   0       
boundary_l1_l2      23608     409356    40.95%    50.17%   6000  12000  997   17003   0    
```

L2 = 0.5 L1 (L2 < L1)
```
policy              requests  pages   l1_hit    l1+l2_hit  D     H     D+H   unique  failed_H
------------------  --------  ------  --------  ---------  ----  ----  ----  ------  --------
main_write_through  23608     409356    40.95%    40.98%   6000  3000  2966  6034    8877    
boundary_l1_l2      23608     409356    40.95%    44.67%   6000  3000  178   8822    0    
```



































<!-- pr-states:start -->
---
### CI States

Latest PR Test (Base): <!-- slot:pr-test:start -->:x: [Run #28956143508](https://github.com/sgl-project/sglang/actions/runs/28956143508)<!-- slot:pr-test:end -->
Latest PR Test (Extra): <!-- slot:pr-test-extra:start -->:x: [Run #28956143233](https://github.com/sgl-project/sglang/actions/runs/28956143233)<!-- slot:pr-test-extra:end -->
<!-- pr-states:end -->
