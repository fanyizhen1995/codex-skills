---
type: RawSource
title: RAG Access Policy PII And Evaluation Governance Official Sources
source_kind: web
url: https://learn.microsoft.com/en-us/azure/search/search-document-level-access-overview
secondary_urls:
  - https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search
  - https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-pii-detection
  - https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview
  - https://docs.weaviate.io/weaviate/configuration/rbac
  - https://docs.weaviate.io/weaviate/concepts/data
  - https://docs.datahub.com/docs/authorization/policies
  - https://langfuse.com/docs/evaluation/experiments/datasets
captured: 2026-07-07
status: ingested
---
# Source

Official Azure AI Search document-level access-control documentation: https://learn.microsoft.com/en-us/azure/search/search-document-level-access-overview

Official Azure AI Search security-filter documentation: https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search

Official Azure AI Search PII Detection skill documentation: https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-pii-detection

Official Azure Language PII overview: https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview

Official Weaviate RBAC documentation: https://docs.weaviate.io/weaviate/configuration/rbac

Official Weaviate data-structure documentation: https://docs.weaviate.io/weaviate/concepts/data

Official DataHub policies documentation: https://docs.datahub.com/docs/authorization/policies

Official Langfuse dataset documentation: https://langfuse.com/docs/evaluation/experiments/datasets

Captured as a concise source note for `ai_infra` RAG access policy, document-level authorization, PII redaction, catalog policy, and evaluation-dataset governance coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- Azure AI Search documents document-level access control for RAG, agentic systems, and enterprise search. It describes approaches based on security filters, POSIX-like ACL or RBAC scope metadata, Microsoft Purview sensitivity labels, and SharePoint ACLs.
- Azure AI Search query-time enforcement compares user or group claims from a Microsoft Entra token with permission metadata stored alongside indexed documents, then returns only documents whose synchronized metadata grants access.
- Azure AI Search explicitly distinguishes permission synchronization from query-time enforcement. Permission changes in source systems are reflected only after source-specific synchronization writes updated metadata into the index.
- Azure AI Search notes that chunked indexes produced through integrated vectorization or text splitting must project permission fields or sensitivity labels to each chunk row; without chunk projection, chunk-level references are not filtered.
- The Azure AI Search security-filter pattern stores user or group identifiers in a filterable field, keeps that field non-retrievable, and applies a query filter such as `search.in` to trim results for callers whose identifiers do not match.
- Azure AI Search PII Detection skill can extract personally identifiable information from input text and optionally mask it, with configurable confidence, masking mode, masking character, entity categories, and model version.
- Azure Language PII detection covers text, conversation, and document-based inputs, returning structured entity categories, confidence scores, and redacted output based on the API configuration.
- Weaviate RBAC controls access by authenticated user identity, roles, permissions, resource types, actions, and optional constraints. Data-object permissions include create, read, update, and delete access scoped by collection and tenant name filters.
- Weaviate multi-tenancy isolates each tenant's data on a dedicated shard; tenant state controls read/write availability, and deleting a tenant deletes the associated shard and objects.
- DataHub policies define who can do what to which resources. Metadata policies can target resource types, URNs, tags, domains, containers, glossary terms, and actors such as users, groups, or owners.
- DataHub view-based access-control guidance warns that policy design affects search/entity-page performance and recommends ownership or shallow domain patterns when restricting metadata visibility.
- Langfuse datasets are collections of inputs and expected outputs used for application evaluation. Dataset items can carry metadata and source trace links, can be created from production traces or observations, and support schema validation.
- Langfuse dataset versioning records item add/update/delete/archive operations over time. Experiments can run against a specific dataset version to reproduce or compare evaluation results after item changes.

# Use In Wiki

Use this source note for bounded RAG governance claims about document ACL propagation into retrieval indexes, query-time security trimming, chunk-level permission projection, PII redaction in indexing pipelines, vector-store RBAC and tenant scoping, metadata-catalog policies, and evaluation-dataset versioning. Do not use it to claim production enforcement correctness, legal compliance, or complete cache/vector/evaluation delete propagation without additional run, audit, or incident evidence.
