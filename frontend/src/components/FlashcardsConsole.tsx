'use client';

import React, { useState, useEffect } from 'react';
import {
  Layers,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  RotateCw,
  Shuffle,
  CheckCircle2,
  HelpCircle,
  Trash2,
  BookOpen,
  LayoutGrid,
  Maximize2
} from 'lucide-react';

interface Flashcard {
  id: string;
  document_id: string;
  source_chunk_id?: string;
  question: string;
  answer: string;
  created_at: string;
}

interface FlashcardsConsoleProps {
  authToken: string | null;
  documents: Array<{ id: string; filename: string }>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function FlashcardsConsole({ authToken, documents }: FlashcardsConsoleProps) {
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>('all');
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isFlipped, setIsFlipped] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'study' | 'grid'>('study');
  const [masteredIds, setMasteredIds] = useState<Set<string>>(new Set());
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Fetch flashcards
  const fetchCards = async () => {
    if (!authToken) return;
    setIsLoading(true);
    try {
      const url = selectedDocId === 'all'
        ? `${API_BASE}/api/v1/flashcards/`
        : `${API_BASE}/api/v1/flashcards/?document_id=${selectedDocId}`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCards(data);
        setCurrentIndex(0);
        setIsFlipped(false);
      }
    } catch (err) {
      console.error('Fetch Flashcards Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCards();
  }, [authToken, selectedDocId]);

