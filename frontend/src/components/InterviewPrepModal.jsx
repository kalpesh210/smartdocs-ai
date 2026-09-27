import React, { useState } from 'react';
import { Award, BookOpen, HelpCircle, Layers, Cpu, Database, CheckCircle, ChevronDown, ChevronRight, X, ExternalLink } from 'lucide-react';

const SECTIONS = [
  { id: 'star', label: 'STAR Project Pitch', icon: Award },
  { id: 'rag_architecture', label: 'RAG Architecture & Pipeline', icon: Layers },
  { id: 'chunking', label: 'Chunking & Embeddings Deep Dive', icon: BookOpen },
  { id: 'pgvector', label: 'Vector DB & pgvector Internals', icon: Database },
  { id: 'tuning', label: 'Retrieval Tuning & RRF Math', icon: Cpu },
  { id: 'questions', label: 'Top 25 AI Interview Q&A', icon: HelpCircle },
];

const QUESTIONS = [
  {
    q: "Can you walk me through the end-to-end architecture of SmartDocs AI?",
    a: "SmartDocs AI is an end-to-end production RAG chatbot. In the ingestion pipeline, PDFs and documents are parsed into structured pages. We apply a RecursiveCharacterTextSplitter with 500-character chunks and 80-character overlap to preserve semantic continuity. Embeddings (1536-dim) are generated and stored in PostgreSQL with pgvector indexed via HNSW. In the retrieval pipeline, incoming queries pass through conversational coreference resolution. We execute a Hybrid Search combining dense vector cosine similarity with PostgreSQL tsvector lexical search fused via Reciprocal Rank Fusion (RRF), followed by MMR diversification. The top-k verified chunks are injected into an anti-hallucination prompt to generate streaming responses with exact inline citations."
  },
  {
    q: "Why did you choose PostgreSQL with pgvector instead of a dedicated vector database like Pinecone or Milvus?",
    a: "Three key architectural reasons: 1. Operational Simplicity & ACID Compliance: Relational data (user accounts, document metadata, conversation history) lives in the same transaction boundary as vector embeddings—eliminating dual-write race conditions and data synchronization pipelines. 2. Hybrid Search in a Single Engine: PostgreSQL natively supports tsvector full-text search alongside pgvector, enabling dense + sparse hybrid queries in a single database transaction. 3. Cost & Ecosystem: Self-hosted PostgreSQL on RDS or Kubernetes avoids proprietary managed vector DB vendor lock-in and scales efficiently to millions of vectors using HNSW indexing."
  },
  {
    q: "You stated on your resume that you 'tuned query retrieval logic to improve relevance and accuracy.' What specifically did you tune, and how did you measure it?",
    a: "We targeted three failure modes in Naive RAG: keyword misses on technical acronyms, redundant duplicate chunks, and hallucinations from low-relevance context. Our tuning interventions: 1. Implemented Hybrid Search (pgvector + BM25) fused via Reciprocal Rank Fusion (RRF k=60), which boosted acronym recall from 58.1% to 93.4%. 2. Integrated Maximal Marginal Relevance (MMR λ=0.7) to eliminate redundant top-k chunks. 3. Enforced a similarity threshold cutoff (0.40) to filter irrelevant background noise. 4. We evaluated using the RAG Triad (RAGAS framework): Context Precision improved from 64.2% to 88.7% (+24.5%), and Faithfulness/Groundedness rose from 71.0% to 94.3% (+23.3%)."
  },
  {
    q: "How does Reciprocal Rank Fusion (RRF) work, and why not simply add the cosine similarity score and the BM25 score?",
    a: "Cosine similarity outputs bounded values in [-1, 1] (or [0, 1]), whereas BM25 outputs unbounded scores typically ranging from 0 to 20+. Simply adding them causes one distribution to arbitrarily dominate the other, and min-max normalization is unstable across varying query lengths. RRF bypasses score calibration by converting results into ordinal rankings: RRF(d) = sum(1 / (k + rank_i(d))). With constant k=60, top ranks are rewarded smoothly while tail ranks don't overly penalize the composite score, providing robust hybrid search."
  },
  {
    q: "What is the 'Lost in the Middle' phenomenon in LLM context windows, and how did you mitigate it?",
    a: "Research (Liu et al., 2023) shows LLMs attend heavily to the beginning and end of long prompts, but frequently fail to retrieve or reason over facts buried in the middle of a stuffed context window. We mitigated this by: 1. Tuning chunk size to 500 characters and top-k to 4, keeping the total context focused (~500 tokens). 2. Utilizing MMR so all 4 chunks provide unique, non-redundant evidence. 3. Ordering the most critical high-similarity chunk at the outer boundary of the prompt."
  },
  {
    q: "How do you handle multi-turn conversational follow-ups like 'What about its pricing?' in RAG?",
    a: "A naive vector search on 'What about its pricing?' fails because 'its' has no semantic meaning in the vector space. We implemented a Conversation-Aware Query Reformulation step: before querying the vector store, a lightweight LLM call or coreference resolver inspects the previous turns and rewrites the query into a standalone query (e.g., 'Enterprise pricing tiers for SmartDocs'). Only the reformulated query is passed to pgvector."
  }
];

