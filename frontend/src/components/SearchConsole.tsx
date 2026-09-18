'use client';

import React, { useState } from 'react';
import { Search, Sparkles, Sliders, FileText, Bookmark, Zap, Cpu, Hash } from 'lucide-react';

interface SearchResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  section: string | null;
  page_number: number | null;
  content: string;
  similarity_score: number;
  rank?: number;
  rerank_score?: number;
  metadata?: {
    token_count?: number;
  };
}

interface SearchConsoleProps {
  onSearch: (query: string, mode: 'vector' | 'keyword' | 'hybrid' | 'rerank') => Promise<SearchResult[]>;
}

export default function SearchConsole({ onSearch }: SearchConsoleProps) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'vector' | 'keyword' | 'hybrid' | 'rerank'>('rerank');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearchSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setIsSearching(true);
    setHasSearched(true);
    try {
      const res = await onSearch(query, mode);
      setResults(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Header & Mode Selector */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 space-y-5">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-400" />
            Hybrid Semantic & Cross-Encoder Retrieval Engine
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Query across all ingested documents using <strong className="text-indigo-400">BGE-small dense embeddings</strong>, <strong className="text-purple-400">Postgres GIN full-text</strong>, <strong className="text-pink-400">RRF fusion</strong>, and <strong className="text-emerald-400">MS-MARCO Cross-Encoder reranking</strong>.
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-slate-950 p-1.5 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => setMode('vector')}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              mode === 'vector'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Sparkles className="h-3.5 w-3.5 text-indigo-300" /> Vector Cosine
          </button>
          <button
            type="button"
            onClick={() => setMode('keyword')}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              mode === 'keyword'
                ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Hash className="h-3.5 w-3.5 text-purple-300" /> Keyword FTS
          </button>
          <button
            type="button"
            onClick={() => setMode('hybrid')}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              mode === 'hybrid'
                ? 'bg-pink-600 text-white shadow-md shadow-pink-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Sliders className="h-3.5 w-3.5 text-pink-300" /> RRF Hybrid
          </button>
          <button
            type="button"
            onClick={() => setMode('rerank')}
            className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              mode === 'rerank'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Cpu className="h-3.5 w-3.5 text-emerald-300" /> Cross-Encoder Top 5
          </button>
        </div>

        {/* Query Input Form */}
        <form onSubmit={handleSearchSubmit} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. How do variational quantum algorithms optimize parameterized circuits?"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-11 pr-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 disabled:opacity-50 transition-all flex items-center gap-2"
          >
            {isSearching ? <Sparkles className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Execute Search
          </button>
        </form>
      </div>

      {/* Results Container */}
      <div className="space-y-4">
        {hasSearched && (
          <div className="flex items-center justify-between px-1 text-xs text-slate-400">
            <span>Returned <strong>{results.length}</strong> top matching chunks</span>
            <span>Search Mode: <strong className="text-indigo-400 uppercase">{mode}</strong></span>
          </div>
        )}

        {results.length === 0 && hasSearched && !isSearching && (
          <div className="bg-slate-900/40 rounded-2xl border border-slate-800 p-8 text-center text-slate-400 text-xs">
            No matching chunks found for query "{query}". Try adjusting keywords or choosing a different search mode.
          </div>
        )}

        {results.map((res, idx) => (
          <div
            key={res.chunk_id || idx}
            className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 hover:border-indigo-500/50 transition-all space-y-3"
          >
            {/* Header info */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="h-6 w-6 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 text-xs font-bold flex items-center justify-center">
                  #{res.rank || idx + 1}
                </span>
                <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-indigo-400" /> {res.filename}
                </span>
                {res.section && (
                  <span className="px-2 py-0.5 rounded-md bg-slate-800 text-[11px] font-medium text-slate-400 flex items-center gap-1">
                    <Bookmark className="h-3 w-3 text-purple-400" /> {res.section}
                  </span>
                )}
                {res.page_number && (
                  <span className="text-[11px] text-slate-500">Page {res.page_number}</span>
                )}
              </div>

              {/* Score Badges */}
              <div className="flex items-center gap-2">
                {res.rerank_score !== undefined && (
                  <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    Rerank Score: {res.rerank_score.toFixed(4)}
                  </span>
                )}
                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                  Similarity: {res.similarity_score}
                </span>
              </div>
            </div>

            {/* Chunk Content */}
            <p className="text-xs leading-relaxed text-slate-300 bg-slate-950/70 p-3.5 rounded-xl border border-slate-800/80 font-mono">
              "{res.content}"
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
