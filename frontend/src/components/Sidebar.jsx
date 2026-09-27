import React from 'react';
import { MessageSquare, Plus, Layers, Sliders, Award, Trash2, Database, Bot, Sparkles } from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  conversations,
  activeConvId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onOpenInterviewPrep,
  health,
  docCount
}) {
  return (
    <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col h-full flex-shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 font-bold shadow-md shadow-emerald-500/20">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-tight text-white flex items-center gap-1.5">
              SmartDocs AI
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                RAG
              </span>
            </h1>
            <p className="text-[10px] text-slate-400 font-mono">
              {health?.database_dialect === 'postgresql' ? 'pgvector • HNSW' : 'FastAPI • SQLite'}
            </p>
          </div>
        </div>
      </div>

      {/* Main Navigation Tabs */}
      <div className="p-3 space-y-1 border-b border-slate-800 text-xs">
        <button
          onClick={() => setActiveTab('chat')}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl font-medium transition-colors ${
            activeTab === 'chat'
              ? 'bg-emerald-500/10 text-emerald-400 font-semibold'
              : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>RAG Chatbot</span>
        </button>

        <button
          onClick={() => setActiveTab('documents')}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl font-medium transition-colors ${
            activeTab === 'documents'
              ? 'bg-emerald-500/10 text-emerald-400 font-semibold'
              : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
          }`}
        >
          <span className="flex items-center gap-2.5">
            <Layers className="w-4 h-4" />
            <span>Document Ingestion</span>
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-400">
            {docCount}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('retrieval')}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl font-medium transition-colors ${
            activeTab === 'retrieval'
              ? 'bg-emerald-500/10 text-emerald-400 font-semibold'
              : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Retrieval Tuning Lab</span>
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNewConversation}
          className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700/80 border border-slate-700/60 text-slate-200 text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-sm"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Conversation</span>
        </button>
      </div>

      {/* Conversation Sessions List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 px-3 py-1 block">
          Recent Sessions
        </span>

        {conversations.length === 0 ? (
          <div className="px-3 py-4 text-center text-xs text-slate-500">
            No chat history yet.
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = activeConvId === conv.id;
            return (
              <div
                key={conv.id}
                onClick={() => {
                  onSelectConversation(conv.id);
                  setActiveTab('chat');
                }}
                className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-slate-800 text-white font-medium'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <Bot className="w-3.5 h-3.5 flex-shrink-0 text-slate-500 group-hover:text-emerald-400" />
                  <span className="truncate max-w-[150px]">{conv.title || 'Conversation'}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 rounded transition-opacity"
                  title="Delete chat"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Interview Prep Banner at Bottom */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/40">
        <button
          onClick={onOpenInterviewPrep}
          className="w-full p-2.5 rounded-xl bg-gradient-to-r from-emerald-950/60 to-teal-950/60 border border-emerald-500/30 hover:border-emerald-500/60 text-emerald-300 text-xs font-semibold flex items-center justify-between transition-all group shadow-sm"
        >
          <span className="flex items-center gap-2">
            <Award className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
            <span>AI Interview Prep</span>
          </span>
          <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-mono">
            STAR
          </span>
        </button>
      </div>
    </aside>
  );
}