  // Generate Flashcards for current document
  const handleGenerate = async () => {
    if (!authToken || selectedDocId === 'all') return;
    setIsGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/flashcards/generate/${selectedDocId}?max_cards=6`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        await fetchCards();
      }
    } catch (err) {
      console.error('Generate Flashcards Error:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  // Delete single flashcard
  const handleDeleteCard = async (id: string) => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/flashcards/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok || res.status === 204) {
        setCards((prev) => prev.filter((c) => c.id !== id));
        if (currentIndex >= cards.length - 1 && currentIndex > 0) {
          setCurrentIndex((prev) => prev - 1);
        }
        setIsFlipped(false);
      }
    } catch (err) {
      console.error('Delete Flashcard Error:', err);
    }
  };

  // Navigation handlers
  const handleNext = () => {
    if (cards.length === 0) return;
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev + 1) % cards.length);
  };

  const handlePrev = () => {
    if (cards.length === 0) return;
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev - 1 + cards.length) % cards.length);
  };

  const handleShuffle = () => {
    if (cards.length <= 1) return;
    setIsFlipped(false);
    const shuffled = [...cards].sort(() => Math.random() - 0.5);
    setCards(shuffled);
    setCurrentIndex(0);
  };

  const toggleMastered = (id: string) => {
    setMasteredIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Document name resolver
  const getDocName = (docId: string) => {
    const doc = documents.find((d) => d.id === docId);
    return doc ? doc.filename : 'Document';
  };

  const currentCard = cards[currentIndex];
  const isCurrentMastered = currentCard ? masteredIds.has(currentCard.id) : false;

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/70 border border-slate-800">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-100">Study Flashcards Studio</h2>
            <p className="text-xs text-slate-400">
              AI-generated structured Q&A pairs directly extracted from document chunks
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Document filter */}
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 max-w-[200px]"
          >
            <option value="all">All Documents ({cards.length} cards)</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename}
              </option>
            ))}
          </select>

          {/* Generate Button (only for a specific document) */}
          {selectedDocId !== 'all' && (
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold shadow-md shadow-purple-600/20 transition-all disabled:opacity-50"
            >
              <Sparkles className={`h-3.5 w-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
              {isGenerating ? 'Extracting...' : 'Generate Cards'}
            </button>
          )}

          {/* Mode Switcher */}
          <div className="flex items-center bg-slate-950 rounded-xl p-1 border border-slate-800">
            <button
              onClick={() => setViewMode('study')}
              className={`p-1.5 rounded-lg text-xs font-medium transition-colors ${
                viewMode === 'study' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Study Mode"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg text-xs font-medium transition-colors ${
                viewMode === 'grid' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Grid View"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {cards.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-900/50 border border-slate-800 space-y-4">
          <BookOpen className="h-12 w-12 text-slate-600 mx-auto" />
          <div>
            <h3 className="text-sm font-semibold text-slate-300">No Flashcards Available</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Select a specific document from the dropdown above and click &quot;Generate Cards&quot; to synthesize structured Q&A flashcards using LLM tool extraction.
            </p>
          </div>
        </div>
      ) : viewMode === 'study' ? (
        /* Single Card 3D Flip Study Mode */
        <div className="flex flex-col items-center space-y-6 max-w-2xl mx-auto">
          {/* Progress and status */}
          <div className="w-full flex items-center justify-between text-xs text-slate-400 px-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-200">
                Card {currentIndex + 1} of {cards.length}
              </span>
              <span>•</span>
              <span className="text-emerald-400 font-medium">
                {masteredIds.size} Mastered
              </span>
            </div>
            <button
              onClick={handleShuffle}
              className="flex items-center gap-1.5 hover:text-indigo-400 transition-colors"
            >
              <Shuffle className="h-3.5 w-3.5" /> Shuffle Deck
            </button>
          </div>

          {/* 3D Flip Card Container */}
          <div
            className="w-full h-80 cursor-pointer perspective-1000 group"
            onClick={() => setIsFlipped(!isFlipped)}
          >
            <div
              className={`relative w-full h-full rounded-2xl transition-transform duration-500 transform-style-3d shadow-2xl border ${
                isFlipped
                  ? 'rotate-y-180 bg-slate-900/90 border-purple-500/40'
                  : 'bg-slate-900/90 border-indigo-500/40 hover:border-indigo-400/60'
              }`}
            >
              {/* FRONT (QUESTION) */}
              <div
                className={`absolute inset-0 p-8 flex flex-col justify-between backface-hidden ${
                  isFlipped ? 'pointer-events-none' : ''
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-[11px] font-semibold text-indigo-400 uppercase tracking-wider">
                      Question
                    </span>
                    <span className="text-[11px] text-slate-500 truncate max-w-[200px]">
                      {getDocName(currentCard.document_id)}
                    </span>
                  </div>
                  <h3 className="mt-6 text-lg font-semibold text-slate-100 leading-relaxed">
                    {currentCard.question}
                  </h3>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-800/80 text-slate-500 text-xs">
                  <div className="flex items-center gap-1.5">
                    <RotateCw className="h-3.5 w-3.5" />
                    <span>Click card to reveal answer</span>
                  </div>
                  {isCurrentMastered && (
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Mastered
                    </span>
                  )}
                </div>
              </div>

              {/* BACK (ANSWER) */}
              <div
                className={`absolute inset-0 p-8 flex flex-col justify-between backface-hidden rotate-y-180 bg-slate-950/95 rounded-2xl ${
                  !isFlipped ? 'pointer-events-none' : ''
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="px-2.5 py-1 rounded-md bg-purple-500/10 border border-purple-500/20 text-[11px] font-semibold text-purple-400 uppercase tracking-wider">
                      Answer
                    </span>
                    <span className="text-[11px] text-slate-500 truncate max-w-[200px]">
                      {getDocName(currentCard.document_id)}
                    </span>
                  </div>
                  <div className="mt-4 text-sm text-slate-200 leading-relaxed max-h-40 overflow-y-auto pr-1">
                    {currentCard.answer}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-800/80 text-slate-500 text-xs">
                  <div className="flex items-center gap-1.5 text-indigo-400">
                    <RotateCw className="h-3.5 w-3.5" />
                    <span>Click to flip back to question</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCard(currentCard.id);
                    }}
                    className="text-slate-500 hover:text-rose-400 transition-colors"
                    title="Delete card"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Action Controls */}
          <div className="flex items-center gap-4">
            <button
              onClick={handlePrev}
              className="p-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
              title="Previous Card"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>

            <button
              onClick={() => toggleMastered(currentCard.id)}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl text-xs font-semibold border transition-all ${
                isCurrentMastered
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <CheckCircle2 className="h-4 w-4" />
              {isCurrentMastered ? 'Mastered!' : 'Mark as Mastered'}
            </button>

            <button
              onClick={handleNext}
              className="p-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-colors"
              title="Next Card"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        </div>
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {cards.map((card, idx) => (
            <div
              key={card.id}
              className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold text-indigo-400">Card #{idx + 1}</span>
                  <span className="text-[10px] text-slate-500 truncate max-w-[140px]">
                    {getDocName(card.document_id)}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-slate-200 line-clamp-2">
                  {card.question}
                </h4>
                <p className="text-xs text-slate-400 line-clamp-3">
                  {card.answer}
                </p>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-800 text-xs">
                <button
                  onClick={() => {
                    setCurrentIndex(idx);
                    setViewMode('study');
                    setIsFlipped(false);
                  }}
                  className="text-xs text-indigo-400 hover:underline font-medium"
                >
                  Study This Card &rarr;
                </button>
                <button
                  onClick={() => handleDeleteCard(card.id)}
                  className="text-slate-500 hover:text-rose-400 transition-colors"
                  title="Delete card"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
