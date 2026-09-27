import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, User, Bookmark, ExternalLink, Cpu } from 'lucide-react';

export default function ChatMessage({ message, onSelectSource }) {
  const isUser = message.role === 'user';
  const sources = message.sources || [];
  const meta = message.retrieval_metadata || {};

  return (
    <div className={`py-5 px-4 md:px-8 flex space-x-4 ${isUser ? 'bg-slate-900/30' : 'bg-slate-900/80 border-y border-slate-800/40'}`}>
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-md">
            <User className="w-4 h-4" />
          </div>
        ) : (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 font-bold shadow-md">
            <Bot className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Message Body */}
      <div className="flex-1 min-w-0 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            {isUser ? 'You' : 'SmartDocs AI'}
          </span>
          {meta.strategy && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60 flex items-center gap-1 font-mono">
              <Cpu className="w-2.5 h-2.5 text-emerald-400" />
              {meta.strategy.toUpperCase()} • {meta.total_latency_ms}ms
            </span>
          )}
        </div>

        {/* Markdown Content */}
        <div className="prose prose-invert max-w-none text-sm text-slate-200 leading-relaxed font-normal">
          <ReactMarkdown
            components={{
              p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
              ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-2 space-y-1" {...props} />,
              ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-2 space-y-1" {...props} />,
              li: ({ node, ...props }) => <li className="text-slate-300" {...props} />,
              strong: ({ node, ...props }) => <strong className="font-semibold text-white" {...props} />,
              code: ({ node, inline, ...props }) => (
                inline ? (
                  <code className="bg-slate-800 px-1.5 py-0.5 rounded text-emerald-400 font-mono text-xs" {...props} />
                ) : (
                  <pre className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-xs overflow-x-auto my-2 text-emerald-300 font-mono" {...props} />
                )
              ),
              blockquote: ({ node, ...props }) => (
                <blockquote className="border-l-2 border-emerald-500/70 pl-3 italic text-slate-400 my-2" {...props} />
              )
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Source Citations Pills */}
        {!isUser && sources.length > 0 && (
          <div className="pt-2 border-t border-slate-800/60 mt-3">
            <span className="text-[11px] font-medium text-slate-400 block mb-1.5 flex items-center gap-1.5">
              <Bookmark className="w-3 h-3 text-emerald-400" />
              Grounded Evidence & Source Citations ({sources.length}):
            </span>
            <div className="flex flex-wrap gap-2">
              {sources.map((src, idx) => {
                const scoreText = src.similarity !== undefined
                  ? `${(src.similarity * 100).toFixed(0)}%`
                  : (src.rrf_score ? `Rank ${idx + 1}` : 'Src');
                return (
                  <button
                    key={idx}
                    onClick={() => onSelectSource(src)}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/80 text-xs text-slate-300 hover:text-white transition-all group shadow-sm"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 group-hover:scale-125 transition-transform" />
                    <span className="font-medium truncate max-w-[140px]">{src.document_filename || `Doc ${idx+1}`}</span>
                    <span className="text-slate-400 text-[10px]">p.{src.page_number || 1}</span>
                    <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-1 rounded">{scoreText}</span>
                    <ExternalLink className="w-2.5 h-2.5 text-slate-500 group-hover:text-slate-300" />
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
