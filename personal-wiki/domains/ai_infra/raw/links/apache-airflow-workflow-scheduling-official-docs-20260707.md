---
type: RawSource
title: Apache Airflow Workflow Scheduling Documentation
source_kind: web
url: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html
secondary_urls:
  - https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html
  - https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/
captured: 2026-07-07
status: ingested
---
# Source

Official Apache Airflow DAG documentation: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html

Official Apache Airflow task documentation: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html

Official Apache Airflow authoring and scheduling documentation: https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/

Captured as a concise source note for `ai_infra` workflow scheduling coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Airflow represents a workflow as a DAG: a collection of tasks with explicit dependencies and scheduling metadata.
- Airflow tasks are executable units inside a DAG and can be produced by operators, sensors, or TaskFlow-decorated Python functions.
- Airflow DAG runs are concrete executions of a DAG for a logical date or trigger.
- The Airflow scheduler creates scheduled DAG runs and queues tasks when their dependencies and run conditions are satisfied.
- Airflow task instances have states, retry behavior, and dependency checks that matter to pipeline operations.
- Airflow scheduling belongs to the workflow-control layer; it does not itself define vector-index semantics, table-format retention, or RAG quality policy.

# Use In Wiki

Use this source note for workflow orchestration claims about DAGs, tasks, DAG runs, scheduler-created runs, task dependencies, task states, and retry boundaries. Use separate table-format, metadata-lineage, and RAG observability sources for storage lifecycle, provenance, and retrieval quality.
