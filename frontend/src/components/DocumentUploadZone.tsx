'use client';

import React, { useState } from 'react';
import { UploadCloud, File, CheckCircle2, Clock, AlertCircle, RefreshCw, FileText, Layers, Trash2, Sparkles } from 'lucide-react';

interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'chunked' | 'ready' | 'error';
  created_at: string;
  doc_metadata?: {
    chunk_count?: number;
    embeddings_count?: number;
    extracted_blocks_count?: number;
  };
}

interface DocumentUploadZoneProps {
  documents: DocumentItem[];
  onUpload: (file: File) => Promise<void>;
  onDelete: (documentId: string) => Promise<void>;
  onOpenSummary?: (documentId: string, filename: string) => void;
  onRefresh: () => void;
  isUploading: boolean;
}

export default function DocumentUploadZone({
  documents,
  onUpload,
  onDelete,
  onOpenSummary,
  onRefresh,
  isUploading,
}: DocumentUploadZoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      onUpload(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      onUpload(file);
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (confirm(`Are you sure you want to remove '${filename}' from your research workspace?`)) {
      setDeletingId(docId);
      try {
        await onDelete(docId);
      } finally {
        setDeletingId(null);
      }
    }
  };

  const getStatusBadge = (status: DocumentItem['status']) => {
    switch (status) {
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3.5 w-3.5" /> Ready & Embedded
          </span>
        );
      case 'chunked':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Layers className="h-3.5 w-3.5" /> Chunked
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Processing
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <Clock className="h-3.5 w-3.5" /> Pending
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="h-3.5 w-3.5" /> Error
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload Box */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-300 ${
          dragActive
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
            : 'border-slate-800 hover:border-slate-700 bg-slate-900/40'
        }`}
      >
        <input
          type="file"
          id="file-upload"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={handleFileChange}
          disabled={isUploading}
        />
        <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-4">
          <div className="h-16 w-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shadow-inner">
            <UploadCloud className="h-8 w-8" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-200">
              {isUploading ? 'Uploading & Dispatched to Ingestion Pipeline...' : 'Drag & Drop Research Papers / Documents'}
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Supports <strong className="text-indigo-400">PDF, DOCX, TXT, MD</strong> up to 50MB
            </p>
          </div>
          <button
            type="button"
            onClick={() => document.getElementById('file-upload')?.click()}
            disabled={isUploading}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-all"
          >
            Select Document File
          </button>
        </label>
      </div>

      {/* Uploaded Documents List */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-400" />
            <h3 className="text-sm font-semibold text-slate-200">Ingested Document Repository</h3>
            <span className="px-2 py-0.5 rounded-md bg-slate-800 text-xs font-semibold text-slate-400">
              {documents.length}
            </span>
          </div>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-indigo-400 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh Status
          </button>
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs">
            No documents uploaded yet. Upload a PDF or TXT paper above to begin embedding and retrieval.
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition-all"
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-indigo-950/50 border border-indigo-800/40 flex items-center justify-center text-indigo-400">
                    <File className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-slate-200">{doc.filename}</h4>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                      <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                      <span>•</span>
                      <span>Type: {doc.file_type.toUpperCase()}</span>
                      {doc.doc_metadata?.chunk_count && (
                        <>
                          <span>•</span>
                          <span className="text-indigo-400">{doc.doc_metadata.chunk_count} Chunks</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {getStatusBadge(doc.status)}
                  {onOpenSummary && (doc.status === 'ready' || doc.status === 'chunked') && (
                    <button
                      onClick={() => onOpenSummary(doc.id, doc.filename)}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 text-xs font-medium transition-all"
                      title="View Executive Summary"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>Summary</span>
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(doc.id, doc.filename)}
                    disabled={deletingId === doc.id}
                    className="p-2 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all border border-transparent hover:border-rose-500/20"
                    title={`Delete '${doc.filename}'`}
                  >
                    {deletingId === doc.id ? (
                      <RefreshCw className="h-4 w-4 animate-spin text-rose-400" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
