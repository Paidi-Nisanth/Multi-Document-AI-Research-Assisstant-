'use client';

import React, { useState } from 'react';
import { X, Cpu, Layers, CheckSquare, Square, Plus, Trash2, Play, Copy, Check, FileText, Sparkles, RefreshCw } from 'lucide-react';

interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  doc_metadata?: {
    chunk_count?: number;
  };
}

interface MultiDocCompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  documents: DocumentItem[];
  authToken: string | null;
  apiBase: string;
}

const PRESET_AXES = [
  'Core Architecture & Methodology',
  'Precision & Numeric Formats',
  'Accuracy & Perplexity Impact',
  'Hardware Overhead & Latency',
  'Primary Limitations & Scope'
];

export default function MultiDocCompareModal({
  isOpen,
  onClose,
  documents,
  authToken,
  apiBase
}: MultiDocCompareModalProps) {
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [axes, setAxes] = useState<string[]>(PRESET_AXES);
  const [newAxisInput, setNewAxisInput] = useState('');
  const [customQuery, setCustomQuery] = useState('');
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Initialize selectedDocIds with first 2 documents if available
  React.useEffect(() => {
    if (documents.length >= 2 && selectedDocIds.length === 0) {
      setSelectedDocIds([documents[0].id, documents[1].id]);
    }
  }, [documents]);

  if (!isOpen) return null;

  const toggleDocSelection = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId)
        ? prev.filter((id) => id !== docId)
        : [...prev, docId]
    );
  };

  const handleAddAxis = (e: React.FormEvent) => {
    e.preventDefault();
    if (newAxisInput.trim() && !axes.includes(newAxisInput.trim())) {
      setAxes([...axes, newAxisInput.trim()]);
      setNewAxisInput('');
    }
  };

  const handleRemoveAxis = (axisToRemove: string) => {
    setAxes(axes.filter((a) => a !== axisToRemove));
  };

  const handleRunComparison = async () => {
    if (selectedDocIds.length < 2 || !authToken || isComparing) return;

    setIsComparing(true);
    setComparisonResult(null);

    try {
      const response = await fetch(`${apiBase}/api/v1/chat/compare`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          document_ids: selectedDocIds,
          comparison_axes: axes,
          query: customQuery.trim() || 'Comprehensive multi-document comparative analysis',
        }),
      });

      if (!response.ok) {
        throw new Error(`Comparison request failed with status ${response.status}`);
      }

      const data = await response.json();
      setComparisonResult(data.synthesis || 'No synthesis generated.');
    } catch (err: any) {
      console.error('Comparison Error:', err);
      setComparisonResult(`Error executing multi-document comparison: ${err.message}`);
    } finally {
      setIsComparing(false);
    }
  };

  const handleCopy = () => {
    if (comparisonResult) {
      navigator.clipboard.writeText(comparisonResult);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Helper to render Markdown tables and text inside comparison view
  const renderComparisonMarkdown = (text: string) => {
    if (!text) return null;

    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let currentTableRows: string[][] = [];

    const flushTable = () => {
      if (currentTableRows.length > 0) {
        const headerRow = currentTableRows[0];
        const bodyRows = currentTableRows.slice(1).filter((r) => !r[0]?.startsWith('---'));

        elements.push(
          <div key={`table-${elements.length}`} className="my-4 overflow-x-auto rounded-xl border border-slate-700/80 bg-slate-950/80 p-1">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 border-b border-slate-700 text-slate-200">
                  {headerRow.map((cell, cIdx) => (
                    <th key={cIdx} className="px-3.5 py-2.5 font-bold uppercase tracking-wider text-[11px] text-indigo-400">
                      {cell.trim()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-300">
                {bodyRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-900/40 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3.5 py-2.5 leading-relaxed font-normal">
                        {cell.trim()}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        currentTableRows = [];
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        const cells = trimmed.split('|').slice(1, -1);
        currentTableRows.push(cells);
        continue;
      } else {
        flushTable();
      }

      if (trimmed.startsWith('## ')) {
        elements.push(
          <h2 key={`h2-${i}`} className="text-base font-bold text-white mt-6 mb-2 flex items-center gap-2 border-b border-slate-800 pb-1.5">
            <span className="h-2 w-2 rounded-full bg-indigo-500" />
            {trimmed.slice(3)}
          </h2>
        );
        continue;
      }

      if (trimmed.startsWith('### ')) {
        elements.push(
          <h3 key={`h3-${i}`} className="text-sm font-semibold text-slate-200 mt-4 mb-1">
            {trimmed.slice(4)}
          </h3>
        );
        continue;
      }

      if (trimmed === '---') {
        elements.push(<hr key={`hr-${i}`} className="border-slate-800 my-4" />);
        continue;
      }

      if (!trimmed) {
        elements.push(<div key={`empty-${i}`} className="h-2" />);
        continue;
      }

      elements.push(
        <p key={`p-${i}`} className="text-xs text-slate-300 leading-relaxed my-1">
          {trimmed}
        </p>
      );
    }

    flushTable();
    return <div className="space-y-1">{elements}</div>;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                Multi-Document Map-Reduce Comparison Studio
                <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-600/20 text-indigo-300 border border-indigo-500/30">
                  STAGE 5
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Execute parallel Map extractions per paper and a single Reduce synthesis into a structured comparative matrix.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Step 1: Select Documents */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-400" />
                1. Select Papers to Compare (Min 2)
              </h3>
              <span className="text-xs text-indigo-400 font-semibold">
                {selectedDocIds.length} Selected
              </span>
            </div>

            {documents.length < 2 ? (
              <p className="text-xs text-rose-400 bg-rose-500/10 p-3 rounded-xl border border-rose-500/20">
                You need at least 2 uploaded documents in your workspace to run a comparative synthesis.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-48 overflow-y-auto p-1">
                {documents.map((doc) => {
                  const isChecked = selectedDocIds.includes(doc.id);
                  return (
                    <div
                      key={doc.id}
                      onClick={() => toggleDocSelection(doc.id)}
                      className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                        isChecked
                          ? 'bg-indigo-950/30 border-indigo-500/50 text-slate-100 shadow-sm'
                          : 'bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      {isChecked ? (
                        <CheckSquare className="h-4 w-4 text-indigo-400 shrink-0" />
                      ) : (
                        <Square className="h-4 w-4 text-slate-600 shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold truncate">{doc.filename}</p>
                        <p className="text-[11px] text-slate-500">
                          {doc.file_type.toUpperCase()} • {(doc.file_size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Step 2: Comparison Axes */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-400" />
              2. Comparison Axes (Rows of Matrix)
            </h3>
            <div className="flex flex-wrap gap-2">
              {axes.map((axis) => (
                <span
                  key={axis}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs bg-slate-950 text-slate-200 border border-slate-800"
                >
                  {axis}
                  <button
                    onClick={() => handleRemoveAxis(axis)}
                    className="text-slate-500 hover:text-rose-400 transition-colors"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>

            <form onSubmit={handleAddAxis} className="flex gap-2">
              <input
                type="text"
                value={newAxisInput}
                onChange={(e) => setNewAxisInput(e.target.value)}
                placeholder="Add custom comparison axis (e.g. Memory Bandwidth, Silicon Area)..."
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                disabled={!newAxisInput.trim()}
                className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1 transition-all"
              >
                <Plus className="h-3.5 w-3.5" /> Add Axis
              </button>
            </form>
          </div>

          {/* Step 3: Custom Focus / Query */}
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300">
              3. Focus Prompt (Optional)
            </label>
            <input
              type="text"
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              placeholder="e.g. Compare quantization overhead and hardware multiplier efficiency..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Run Action */}
          <div>
            <button
              onClick={handleRunComparison}
              disabled={isComparing || selectedDocIds.length < 2}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 hover:from-indigo-500 hover:to-pink-500 disabled:opacity-50 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center gap-2"
            >
              {isComparing ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Running Parallel Map-Reduce Comparison...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white" />
                  Generate Parallel Map-Reduce Comparison Matrix
                </>
              )}
            </button>
          </div>

          {/* Comparison Output */}
          {comparisonResult && (
            <div className="space-y-3 pt-4 border-t border-slate-800">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Comparative Synthesis Report
                </h3>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all"
                >
                  {copied ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-400" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" /> Copy Markdown
                    </>
                  )}
                </button>
              </div>

              <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 max-h-[400px] overflow-y-auto">
                {renderComparisonMarkdown(comparisonResult)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
