---
type: RawSource
title: FAISS README And Indexes Wiki
source_kind: web
url: https://github.com/facebookresearch/faiss
secondary_urls:
  - https://github.com/facebookresearch/faiss/wiki/Faiss-indexes
captured: 2026-07-07
status: ingested
---
# Source

Official FAISS GitHub repository README: https://github.com/facebookresearch/faiss

Official FAISS indexes wiki: https://github.com/facebookresearch/faiss/wiki/Faiss-indexes

Captured as a concise source note for `ai_infra` data/RAG/vector infrastructure coverage. The full external pages were not mirrored; the durable facts below are paraphrased from the official sources.

# Captured Facts

- FAISS describes itself as a library for efficient similarity search and clustering of dense vectors.
- The README says FAISS contains algorithms that search vector sets of any size, including sets that may not fit in RAM, and includes supporting code for evaluation and parameter tuning.
- FAISS is implemented primarily in C++ with Python wrappers; some useful algorithms are implemented on GPU.
- FAISS compares vectors with L2 distance or dot product and supports cosine similarity by normalizing vectors before dot-product search.
- The README frames FAISS indexes as tradeoffs across search time, search quality, memory per vector, training time, adding time, and need for external data for unsupervised training.
- Some FAISS methods use compressed vector representations and can scale to billions of vectors in main memory on a single server at the cost of less precise search.
- The indexes wiki lists representative index families including exact flat indexes (`IndexFlatL2`, `IndexFlatIP`), HNSW (`IndexHNSWFlat`), inverted-file indexes (`IndexIVFFlat`), scalar quantization, product quantization (`IndexPQ`), and IVF plus product quantization (`IndexIVFPQ`, `IndexIVFPQR`).
- Flat indexes store fixed-size vector codes and compare all indexed vectors to query vectors at search time.
- IVF methods partition the feature space into cells/lists and compare a query with only selected inverted lists, creating a speed/accuracy tradeoff controlled by list and probe choices.
- Product-quantization indexes split vectors into subvectors and quantize each subvector, reducing representation size while changing precision and search behavior.

# Use In Wiki

Use this source note for library-level vector search claims about FAISS dense-vector similarity search, index-family tradeoffs, flat/HNSW/IVF/PQ indexes, compression, CPU/GPU implementation, and scale-oriented search design.
