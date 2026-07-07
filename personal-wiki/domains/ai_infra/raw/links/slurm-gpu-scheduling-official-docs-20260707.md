---
type: RawSource
title: Slurm GPU And Generic Resource Scheduling Documentation
source_kind: web
url: https://slurm.schedmd.com/gres.html
related_urls:
  - https://slurm.schedmd.com/sbatch.html
  - https://slurm.schedmd.com/srun.html
captured: 2026-07-07
status: ingested
---
# Source

Official Slurm documentation:

- Generic Resource Scheduling: https://slurm.schedmd.com/gres.html
- sbatch command: https://slurm.schedmd.com/sbatch.html
- srun command: https://slurm.schedmd.com/srun.html

Captured as a concise source note for `ai_infra` HPC and GPU scheduling coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Slurm Generic Resource Scheduling (GRES) lets a cluster define generic resources such as GPU models and expose resource counts for jobs and job steps.
- GRES configuration distinguishes resource name, optional type such as a GPU model, and resource count requested by a job or job step.
- Slurm job steps can allocate generic resources from the generic resources allocated to the parent job, and a step can request a different resource count than the job allocation.
- Slurm supports non-consumable GRES through `no_consume`, which is useful for node attributes that can be requested without reducing a count.
- The `sbatch` and `srun` command surfaces are the submission and step execution boundaries that training launchers or wrapper scripts must integrate with when running distributed jobs under Slurm.
- Slurm GPU/GRES evidence is HPC scheduler evidence. It does not by itself prove Kubernetes scheduling behavior unless a separate bridge, operator, or integration source is cited.

# Use In Wiki

Use this source note for Slurm GPU/GRES resource modeling, job allocation, job-step resource allocation, and the boundary between HPC batch scheduling and AI training launchers. Pair it with Kubernetes or KubeRay sources before making Kubernetes-specific claims.
