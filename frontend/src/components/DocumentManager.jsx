import React, { useState } from 'react';
import { UploadCloud, File, Trash2, CheckCircle2, Clock, AlertTriangle, Layers, Eye, RefreshCw, X } from 'lucide-react';
import { api } from '../services/api';

export default function DocumentManager({ documents, onRefresh, onSelectSource }) {
  const [uploading, setUploading] = useState(false);
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(80);
  const [selectedDocChunks, setSelectedDocChunks] = useState(null);
  const [inspectingDocName, setInspectingDocName] = useState('');
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setUploading(true);
    setErrorMsg('');

    try {
      await api.uploadDocument(file, chunkSize, chunkOverlap);
      await onRefresh();
    } catch (err) {
      setErrorMsg(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm("Are you sure you want to delete this document and its vector embeddings?")) return;
    try {
      await api.deleteDocument(docId);
      await onRefresh();
    } catch (err) {
      alert("Error deleting document: " + err.message);
    }
  };

  const handleInspect = async (doc) => {
    setLoadingChunks(true);
    setInspectingDocName(doc.filename);
    try {
      const data = await api.getDocument(doc.id);
      setSelectedDocChunks(data.chunks || []);
    } catch (err) {
      alert("Error fetching chunks: " + err.message);
    } finally {
      setLoadingChunks(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" />
            Document Ingestion & Chunking Pipeline
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Ingest PDFs, TXT, or MD documents. Configure recursive chunking boundaries and generate embeddings.
          </p>
        </div>
        <button
          onClick={onRefresh}
          className="p-2 text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-xl transition-colors flex items-center gap-2 text-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-950/60 border border-red-800 rounded-xl text-xs text-red-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Ingestion Configuration Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
        {/* Dropzone */}
        <div className="md:col-span-2">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              handleFileUpload(e.dataTransfer.files);
            }}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-all flex flex-col items-center justify-center min-h-[180px] ${
              dragActive ? 'border-emerald-500 bg-emerald-500/10' : 'border-slate-700/80 hover:border-slate-600 bg-slate-950/40'
            }`}
          >
            <UploadCloud className="w-10 h-10 text-emerald-400 mb-3 animate-pulse" />
            <h4 className="text-sm font-semibold text-slate-200">
              Drag & Drop PDF or Text files here
            </h4>
            <p className="text-xs text-slate-400 mt-1">
              Supports .pdf, .txt, .md, .csv (auto-parsed into pages and semantic chunks)
            </p>

            <label className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold rounded-xl text-xs cursor-pointer transition-colors shadow-lg shadow-emerald-950/50">
              {uploading ? 'Processing & Indexing...' : 'Browse Local Files'}
              <input
                type="file"
                className="hidden"
                accept=".pdf,.txt,.md,.csv,.json"
                onChange={(e) => handleFileUpload(e.target.files)}
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {/* Chunking Hyperparameter Controls */}
        <div className="space-y-4 bg-slate-950/50 p-4 rounded-xl border border-slate-800/80">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Ingestion Tuning Parameters
          </h4>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Target Chunk Size:</span>
              <span className="text-emerald-400 font-mono font-medium">{chunkSize} chars</span>
            </div>
            <input
              type="range"
              min="200"
              max="1500"
              step="50"
              value={chunkSize}
              onChange={(e) => setChunkSize(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block mt-0.5">
              ~{Math.round(chunkSize / 4)} tokens. Smaller = granular, larger = more context.
            </span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">Chunk Overlap:</span>
              <span className="text-emerald-400 font-mono font-medium">{chunkOverlap} chars</span>
            </div>
            <input
              type="range"
              min="20"
              max="300"
              step="10"
              value={chunkOverlap}
              onChange={(e) => setChunkOverlap(Number(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
            <span className="text-[10px] text-slate-500 block mt-0.5">
              Preserves contextual continuity across split boundaries.
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400 leading-normal">
            💡 <strong className="text-slate-200">Interview Tip:</strong> We tuned chunk size to 500 characters with 80-character overlap to balance high semantic density while preventing context fragmentation.
          </div>
        </div>
      </div>

      {/* Indexed Documents Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="font-semibold text-slate-200 text-sm">
            Indexed Corpus ({documents.length} Documents)
          </h3>
        </div>

        {documents.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            No documents uploaded yet. Upload a PDF or TXT document above to start indexing into pgvector!
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {documents.map((doc) => (
              <div key={doc.id} className="p-4 px-6 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                <div className="flex items-center space-x-3 min-w-0">
                  <div className="p-2 rounded-lg bg-slate-800 text-emerald-400">
                    <File className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <h5 className="font-medium text-slate-200 text-sm truncate max-w-sm">
                      {doc.filename}
                    </h5>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                      <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                      <span>•</span>
                      <span>{doc.page_count} Pages</span>
                      <span>•</span>
                      <span className="text-emerald-400 font-mono font-medium">{doc.chunk_count} Chunks</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  {doc.status === 'completed' && (
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] flex items-center gap-1 font-medium">
                      <CheckCircle2 className="w-3 h-3" /> Indexed
                    </span>
                  )}
                  {doc.status === 'processing' && (
                    <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] flex items-center gap-1 font-medium animate-pulse">
                      <Clock className="w-3 h-3" /> Processing
                    </span>
                  )}
                  {doc.status === 'failed' && (
                    <span className="px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/20 text-[11px] flex items-center gap-1 font-medium">
                      <AlertTriangle className="w-3 h-3" /> Error
                    </span>
                  )}

                  <button
                    onClick={() => handleInspect(doc)}
                    className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Inspect chunks and embeddings"
                  >
                    <Eye className="w-4 h-4" />
                  </button>

                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Inspect Chunks Modal */}
      {selectedDocChunks && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-white text-base">
                  Chunks Inspector: {inspectingDocName}
                </h3>
                <p className="text-xs text-slate-400">
                  {selectedDocChunks.length} semantic chunks generated using RecursiveCharacterTextSplitter
                </p>
              </div>
              <button
                onClick={() => setSelectedDocChunks(null)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              {selectedDocChunks.map((chunk, idx) => (
                <div key={chunk.id} className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span className="font-semibold text-emerald-400 font-mono">
                      Chunk #{chunk.chunk_index} (Page {chunk.page_number})
                    </span>
                    <span className="font-mono text-[11px] text-slate-500">
                      {chunk.content.length} chars • ~{chunk.token_count} tokens
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 font-mono leading-relaxed bg-slate-900/50 p-3 rounded-lg border border-slate-800/60">
                    {chunk.content}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