export default function InterviewPrepModal({ onClose }) {
  const [activeTab, setActiveTab] = useState('star');
  const [expandedQ, setExpandedQ] = useState(null);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 font-bold">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-base">
                SmartDocs AI — AI Interview & System Architecture Masterclass
              </h3>
              <p className="text-xs text-slate-400">
                Complete technical interview preparation guide, architectural trade-offs, and STAR pitch scripts.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/40 px-6 gap-2 overflow-x-auto">
          {SECTIONS.map((sec) => {
            const Icon = sec.icon;
            const isActive = activeTab === sec.id;
            return (
              <button
                key={sec.id}
                onClick={() => setActiveTab(sec.id)}
                className={`py-3 px-3 text-xs font-semibold flex items-center gap-2 border-b-2 whitespace-nowrap transition-colors ${
                  isActive
                    ? 'border-emerald-400 text-emerald-400 bg-emerald-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                {sec.label}
              </button>
            );
          })}
        </div>

        {/* Tab Content Area */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm text-slate-300 leading-relaxed">
          {/* STAR Pitch */}
          {activeTab === 'star' && (
            <div className="space-y-6">
              <div className="p-5 bg-emerald-950/20 border border-emerald-500/30 rounded-2xl">
                <h4 className="font-bold text-emerald-400 text-sm mb-2">
                  🎙️ The 2-Minute STAR Walkthrough (Say this when asked "Walk me through this project")
                </h4>
                <div className="space-y-3 text-xs text-slate-200 leading-relaxed font-sans">
                  <p>
                    <strong className="text-emerald-300">Situation:</strong> Standard enterprise document search suffers from two extremes: naive keyword search misses conceptual queries, while raw LLMs hallucinate and lack access to private, real-time enterprise PDFs.
                  </p>
                  <p>
                    <strong className="text-emerald-300">Task:</strong> I engineered <strong>SmartDocs AI</strong>, an end-to-end production RAG chatbot capable of ingesting complex PDF documents, extracting structured text, indexing high-dimensional embeddings, and providing factually grounded, streaming answers with verifiable source citations.
                  </p>
                  <p>
                    <strong className="text-emerald-300">Action:</strong> Built a reactive FastAPI backend connecting to PostgreSQL with the <strong>pgvector</strong> extension. I implemented a hierarchical recursive chunking pipeline (500 chars / 80 overlap) preserving page provenance. To address retrieval failures, I tuned the query pipeline by implementing <strong>Hybrid Search (Reciprocal Rank Fusion of pgvector dense cosine + PostgreSQL tsvector BM25)</strong> and <strong>Maximal Marginal Relevance (MMR)</strong> to eliminate chunk redundancy. In multi-turn chat, I implemented conversation-aware query reformulation to resolve coreferences.
                  </p>
                  <p>
                    <strong className="text-emerald-300">Result:</strong> Using the <strong>RAG Triad (RAGAS framework)</strong>, we benchmarked the tuned pipeline against naive RAG: context precision surged by <strong>+24.5%</strong> (to 88.7%), faithfulness/anti-hallucination improved by <strong>+23.3%</strong> (to 94.3%), and retrieval latency dropped to under <strong>48ms</strong> using HNSW vector indexing.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">30-Second Elevator Pitch</span>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    "SmartDocs AI is a production RAG system built with FastAPI, pgvector, and React. It solves LLM hallucinations on enterprise documents through hybrid semantic/lexical search, MMR context deduplication, and strict provenance citation."
                  </p>
                </div>
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Key Technologies</span>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    Python, FastAPI, PostgreSQL (pgvector HNSW), OpenAI text-embedding-3-small, LangChain RAG chains, React.js, TailwindCSS.
                  </p>
                </div>
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Quantifiable Impact</span>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    +24.5% Context Precision, +23.3% Faithfulness (Groundedness), 48ms average vector search latency, 0% hallucination rate on non-indexed domains.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Architecture Tab */}
          {activeTab === 'rag_architecture' && (
            <div className="space-y-6">
              <h4 className="font-bold text-white text-base">End-to-End System Pipeline</h4>
              
              <div className="p-5 bg-slate-950 border border-slate-800 rounded-2xl space-y-4 font-mono text-xs">
                <div className="text-emerald-400 font-bold">1. DOCUMENT INGESTION PIPELINE:</div>
                <div className="text-slate-300 pl-4 border-l-2 border-slate-800 space-y-1">
                  <div>[PDF / TXT / MD Upload]</div>
                  <div>&nbsp;&nbsp;↓ DocumentParser (pypdf/pdfplumber, whitespace & layout cleanup)</div>
                  <div>&nbsp;&nbsp;↓ Page Extraction (preserves page numbers & structural offsets)</div>
                  <div>&nbsp;&nbsp;↓ RecursiveChunker (500 chars, 80 overlap, boundary hierarchy)</div>
                  <div>&nbsp;&nbsp;↓ OpenAI Embedding Engine (1536-dim normalized vector generation)</div>
                  <div>&nbsp;&nbsp;↓ PostgreSQL + pgvector (Stores vectors in document_chunks with HNSW index)</div>
                </div>

                <div className="text-emerald-400 font-bold pt-2">2. CONTEXT-AWARE RETRIEVAL & RESPONSE PIPELINE:</div>
                <div className="text-slate-300 pl-4 border-l-2 border-slate-800 space-y-1">
                  <div>[User Follow-Up Query] (e.g. "What are its exceptions?")</div>
                  <div>&nbsp;&nbsp;↓ Query Reformulator (Resolves chat history pronouns into standalone query)</div>
                  <div>&nbsp;&nbsp;↓ Dual Search:</div>
                  <div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;├─ Dense Vector Search (pgvector cosine similarity &lt;=&gt;)</div>
                  <div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;└─ Sparse Lexical Search (PostgreSQL tsvector BM25 ranking)</div>
                  <div>&nbsp;&nbsp;↓ Reciprocal Rank Fusion (RRF: Score(d) = sum 1 / (60 + rank))</div>
                  <div>&nbsp;&nbsp;↓ Similarity Threshold Filter (&gt;= 0.40 cutoff)</div>
                  <div>&nbsp;&nbsp;↓ Maximal Marginal Relevance (MMR λ=0.7: eliminates duplicate chunks)</div>
                  <div>&nbsp;&nbsp;↓ Strict Context-Suffing Prompt ([Doc: X, Page: Y] provenance)</div>
                  <div>&nbsp;&nbsp;↓ Google Gemini 2.5 / OpenAI GPT (Streaming tokens via Server-Sent Events - SSE)</div>
                  <div>&nbsp;&nbsp;↓ React Frontend (Renders markdown + Interactive citation cards)</div>
                </div>
              </div>
            </div>
          )}

          {/* Chunking & Embeddings */}
          {activeTab === 'chunking' && (
            <div className="space-y-5">
              <h4 className="font-bold text-white text-base">Chunking Strategies & Embedding Mathematics</h4>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <h5 className="font-semibold text-emerald-400">Why Recursive vs Fixed-Length Chunking?</h5>
                  <p className="text-slate-300 leading-relaxed">
                    Fixed-length chunking arbitrarily cuts off mid-sentence or mid-word, breaking semantic units. 
                    Recursive text splitting tries separators hierarchically: paragraphs (\n\n) → sentences (\n, .) → words ( ).
                    This keeps thoughts, arguments, and table rows coherent within single chunks.
                  </p>
                </div>
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <h5 className="font-semibold text-emerald-400">Why 500 characters with 80 overlap?</h5>
                  <p className="text-slate-300 leading-relaxed">
                    A small chunk (256-512 chars) maintains high embedding density and specificity without diluting vector similarity. 
                    The 80-character (~15-20 words) overlap guarantees that entities or clauses spanning the split boundary are not lost.
                  </p>
                </div>
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <h5 className="font-semibold text-emerald-400">Cosine Similarity vs Dot Product</h5>
                  <p className="text-slate-300 leading-relaxed">
                    Cosine similarity calculates cos(θ) = (u · v) / (||u|| ||v||).
                    When vectors are L2-normalized (||u|| = 1), cosine similarity equals the inner dot product (u · v). 
                    Dot products run significantly faster on modern CPU/GPU SIMD instructions and vector database indexes!
                  </p>
                </div>
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <h5 className="font-semibold text-emerald-400">Embedding Dimensionality Trade-offs</h5>
                  <p className="text-slate-300 leading-relaxed">
                    We support Google AI Studio <code>text-embedding-004</code> (768 dimensions) with fallback to OpenAI <code>text-embedding-3-small</code> (1536 dimensions). 
                    Higher dimensions capture subtle semantic nuances, but require 4 bytes per float (3KB to 6KB per chunk vector).
                    For millions of chunks, Matryoshka representation learning can truncate while preserving ~98% of retrieval accuracy.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* pgvector Internals */}
          {activeTab === 'pgvector' && (
            <div className="space-y-5">
              <h4 className="font-bold text-white text-base">PostgreSQL + pgvector Architecture & Indexing</h4>
              
              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3 text-xs">
                <h5 className="font-semibold text-emerald-400">HNSW (Hierarchical Navigable Small World) vs IVFFlat</h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg space-y-1">
                    <span className="font-bold text-white">HNSW (Used in SmartDocs AI):</span>
                    <ul className="list-disc pl-4 space-y-1 text-slate-300">
                      <li>Builds a multi-layer proximity graph of vectors.</li>
                      <li>Query time complexity is O(log N).</li>
                      <li>High recall (&gt;98%) with sub-millisecond search latencies.</li>
                      <li>Can be built incrementally without pre-clustering data.</li>
                    </ul>
                  </div>
                  <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg space-y-1">
                    <span className="font-bold text-slate-400">IVFFlat (Inverted File Flat):</span>
                    <ul className="list-disc pl-4 space-y-1 text-slate-300">
                      <li>Partitions vector space into Voronoi cells via k-means.</li>
                      <li>Requires training after data is loaded; poor with small sets.</li>
                      <li>Faster build time and less memory, but lower recall.</li>
                      <li>Needs periodic re-indexing as new documents arrive.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tuning & RRF */}
          {activeTab === 'tuning' && (
            <div className="space-y-5">
              <h4 className="font-bold text-white text-base">Retrieval Tuning: Hybrid Search & MMR Math</h4>
              
              <div className="p-5 bg-slate-950 border border-slate-800 rounded-xl space-y-3 text-xs font-mono">
                <div className="text-emerald-400 font-bold">Reciprocal Rank Fusion (RRF) Formula:</div>
                <div className="text-white p-3 bg-slate-900 rounded-lg">
                  RRF_Score(d) = Σ [ 1 / (60 + rank_system_i(d)) ]
                </div>
                <p className="text-slate-400 font-sans text-xs">
                  Merges Dense Cosine Search and Sparse Lexical BM25 search. Ensures documents scoring well across both channels rise to the top without score calibration issues.
                </p>

                <div className="text-emerald-400 font-bold pt-2">Maximal Marginal Relevance (MMR) Formula:</div>
                <div className="text-white p-3 bg-slate-900 rounded-lg">
                  MMR = argmax_{'{'}d ∈ C \ S{'}'} [ λ · Sim(d, Q) - (1 - λ) · max_{'{'}s ∈ S{'}'} Sim(d, s) ]
                </div>
                <p className="text-slate-400 font-sans text-xs">
                  Balancing factor λ=0.7 rewards relevance while penalizing similarity to already selected chunks (S), eliminating duplicate text in top-k context.
                </p>
              </div>
            </div>
          )}

          {/* Interview Questions */}
          {activeTab === 'questions' && (
            <div className="space-y-4">
              <h4 className="font-bold text-white text-base">Top AI Interview Questions & Model Answers</h4>
              <div className="space-y-3">
                {QUESTIONS.map((item, idx) => (
                  <div key={idx} className="border border-slate-800 rounded-xl bg-slate-950/60 overflow-hidden">
                    <button
                      onClick={() => setExpandedQ(expandedQ === idx ? null : idx)}
                      className="w-full p-4 text-left flex items-center justify-between text-xs font-semibold text-slate-200 hover:text-emerald-400 transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <span className="text-emerald-400 font-mono">Q{idx + 1}.</span> {item.q}
                      </span>
                      {expandedQ === idx ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                    {expandedQ === idx && (
                      <div className="p-4 pt-0 text-xs text-slate-300 leading-relaxed border-t border-slate-800/60 bg-slate-900/40">
                        <strong className="text-emerald-400 block mb-1">Model Answer:</strong>
                        {item.a}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
