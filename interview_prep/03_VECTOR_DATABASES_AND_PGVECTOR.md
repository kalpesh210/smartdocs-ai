# Masterclass 03: Vector Databases & pgvector Internals

## 1. Why PostgreSQL + pgvector? The Architectural Trade-offs

Interview Question: **"Why did you use pgvector instead of a dedicated vector database like Pinecone, Milvus, or Qdrant?"**

### The Comparison Matrix:

| Feature | PostgreSQL + pgvector | Pinecone (Managed) | Milvus / Qdrant (Dedicated) |
| :--- | :--- | :--- | :--- |
| **Data Architecture** | Unified Relational + Vector | Vector-first (Metadata is secondary) | Vector-first + Hybrid search |
| **ACID Guarantees** | Full ACID (Transactions, Foreign Keys) | Eventual Consistency | Eventual Consistency |
| **Multi-Table Joins** | Native SQL joins across users, chats, docs | Impossible (Requires external DB sync) | Complex or impossible |
| **Hybrid Search** | Native `tsvector` + vector in 1 query | Vector search + sparse keyword vectors | Built-in BM25 support |
| **Hosting & Cost** | Self-hosted or AWS RDS / Supabase | Expensive SaaS consumption pricing | Self-hosted cluster or cloud |
| **Operational Overhead** | Low (Single existing DB engine) | Very Low (Fully managed) | High (Separate cluster to manage) |

### The "Dual-Database" Nightmare in Production:
If you use a dedicated vector database alongside a relational database:
1. **Synchronization Race Conditions**: When a user deletes a document in Postgres, you must asynchronously issue a delete to Pinecone. If the worker fails, ghost vectors remain searchable.
2. **Metadata Filtering Overhead**: Filtering by user permissions (`WHERE user_id = 42`) in pure vector DBs requires post-filtering (wasteful scans) or pre-filtering (index fragmentation).
3. **Data Redundancy**: Document text and metadata are duplicated across both systems.

**Key Interview Takeaway**: *For datasets under 10–20 million vectors, PostgreSQL with `pgvector` offers unbeatable operational simplicity, transactional consistency, and cost efficiency.*

---

## 2. Indexing Algorithms: HNSW vs IVFFlat

### 1. HNSW (Hierarchical Navigable Small World) — *Used in SmartDocs AI*
- **Structure**: Multi-layer skip-list graph. Top layers contain sparse links for long-range navigation; bottom layer contains all vectors connected to their nearest neighbors.
- **Search Complexity**: $O(\log N)$.
- **Recall**: Extremely high (>98% recall).
- **Build Time & Memory**: Higher memory usage (stores graph neighbor links), but supports incremental vector insertions without rebuilding the index!

#### SQL DDL for HNSW in pgvector:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table
CREATE TABLE document_chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536)
);

-- Create HNSW Index with Cosine Distance
CREATE INDEX idx_chunks_embedding_hnsw 
ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Parameters Explained**:
- `m = 16`: Max number of bidirectional links per vector node (higher = better recall, higher memory).
- `ef_construction = 64`: Size of the dynamic candidate list during graph construction (higher = better index quality, slower insert).
- `hnsw.ef_search = 40`: Runtime query parameter. Controls the candidate queue during search.

---

### 2. IVFFlat (Inverted File Flat)
- **Structure**: Partitions the vector space into $K$ Voronoi centroids using K-means clustering. At query time, only the vectors within the closest centroids are scanned.
- **Limitation**:
  - Requires training data to define centroids. If you index an empty table, the index is useless!
  - Does not adapt well to data drift (must periodically `REINDEX`).
  - Lower recall than HNSW under high concurrency.

---

## 3. pgvector Distance Operators

| Operator | Metric | Mathematical Formula | Optimal Index Operator Class |
| :--- | :--- | :--- | :--- |
| `<=>` | **Cosine Distance** | $1 - \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$ | `vector_cosine_ops` |
| `<->` | **Euclidean (L2) Distance** | $\sqrt{\sum (u_i - v_i)^2}$ | `vector_l2_ops` |
| `<#>` | **Negative Inner Product** | $-(\mathbf{u} \cdot \mathbf{v})$ | `vector_ip_ops` |

> [!TIP]
> Why does `<#>` return negative inner product? PostgreSQL indexes sort in ascending order (`ASC`), so returning the negative value orders the highest inner product (most similar) first!
