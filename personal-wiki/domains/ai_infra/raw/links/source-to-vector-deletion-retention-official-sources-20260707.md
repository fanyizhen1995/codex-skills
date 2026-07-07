---
type: RawSource
title: Source-To-Vector Deletion And Retention Official Sources
source_kind: web
url: https://milvus.io/docs/delete-entities.md
secondary_urls:
  - https://milvus.io/docs/set-collection-ttl.md
  - https://api.qdrant.tech/api-reference/points/delete-points
  - https://docs.weaviate.io/weaviate/manage-objects/delete
  - https://docs.weaviate.io/weaviate/concepts/data
  - https://learn.microsoft.com/en-us/azure/search/search-how-to-index-azure-blob-changed-deleted
captured: 2026-07-07
status: ingested
---
# Source

Official Milvus delete-entity documentation: https://milvus.io/docs/delete-entities.md

Official Milvus collection TTL documentation: https://milvus.io/docs/set-collection-ttl.md

Official Qdrant delete-points API reference: https://api.qdrant.tech/api-reference/points/delete-points

Official Weaviate delete-object documentation: https://docs.weaviate.io/weaviate/manage-objects/delete

Official Weaviate data-structure documentation: https://docs.weaviate.io/weaviate/concepts/data

Official Azure AI Search change/delete detection documentation: https://learn.microsoft.com/en-us/azure/search/search-how-to-index-azure-blob-changed-deleted

Captured as a concise source note for `ai_infra` source-to-vector deletion, vector-store deletion, TTL, and search-index deletion-detection coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Milvus documents deletion of entities by filter expression, primary key, and partition. The same page treats entities as records in a collection, so this is vector-store row/entity deletion evidence rather than upstream table delete propagation evidence.
- Milvus documents Time-to-Live retention at collection and entity levels. Expired entities stop appearing in search and query results immediately, then are physically removed during a later compaction cycle; the page describes compaction timing and configuration as part of the retention boundary.
- Qdrant documents a delete-points operation that can delete specified points from a collection by explicit point IDs or by a filter selector. The API response acknowledges an operation id, and optional query parameters include wait and ordering controls.
- Weaviate documents deletion of objects by object id, by filter criteria, and by multiple ids. For multi-tenant collections, the tenant name is part of the deletion context.
- Weaviate documents object TTL. Expired objects are automatically deleted at configured intervals, can be excluded from query results before deletion has physically run, and multi-tenant deletion is constrained by tenant activity state.
- Weaviate documents tenant isolation through shards and states. Deleting a tenant deletes the associated shard and all of its objects; inactive or offloaded tenants are not available for read or write access until activated.
- Azure AI Search indexers automatically detect changed Azure Storage content through object timestamps, but deletion detection requires a soft-delete strategy. Native blob soft delete or custom metadata can mark source content for deletion so a later indexer run removes the corresponding search document.
- Azure AI Search warns that deletion detection must be configured from the first indexer run. Documents deleted before the policy was established can remain in the index unless a new index/indexer path is used.
- Azure AI Search documents a two-step custom metadata deletion strategy: first flag source content, run the indexer so the search document is deleted, and only then physically delete the source file.
- Azure AI Search deletion detection does not cover one-to-many indexing scenarios; those require submitting a deletion request to the search index API.

# Use In Wiki

Use this source note for bounded claims about vector-store object deletion, collection/entity TTL, tenant-scoped vector data deletion, and search-index deletion detection. Do not use it to claim automatic end-to-end propagation from source tables into every embedding store, vector index, RAG cache, and evaluation dataset. That broader claim requires explicit pipeline wiring or incident/run evidence.
