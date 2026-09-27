import React, { useState } from 'react';
import { Sliders, Search, ArrowRight, Zap, Target, BarChart2, ShieldCheck, HelpCircle } from 'lucide-react';
import { api } from '../services/api';

export default function RetrievalTuner({ onSelectSource }) {
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState('compare_all');
  const [topK, setTopK] = useState(4);
  const [threshold, setThreshold] = useState(0.40);
  const [mmrLambda, setMmrLambda] = useState(0.70);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [benchmarks, setBenchmarks] = useState(null);

  const handleTest = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await api.testRetrieval({
        query,
        strategy,
        top_k: topK,
        similarity_threshold: threshold,
        mmr_lambda: mmrLambda,
      });
      setResults(data);
    } catch (err) {
      alert("Error testing retrieval: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadBenchmarks = async () => {
    try {
      const data = await api.getBenchmarks();
      setBenchmarks(data);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sliders className="w-5 h-5 text-emerald-400" />
            Retrieval Tuning & Experimentation Lab
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Empirically benchmark Dense Vector, BM25 Lexical, Hybrid (RRF), and MMR Diversity retrieval strategies.
          </p>
        </div>
        <button
          onClick={loadBenchmarks}
          className="px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold flex items-center gap-2 self-start"
        >
          <BarChart2 className="w-4 h-4" /> View Evaluation Benchmarks
        </button>
      </div>

      {/* Benchmark Drawer / Modal if loaded */}
      {benchmarks && (
        <div className="p-5 bg-slate-900/90 border border-emerald-500/40 rounded-2xl space-y-3 animate-fadeIn">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-emerald-400 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              {benchmarks.title} ({benchmarks.dataset_size})
            </h4>
            <button
              onClick={() => setBenchmarks(null)}
              className="text-xs text-slate-400 hover:text-white"
            >
              Dismiss
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase text-[10px] font-semibold">
                <tr>
                  <th className="p-2.5">Evaluation Metric</th>
                  <th className="p-2.5">Naive RAG (Baseline)</th>
                  <th className="p-2.5">SmartDocs Tuned</th>
                  <th className="p-2.5">Gain</th>
                  <th className="p-2.5">Tuning Intervention</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {benchmarks.comparison.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-800/40">
                    <td className="p-2.5 font-medium text-white">{row.metric}</td>
                    <td className="p-2.5 text-rose-400 font-mono">{row.naive_rag}</td>
                    <td className="p-2.5 text-emerald-400 font-mono font-semibold">{row.tuned_rag}</td>
                    <td className="p-2.5 text-emerald-300 font-semibold">{row.improvement}</td>
                    <td className="p-2.5 text-slate-400">{row.tuning_intervention}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Query & Controls Card */}
      <form onSubmit={handleTest} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Enter a test query (e.g., 'What are the performance metrics and indexing trade-offs?')"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-700/80 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-slate-950 font-semibold rounded-xl text-xs flex items-center gap-2 transition-colors shadow-lg shadow-emerald-950/40"
          >
            <Zap className="w-4 h-4" />
            {loading ? 'Executing Retrieval...' : 'Test Retrieval'}
          </button>
        </div>

        {/* Sliders Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5 pt-4 border-t border-slate-800/80">
          <div>
            <label className="text-xs text-slate-400 font-medium block mb-1">Strategy Mode</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full py-2 px-3 bg-slate-950 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="compare_all">⚡ Compare All Side-by-Side</option>
              <option value="hybrid">Hybrid Search (RRF: Dense + Sparse)</option>
              <option value="vector">Dense Vector Search (pgvector cosine)</option>
              <option value="keyword">Sparse Lexical Search (BM25)</option>
              <option value="mmr">Maximal Marginal Relevance (MMR)</option>
            </select>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Top-K Chunks:</span>
              <span className="text-emerald-400 font-mono font-medium">{topK}</span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500">Number of passages passed to LLM context</span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Similarity Threshold:</span>
              <span className="text-emerald-400 font-mono font-medium">{threshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="0.9"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500">Cutoff gate to prevent hallucination noise</span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">MMR Diversity ($\lambda$):</span>
              <span className="text-emerald-400 font-mono font-medium">{mmrLambda.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={mmrLambda}
              onChange={(e) => setMmrLambda(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500">1.0 = Pure relevance, 0.0 = Max diversity</span>
          </div>
        </div>
      </form>

      {/* Results View */}
      {results && results.mode === 'comparison' && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-300">
            Side-by-Side Comparison for: <span className="text-emerald-400">"{results.query}"</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Object.entries(results.results).map(([stratName, stratData]) => (
              <div key={stratName} className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 flex flex-col space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="font-bold text-xs uppercase text-emerald-400 font-mono">
                    {stratName}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {stratData.metadata.total_latency_ms}ms
                  </span>
                </div>

                <div className="text-[11px] text-slate-400">
                  Retrieved: <span className="text-white font-semibold">{stratData.chunks.length}</span> chunks
                </div>

                <div className="space-y-2.5 overflow-y-auto max-h-[400px]">
                  {stratData.chunks.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-500 italic">
                      No chunks satisfied similarity threshold ({threshold})
                    </div>
                  ) : (
                    stratData.chunks.map((c, i) => (
                      <div
                        key={i}
                        onClick={() => onSelectSource(c)}
                        className="p-3 bg-slate-950/70 hover:bg-slate-800/60 border border-slate-800/80 rounded-xl cursor-pointer transition-colors text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                          <span className="truncate max-w-[100px] text-slate-300">{c.document_filename}</span>
                          <span className="text-emerald-400">
                            {c.similarity !== undefined ? `${(c.similarity * 100).toFixed(0)}%` : `RRF ${c.rrf_score}`}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 line-clamp-3 leading-relaxed">
                          {c.content}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {results && results.mode !== 'comparison' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-white text-sm">
              Retrieved {results.results.chunks.length} Chunks using {results.strategy.toUpperCase()}
            </h4>
            <span className="text-xs text-emerald-400 font-mono">
              Latency: {results.results.metadata.total_latency_ms}ms
            </span>
          </div>

          <div className="space-y-3">
            {results.results.chunks.map((c, i) => (
              <div
                key={i}
                onClick={() => onSelectSource(c)}
                className="p-4 bg-slate-950/70 hover:bg-slate-800/40 border border-slate-800 rounded-xl cursor-pointer transition-colors space-y-2"
              >
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-medium text-slate-200">
                    {c.document_filename} (Page {c.page_number})
                  </span>
                  <span className="text-emerald-400 font-mono font-semibold">
                    {c.similarity !== undefined ? `${(c.similarity * 100).toFixed(1)}% match` : `RRF Score: ${c.rrf_score}`}
                  </span>
                </div>
                <p className="text-xs text-slate-300 font-mono leading-relaxed">
                  {c.content}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
