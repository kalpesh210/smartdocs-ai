import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, Sparkles, SlidersHorizontal, AlertCircle, FileText } from 'lucide-react';
import ChatMessage from './ChatMessage';

export default function ChatInterface({
  messages,
  onSendMessage,
  loading,
  onSelectSource,
  documentsCount,
  onNavigateToDocs
}) {
  const [input, setInput] = useState('');
  const [strategy, setStrategy] = useState('hybrid');
  const [showSettings, setShowSettings] = useState(false);
  const [topK, setTopK] = useState(4);
  const [threshold, setThreshold] = useState(0.40);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;
    onSendMessage({
      message: input,
      retrieval_strategy: strategy,
      top_k: topK,
      similarity_threshold: threshold
    });
    setInput('');
  };

  const sampleQuestions = [
    "What are the key architectural components of this RAG pipeline?",
    "How does PostgreSQL with pgvector handle vector similarity search?",
    "Explain the tuning techniques used to improve retrieval accuracy."
  ];

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-hidden relative">
      {/* Top Header / Active Settings Bar */}
      <div className="px-6 py-3 border-b border-slate-800 bg-slate-900/40 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <span className="text-xs font-semibold text-slate-300">Strategy:</span>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="text-xs bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
          >
            <option value="hybrid">⚡ Hybrid (RRF: Dense + Sparse)</option>
            <option value="vector">Dense Vector (pgvector)</option>
            <option value="keyword">Sparse Lexical (BM25)</option>
            <option value="mmr">MMR (Diversity Re-ranking)</option>
          </select>

          <span className="text-xs text-slate-500">•</span>
          <span className="text-xs text-slate-400 font-mono">Top-K: {topK}</span>
          <span className="text-xs text-slate-500">•</span>
          <span className="text-xs text-slate-400 font-mono">Cutoff: {threshold}</span>
        </div>

        <button
          onClick={() => setShowSettings(!showSettings)}
          className={`p-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-colors ${
            showSettings
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
          title="Tuning Settings"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Tuning</span>
        </button>
      </div>

      {/* Popover Settings Drawer */}
      {showSettings && (
        <div className="px-6 py-3 bg-slate-900/90 border-b border-slate-800 flex flex-wrap items-center gap-6 text-xs animate-fadeIn">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Top-K Chunks:</span>
            <input
              type="range"
              min="1"
              max="8"
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-24 accent-emerald-500 cursor-pointer"
            />
            <span className="font-mono text-emerald-400">{topK}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400">Similarity Cutoff:</span>
            <input
              type="range"
              min="0.0"
              max="0.8"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-24 accent-emerald-500 cursor-pointer"
            />
            <span className="font-mono text-emerald-400">{threshold.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-8 text-center max-w-xl mx-auto space-y-6">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 font-bold shadow-xl shadow-emerald-500/20">
              <Bot className="w-7 h-7" />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-bold text-white">
                SmartDocs AI Assistant
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Ask questions grounded strictly in your uploaded PDF documents. 
                Responses include verifiable page citations, similarity scores, and multi-turn query context.
              </p>
            </div>

            {documentsCount === 0 && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-300 flex items-center gap-2 text-left">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>No documents indexed yet. Upload a document in Document Ingestion to query against your knowledge base!</span>
              </div>
            )}

            {/* Prompt Starter Pills */}
            <div className="w-full space-y-2 pt-2">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
                Sample Interview & Domain Questions:
              </span>
              {sampleQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => setInput(q)}
                  className="w-full text-left p-3 rounded-xl bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800 text-xs text-slate-300 hover:text-white transition-colors"
                >
                  "{q}"
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/40">
            {messages.map((msg, i) => (
              <ChatMessage
                key={msg.id || i}
                message={msg}
                onSelectSource={onSelectSource}
              />
            ))}
            {loading && (
              <div className="py-5 px-8 flex space-x-4 bg-slate-900/50">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <Sparkles className="w-4 h-4 animate-spin" />
                </div>
                <div className="flex-1 space-y-2 pt-1">
                  <div className="text-xs text-slate-400 flex items-center gap-2">
                    <span>Retrieving relevant chunks & formulating grounded answer...</span>
                  </div>
                  <div className="h-2 w-32 bg-slate-800 rounded animate-pulse" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Box Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/60">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents (or follow up on previous turns)..."
            className="w-full pl-4 pr-12 py-3 bg-slate-950 border border-slate-700/80 rounded-2xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors shadow-inner"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="absolute right-2 p-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-slate-950 font-bold transition-colors shadow-md"
            title="Send Message"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <p className="text-[10px] text-center text-slate-500 mt-2">
          Grounded with strict anti-hallucination prompts. Citations are verified against stored vector passages.
        </p>
      </div>
    </div>
  );
}
