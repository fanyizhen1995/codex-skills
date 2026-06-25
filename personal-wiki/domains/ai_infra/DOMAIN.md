# AI Infrastructure

## Boundary

This domain covers infrastructure used to build, train, evaluate, deploy,
serve, observe, and operate AI systems. It includes accelerator and cluster
architecture, distributed training, inference serving, model runtime systems,
MLOps platforms, data and feature pipelines, vector/search infrastructure,
evaluation infrastructure, reliability, security, cost, and performance work
when those topics are tied to AI workloads.

This domain does not cover general ML theory, model architecture details,
prompting techniques, product strategy, application UX, or generic distributed
systems unless the material has direct infrastructure implications for AI
systems.

Cross-domain links are allowed for reusable concepts, organizations, people,
papers, and systems that are relevant outside AI infrastructure. Keep the
primary curated page in this domain only when the core claim is about AI
infrastructure behavior, operations, or design tradeoffs.

## Read Order

1. Read this `DOMAIN.md`.
2. Read `wiki/index.md`.
3. Open specific wiki pages by following links.
4. Open raw sources only when validating or ingesting claims.

## Core Topics

- Accelerator and GPU cluster infrastructure
- Distributed training and checkpointing systems
- Inference serving, batching, routing, and model runtimes
- Data pipelines, feature stores, embeddings, and vector/search systems
- Evaluation, observability, reliability, and incident response for AI systems
- Security, governance, cost, and capacity planning for AI platforms

## Common Aliases

- ai infra
- ai-infra
- AI infrastructure

## Ingest Notes

Raw sources enter through `raw/inbox/` unless they already fit a specific raw
subdirectory.

When ingesting, update `ingest.md` and preserve source references.

## Domain-Specific Rules

- Keep model or algorithm details only when they explain infrastructure
  requirements, constraints, or tradeoffs.
- Prefer separating papers, projects, and operational decisions into their
  matching wiki subdirectories.
