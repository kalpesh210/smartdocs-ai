# Masterclass 02: RAG Deep Dive & Architecture

## 1. Evolution of RAG Paradigms

| Paradigm | Architecture Characteristics | Limitations |
| :--- | :--- | :--- |
| **Naive RAG** | Standard linear flow: Chunk text -> Embed -> Store in Vector DB -> Retrieve Top-K by Cosine Similarity -> Concatenate into LLM prompt. | Low precision, chunk fragmentation, redundant top-k chunks, poor on exact entity matches, severe hallucination when low-relevance chunks pass. |
| **Advanced RAG** *(SmartDocs AI)* | Adds pre-retrieval (query reformulation, hybrid indexing) and post-retrieval (Reciprocal Rank Fusion, MMR re-ranking, threshold filtering, citation grounding). | Requires hyperparameter tuning (k, $\lambda$, threshold), slightly higher orchestration complexity. |
| **Modular RAG** | Dynamic routing agents, self-reflective loops (Self-RAG, Corrective RAG), iterative retrieval, external web fallback. | High latency, multi-agent cost overhead. |

---

## 2. Ingestion & PDF Parsing Challenges in Production

Interviewers love asking: **"Why is PDF parsing so notoriously difficult in AI pipelines?"**

### The Core Challenges:
1. **Visual Stream vs Text Stream**: PDFs store text as geometric printing instructions (e.g. `BT /F1 12 Tf 72 712 Td (Hello) Tj ET`). They do not store reading order, paragraph structure, or table semantics.
2. **Two-Column / Multi-Column Layouts**: Naive text extraction reads left-to-right across the entire page width, interleaving sentences from Column 1 with Column 2 into unintelligible gibberish.
3. **Headers, Footers, and Page Numbers**: Repeating headers and footers (e.g., "Confidential - Page 12 of 100") get embedded into every chunk, introducing spurious vector matches.
4. **Scanned Documents (Images)**: Documents without embedded font streams require Optical Character Recognition (OCR) using Tesseract or AWS Textract.

### How SmartDocs AI Solves This:
- Extracts text page-by-page preserving structural page provenance (`page_number`).
- Sanitizes null bytes, control sequences, and multiple whitespaces while maintaining paragraph breaks.
- Retains start/end character offsets for document chunk traceability.

---

## 3. Text Chunking Strategies: Deep Comparative Analysis

Chunking is the single most impactful hyperparameter in retrieval performance.

```
Full Document Text
   │
   ├─► Fixed-Length Splitter ──────► [Can cut sentences in half, e.g. "The profit was $10" / "0 million"]
   │
   ├─► Sentence Splitter ──────────► [Chunks vary wildly in length; single sentences lack broader context]
   │
   └─► Recursive Character Splitter ► [SmartDocs AI: Hierarchical boundary splitting preserving semantics]
```

### Chunking Strategies Breakdown:
1. **Fixed-Size Chunking (Character or Token based)**:
   - *How it works*: Slices text strictly every $N$ characters (e.g., 500 chars).
   - *Downside*: Cuts words in half or bifurcates critical numerical values across chunks.

2. **Recursive Character Text Splitting (Implemented in SmartDocs AI)**:
   - *How it works*: Attempts to split by a list of separators hierarchically:
     `["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]`
   - *Benefit*: Keeps paragraphs and full sentences intact. Only splits down to words if an individual paragraph exceeds the chunk limit.

3. **Semantic / Embedding-Based Chunking**:
   - *How it works*: Computes cosine similarity between consecutive sentence embeddings; splits when similarity drops below a threshold (indicating a topic shift).
   - *Downside*: Requires $O(N)$ embedding calls during ingestion, increasing pipeline latency and cost.

### The Math Behind Chunk Size (500 chars) and Overlap (80 chars):
- **Why not 2000 characters?**
  - High token counts dilute vector specificity. A 2000-character chunk covering 5 different topics creates an "average" embedding that matches everything poorly.
- **Why not 100 characters?**
  - Fails to capture sufficient contextual relationships (the "needle" has no surrounding context for the LLM to synthesize).
- **The Golden Ratio**: ~400–600 characters (~100–150 tokens) with 15–20% overlap.
- **Overlap Formula**:
  $$\text{Effective Context Coverage} = \text{Chunk Size} - \text{Overlap}$$
  With $\text{Chunk Size} = 500$ and $\text{Overlap} = 80$, the effective step size is $420$ characters, guaranteeing that phrases spanning chunk boundaries appear in full in at least one chunk.

---

## 4. Embedding Space Geometry & Normalization

### Cosine Distance vs Dot Product vs Euclidean (L2) Distance:
- **Cosine Similarity**:
  $$\text{Sim}_{\cos}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \frac{\sum u_i v_i}{\sqrt{\sum u_i^2} \sqrt{\sum v_i^2}}$$
- **L2-Normalized Vectors**:
  If we normalize all vectors such that $\|\mathbf{u}\|_2 = 1$ and $\|\mathbf{v}\|_2 = 1$:
  $$\text{Sim}_{\cos}(\mathbf{u}, \mathbf{v}) = \mathbf{u} \cdot \mathbf{v}$$
- **Why this matters for Interviewers**:
  When vectors are unit-normalized upon insertion into PostgreSQL `pgvector`, cosine similarity reduces to a pure hardware dot product. This eliminates floating-point square root operations, resulting in a **3x–5x speedup** on vector index scans!

---

## 5. The "Lost in the Middle" Phenomenon

Research paper: *Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (Stanford / UC Berkeley, 2023)*.

- **Observation**: Performance of LLMs is highest when relevant information is at the very beginning (Primacy bias) or very end (Recency bias) of the input context. Performance drops by up to 30% when key facts are placed in the middle third of the context.
- **Mitigation in SmartDocs AI**:
  1. We limit `Top-K` to 4 focused chunks rather than stuffing 20 chunks into prompt memory.
  2. We apply MMR re-ranking so every chunk in the prompt contains non-overlapping, high-density signal.
  3. The most relevant chunk is positioned at the top of the context block.
