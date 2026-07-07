---
type: RawSource
title: Ceph Distributed Storage Documentation
source_kind: web
url: https://docs.ceph.com/en/latest/architecture/
related_urls:
  - https://docs.ceph.com/en/latest/cephfs/
  - https://docs.ceph.com/en/latest/rbd/
captured: 2026-07-07
status: ingested
---
# Source

Official Ceph documentation:

- Ceph architecture: https://docs.ceph.com/en/latest/architecture/
- CephFS: https://docs.ceph.com/en/latest/cephfs/
- Ceph Block Device: https://docs.ceph.com/en/latest/rbd/

Captured as a concise source note for `ai_infra` network-storage-cluster coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Ceph is a distributed storage system built around RADOS, with object storage daemons, monitors, and placement logic forming the storage cluster substrate.
- CephFS provides a file-system interface backed by Ceph storage and metadata services, which makes it relevant to shared filesystem coverage.
- Ceph RBD provides block-device semantics backed by Ceph objects, which makes it relevant to virtual disk, container volume, and block-storage coverage.
- Ceph evidence supports distributed storage behavior and storage interface boundaries. It is not AI-specific evidence unless paired with a source that ties Ceph to AI workload data paths, checkpointing, or training cluster operations.
- Use CephFS and RBD as storage-layer primitives; do not use them to claim EFA, Lustre, Weka, NVMe-oF, or GPU-direct behavior.

# Use In Wiki

Use this source note for source-backed claims about Ceph distributed storage architecture, CephFS shared filesystems, and RBD block devices as cluster storage building blocks.
