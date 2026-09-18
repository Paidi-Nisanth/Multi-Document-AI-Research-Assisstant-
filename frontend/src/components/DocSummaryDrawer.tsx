'use client';

import React, { useState, useEffect } from 'react';
import { Sparkles, X, Copy, Check, RefreshCw, BookOpen, Clock, AlertCircle } from 'lucide-react';

interface DocumentSummary {
  document_id: string;
  summary: string;
  cached: boolean;
  total_chunks?: number;
  sections_processed?: number;
}

interface DocSummaryDrawerProps {
  documentId: string | null;
  filename: string | null;
  isOpen: boolean;
  onClose: () => void;
  authToken: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DocSummaryDrawer({
  documentId,
  filename,
  isOpen,
  onClose,
  authToken,
}: DocSummaryDrawerProps) {
  const [summaryData, setSummaryData] = useState<DocumentSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen && documentId && authToken) {
      loadSummary(false);
    } else {
      setSummaryData(null);
      setError(null);
    }
  }, [isOpen, documentId, authToken]);

  const loadSummary = async (forceRefresh: boolean = false) => {
    if (!documentId || !authToken) return;
    setIsLoading(true);
    setError(null);

    try {
      // First check if cached summary exists if not forcing refresh
      if (!forceRefresh) {
        const getRes = await fetch(`${API_BASE}/api/v1/documents/${documentId}/summary`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });
        if (getRes.ok) {
          const data = await getRes.json();
          if (data.summary) {
            setSummaryData(data);
            setIsLoading(false);
            return;
          }
        }
      }

      // Generate or force refresh
      const postRes = await fetch(`${API_BASE}/api/v1/documents/${documentId}/summarize`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ force_refresh: forceRefresh }),
      });

      if (!postRes.ok) {
        const errData = await postRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to generate document summary.');
      }

      const resData = await postRes.json();
      setSummaryData(resData);
    } catch (err: any) {
      console.error('Document Summary Error:', err);
      setError(err.message || 'An unexpected error occurred while generating summary.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (!summaryData?.summary) return;
    navigator.clipboard.writeText(summaryData.summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Structured Markdown Renderer
  const renderSummaryMarkdown = (content: string) => {
    if (!content) return null;
    const lines = content.split('\n');
    const elements: React.ReactNode[] = [];
    let currentList: React.ReactNode[] = [];

    const flushList = () => {
      if (currentList.length > 0) {
        elements.push(
          <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-1.5 my-2 pl-2 text-slate-300 text-xs">
            {currentList}
          </ul>
        );
        currentList = [];
      }
    };

    const renderBoldAndCode = (text: string) => {
      const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
      return parts.map((part, idx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={idx} className="font-semibold text-white">
              {part.slice(2, -2)}
            </strong>
          );
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <code key={idx} className="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-[11px]">
              {part.slice(1, -1)}
            </code>
          );
        }
        return part;
      });
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      if (trimmed === '---') {
        flushList();
        elements.push(<hr key={`hr-${i}`} className="border-slate-800 my-4" />);
        continue;
      }

      if (trimmed.startsWith('# ')) {
        flushList();
        elements.push(
          <h1 key={`h1-${i}`} className="text-lg font-bold text-white mt-5 mb-2 pb-2 border-b border-slate-800">
            {renderBoldAndCode(trimmed.slice(2))}
          </h1>
        );
        continue;
      }

      if (trimmed.startsWith('## ')) {
        flushList();
        elements.push(
          <h2 key={`h2-${i}`} className="text-base font-semibold text-indigo-300 mt-4 mb-2 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-indigo-500 inline-block" />
            {renderBoldAndCode(trimmed.slice(3))}
          </h2>
        );
        continue;
      }

      if (trimmed.startsWith('### ')) {
        flushList();
        elements.push(
          <h3 key={`h3-${i}`} className="text-sm font-semibold text-purple-300 mt-3 mb-1">
            {renderBoldAndCode(trimmed.slice(4))}
          </h3>
        );
        continue;
      }

      const bulletMatch = trimmed.match(/^[\*\-\•]\s+(.*)/) || trimmed.match(/^\d+\.\s+(.*)/);
      if (bulletMatch) {
        currentList.push(
          <li key={`li-${i}`} className="leading-relaxed text-slate-300">
            {renderBoldAndCode(bulletMatch[1])}
          </li>
        );
        continue;
      } else {
        flushList();
      }

      if (!trimmed) {
        elements.push(<div key={`empty-${i}`} className="h-2" />);
        continue;
      }

      elements.push(
        <p key={`p-${i}`} className="text-xs text-slate-300 leading-relaxed my-1.5">
          {renderBoldAndCode(trimmed)}
        </p>
      );
    }

    flushList();
    return <div className="space-y-1">{elements}</div>;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Slide-over Panel */}
      <div className="relative w-full max-w-2xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full z-10 animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                Executive Document Summary
              </h3>
              <p className="text-xs text-slate-400 truncate max-w-md" title={filename || ''}>
                {filename || 'Document'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {summaryData?.cached && (
              <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-medium text-emerald-400">
                Instant Cached
              </span>
            )}
            <button
              onClick={() => loadSummary(true)}
              disabled={isLoading}
              className="p-2 text-slate-400 hover:text-indigo-400 hover:bg-slate-800 rounded-lg transition-colors"
              title="Force Regenerate Summary"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20 space-y-4 text-center">
              <div className="relative">
                <div className="w-14 h-14 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                <Sparkles className="w-6 h-6 text-indigo-400 absolute inset-0 m-auto animate-pulse" />
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-slate-200">
                  Executing Hierarchical Map-Reduce
                </h4>
                <p className="text-xs text-slate-400 max-w-xs">
                  Partitioning chunks into semantic section clusters, synthesizing parallel section abstracts, and compiling executive synthesis...
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-start gap-3">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-semibold mb-1">Summarization Failed</strong>
                {error}
                <button
                  onClick={() => loadSummary(false)}
                  className="mt-3 block text-xs underline font-medium hover:text-rose-300"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}

          {!isLoading && !error && summaryData && (
            <div className="space-y-4">
              {/* Meta metrics */}
              <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs">
                <div className="flex items-center gap-2 text-slate-400">
                  <BookOpen className="h-4 w-4 text-indigo-400" />
                  <span>
                    Length: <strong className="text-slate-200">{summaryData.summary.length} chars</strong>
                  </span>
                </div>
                <div className="flex items-center gap-2 text-slate-400">
                  <Clock className="h-4 w-4 text-purple-400" />
                  <span>
                    Est. Read: <strong className="text-slate-200">~{Math.ceil(summaryData.summary.split(/\s+/).length / 200)} min</strong>
                  </span>
                </div>
              </div>

              {/* Formatted Markdown */}
              <div className="p-6 rounded-2xl bg-slate-950/50 border border-slate-800 text-slate-200 text-sm leading-relaxed">
                {renderSummaryMarkdown(summaryData.summary)}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {summaryData && !isLoading && (
          <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 text-emerald-400" />
                  <span className="text-emerald-400">Copied to Clipboard</span>
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  <span>Copy Summary Markdown</span>
                </>
              )}
            </button>

            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/25 transition-colors"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
