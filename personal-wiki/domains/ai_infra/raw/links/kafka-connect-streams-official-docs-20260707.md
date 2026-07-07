---
type: RawSource
title: Apache Kafka Connect And Streams Documentation
source_kind: web
url: https://kafka.apache.org/documentation/
secondary_urls:
  - https://kafka.apache.org/documentation/streams/
  - https://kafka.apache.org/43/documentation.html#connect
captured: 2026-07-07
status: ingested
---
# Source

Official Apache Kafka documentation: https://kafka.apache.org/documentation/

Official Kafka Streams documentation: https://kafka.apache.org/documentation/streams/

Kafka Connect section in Apache Kafka documentation: https://kafka.apache.org/43/documentation.html#connect

Captured as a concise source note for `ai_infra` streaming ingestion and stream-processing coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Kafka Connect is Kafka's integration framework for moving data between Kafka and external systems through source and sink connectors.
- A source connector imports data from an external system into Kafka topics; a sink connector exports Kafka topic data to an external system.
- Kafka Connect separates connector definitions from tasks and workers, so connector work can be distributed across worker processes.
- Kafka Connect distributed mode uses Kafka-backed storage for connector configuration, offsets, and status, which gives connector workers a cluster-level coordination boundary.
- Kafka Streams is a client library for building applications and microservices whose input and output data are stored in Kafka topics.
- Kafka Streams applications are modeled as processor topologies over streams and tables, with state stores used when processing needs local state.
- Kafka Streams state can be backed by Kafka changelog topics, making stream processors recoverable after task or process failure.

# Use In Wiki

Use this source note for direct Kafka-style ingestion and processing claims: source/sink connector boundaries, connector workers and tasks, Kafka-backed offset/status/config coordination, processor topologies, stream/table processing, local state stores, and changelog-backed recovery. Do not use it to claim complete RAG governance, embedding drift detection, or table-format retention behavior.
