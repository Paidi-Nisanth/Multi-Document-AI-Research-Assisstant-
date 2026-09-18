'use client';

import React from 'react';
import { X, FileText, Bookmark, ExternalLink, Award, Hash } from 'lucide-react';

export interface CitationDetail {
  citation_id: number;
  chunk_id?: string;
  document_id?: string;
  filename?: string;
  section?: string;
  page_number?: number;
  content?: string;
  similarity_score?: number;
  rerank_score?: number;
}

interface SourceInspectorDrawerProps {
  citation: CitationDetail | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function SourceInspectorDrawer({
  citation,
  isOpen,
  onClose,
}: SourceInspectorDrawerProps) {
  if (!isOpen || !citation) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/70 backdrop-blur-sm transition-opacity animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-6 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-sm">
                [{citation.citation_id}]
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-indigo-400" />
                  Source Inspector
                </h3>
                <p className="text-xs text-slate-400 truncate max-w-xs">
                  {citation.filename || 'Cited Source Document'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Source Metadata Badges */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <Bookmark className="h-3 w-3 text-purple-400" /> Section Title
                </span>
                <p className="text-xs font-semibold text-slate-200 truncate">
                  {citation.section || 'General Content'}
                </p>
              </div>

              <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <Hash className="h-3 w-3 text-pink-400" /> Location
                </span>
                <p className="text-xs font-semibold text-slate-200">
                  Page {citation.page_number || 1}
                </p>
              </div>
            </div>

            {/* Relevance & Scores */}
            {(citation.similarity_score !== undefined || citation.rerank_score !== undefined) && (
              <div className="bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-950 p-4 rounded-xl border border-indigo-800/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Award className="h-4 w-4 text-amber-400" />
                  <span className="text-xs font-semibold text-slate-300">Retrieval Confidence Score</span>
                </div>
                <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-800/50">
                  {(citation.rerank_score ?? citation.similarity_score ?? 0).toFixed(4)}
                </span>
              </div>
            )}

            {/* Extracted Chunk Content */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Full Extracted Source Text
              </h4>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap selection:bg-indigo-600 selection:text-white">
                {citation.content || 'No chunk text content available for this citation.'}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 bg-slate-950/90 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Grounding Reference ID: {citation.chunk_id ? citation.chunk_id.slice(0, 8) : 'N/A'}</span>
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-md shadow-indigo-600/30"
            >
              Close Inspector
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
