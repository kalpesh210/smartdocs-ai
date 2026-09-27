import React from 'react';
import { X, FileText, CheckCircle, Percent, Bookmark } from 'lucide-react';

export default function SourceModal({ source, onClose }) {
  if (!source) return null;

  const score = source.similarity !== undefined 
    ? `${(source.similarity * 100).toFixed(1)}% match` 
    : (source.rrf_score ? `RRF Rank: ${source.rrf_score}` : 'Retrieved');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-100 text-base">
                {source.document_filename || "Document Chunk"}
              </h3>
              <p className="text-xs text-slate-400 flex items-center gap-3 mt-0.5">
                <span>Page {source.page_number || 1}</span>
                <span>•</span>
                <span>Chunk #{source.chunk_index !== undefined ? source.chunk_index : 'N/A'}</span>
                <span>•</span>
                <span className="text-emerald-400 font-medium">{score}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm leading-relaxed text-slate-300">
          <div className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl font-mono text-xs whitespace-pre-wrap selection:bg-emerald-500/30">
            {source.content}
          </div>

          {source.metadata && (
            <div className="bg-slate-800/40 rounded-xl p-3 text-xs border border-slate-800">
              <span className="text-slate-400 font-semibold block mb-1">Chunk Provenance Metadata:</span>
              <pre className="text-slate-300 overflow-x-auto">
                {JSON.stringify(source.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/40 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium transition-colors"
          >
            Close Excerpt
          </button>
        </div>
      </div>
    </div>
  );
}
