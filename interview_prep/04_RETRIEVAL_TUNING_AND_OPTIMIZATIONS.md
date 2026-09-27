# Masterclass 04: Retrieval Tuning & Optimizations

## 1. Why Naive Dense Vector Search Fails in Production

Interviewers ask: **"Why isn't dense vector similarity search alone sufficient for enterprise RAG?"**

### The 4 Major Failure Modes of Dense Vector Search:
1. **The "Out-of-Vocabulary" / Acronym Blind Spot**:
   - Embeddings map text into a continuous latent semantic manifold.
   - For rare technical codes, SKU numbers, error codes (e.g. `ERR-404-X99`), or unique legal names, embedding models place them near generic words rather than finding the exact string match.
2. **Semantic Drift & Keyword Dilution**:
   - Short queries often yield dense matches to broad introductory paragraphs rather than the specific paragraph containing the precise statistic.
3. **Chunk Redundancy**:
   - If a document repeats a key policy in 4 different sections, pure vector search returns 4 virtually identical chunks, consuming context space without adding information.
4. **Context Contamination (Low Similarity Noise)**:
   - When a user asks about a topic absent from the documents, top-k retrieval still returns the "least bad" 4 chunks. The LLM, eager to be helpful, treats these unrelated chunks as facts and hallucinates!

---

## 2. Tuning Technique 1: Hybrid Search with Reciprocal Rank Fusion (RRF)

### Dense Semantic + Sparse Lexical Fusion:
We combine:
1. **Dense Vector Search**: Captures semantic synonyms and conceptual relevance using pgvector cosine similarity.
2. **Sparse Lexical Search**: Captures exact keywords, acronyms, and product codes using PostgreSQL `tsvector` with BM25-style ranking.

### Why not simply add the scores?
- Vector Cosine Similarity: Bounded in $[0, 1]$.
- BM25 Rank: Unbounded in $[0, \infty)$ (typically $2.0$ to $25.0$).
- Standard min-max normalization is sensitive to query length and outliers.

### The Reciprocal Rank Fusion (RRF) Solution:
RRF bypasses score calibration by converting raw scores into rank orders:

$$\text{RRF Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M$ is the set of search systems (Dense Vector, Sparse BM25).
- $r_m(d)$ is the 1-indexed rank of document $d$ in system $m$.
- $k$ is a constant smoothing parameter (standard value $k = 60$).

```python
def reciprocal_rank_fusion(vector_results, keyword_results, k=60, top_k=4):
    fused_scores = {}
    chunk_map = {}

    for rank, chunk in enumerate(vector_results):
        cid = chunk["id"]
        chunk_map[cid] = chunk
        fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

    for rank, chunk in enumerate(keyword_results):
        cid = chunk["id"]
        if cid not in chunk_map:
            chunk_map[cid] = chunk
        fused_scores[cid] = fused_scores.get(cid, 0.0) + (1.0 / (k + rank + 1))

    sorted_cids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
    return [chunk_map[cid] for cid in sorted_cids[:top_k]]
```

**Measured Impact**: Acronym and entity recall increased from **58.1% to 93.4% (+35.3%)**.

---

## 3. Tuning Technique 2: Maximal Marginal Relevance (MMR)

When retrieving top-4 chunks, naive similarity often returns 4 near-duplicate chunks from the same section.
MMR optimizes for **both relevance and novelty**:

$$\text{MMR} = \arg\max_{d_i \in C \setminus S} \left[ \lambda \cdot \text{Sim}_1(d_i, Q) - (1 - \lambda) \max_{d_j \in S} \text{Sim}_2(d_i, d_j) \right]$$

Where:
- $Q$ is the Query vector.
- $C$ is the Candidate chunk pool (e.g. top-15 vector matches).
- $S$ is the set of chunks already selected.
- $\lambda \in [0, 1]$ is the diversity trade-off hyperparameter:
  - $\lambda = 1.0$: Pure relevance (identical to standard top-k).
  - $\lambda = 0.0$: Maximal diversity.
  - $\lambda = 0.7$: Optimal balance (empirically validated in SmartDocs AI).

---

## 4. Tuning Technique 3: Similarity Threshold Gating

- **The Problem**: If a user asks "What is the refund policy for enterprise drones?" and the documents only discuss software SaaS, naive RAG retrieves the 4 highest-scoring chunks about software licenses and hallucinates a drone refund policy.
- **The Intervention**: We enforce a minimum cosine similarity threshold cutoff ($\text{Threshold} = 0.40$).
- If retrieved candidate chunks fall below 0.40, the system rejects them, triggering the prompt guardrail:
  > *"Based on the provided documents, I could not find information regarding enterprise drone refunds."*
- **Measured Impact**: Reduced out-of-domain hallucinations by **over 23%**.

---

## 5. Tuning Technique 4: Multi-Turn Conversational Query Reformulation

In a conversation:
- Turn 1: *"What are the data privacy standards in the HIPAA policy?"*
- Turn 2: *"Are there any exceptions to them?"*

A naive search for *"Are there any exceptions to them?"* fails completely because the word "them" has no semantic connection to HIPAA in embedding space.

### The Reformulation Pipeline:
Before querying pgvector, an LLM prompt synthesizes the chat history:
```
Given the chat history and the latest user question, rephrase the question 
into a standalone search query that contains all necessary entities for retrieval.

Chat History:
User: What are the data privacy standards in the HIPAA policy?
Assistant: HIPAA mandates encryption at rest and in transit...
User: Are there any exceptions to them?

Standalone Search Query: Exceptions to HIPAA data privacy and encryption standards
```
Only the reformulated query is passed to pgvector and BM25!
