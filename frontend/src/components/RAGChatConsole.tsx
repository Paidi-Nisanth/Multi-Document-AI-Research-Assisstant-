'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Sparkles,
  Sliders,
  Cpu,
  RefreshCw,
  BookOpen,
  Plus,
  History,
  BrainCircuit,
  Scale,
  Trash2,
  ChevronDown,
  Zap
} from 'lucide-react';
import SourceInspectorDrawer, { CitationDetail } from './SourceInspectorDrawer';
import MultiDocCompareModal from './MultiDocCompareModal';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  citations?: CitationDetail[];
  sources_used?: any[];
  isStreaming?: boolean;
  cached?: boolean;
  cacheSimilarity?: number;
}

interface ConversationItem {
  id: string;
  title: string;
  summary_memory?: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

interface RAGChatConsoleProps {
  authToken: string | null;
  apiBase: string;
  documents?: any[];
}

export default function RAGChatConsole({ authToken, apiBase, documents = [] }: RAGChatConsoleProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello! I am your AI Research Assistant. Ask me any question grounded in your ingested research papers and documents.',
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'rerank' | 'hybrid' | 'vector'>('rerank');
  const [isGenerating, setIsGenerating] = useState(false);

  // Stage 5 State: Active Conversation & Memory
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeSummaryMemory, setActiveSummaryMemory] = useState<string | null>(null);
  const [isMemoryDrawerOpen, setIsMemoryDrawerOpen] = useState(false);
  const [isSessionDropdownOpen, setIsSessionDropdownOpen] = useState(false);

  // Stage 5 State: Comparison Modal
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

  // Citation Drawer State
  const [selectedCitation, setSelectedCitation] = useState<CitationDetail | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Fetch all conversations on mount
  const fetchConversations = async () => {
    if (!authToken) return;
    try {
      const res = await fetch(`${apiBase}/api/v1/conversations/`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data: ConversationItem[] = await res.json();
        setConversations(data);
        if (data.length > 0 && !activeConversationId) {
          // Select most recent conversation
          loadConversation(data[0].id);
        }
      }
    } catch (e) {
      console.error('Error fetching conversations:', e);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [authToken]);

  // Load specific conversation and its persisted messages
  const loadConversation = async (convId: string) => {
    if (!authToken) return;
    try {
      const res = await fetch(`${apiBase}/api/v1/conversations/${convId}`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const detail = await res.json();
        setActiveConversationId(detail.id);
        setActiveSummaryMemory(detail.summary_memory || null);

        if (detail.messages && detail.messages.length > 0) {
          const loadedMsgs: ChatMessage[] = detail.messages.map((m: any) => ({
            id: m.id,
            sender: m.role.toLowerCase() === 'user' ? 'user' : 'assistant',
            text: m.content,
            citations: m.citations || [],
          }));
          setMessages(loadedMsgs);
        } else {
          setMessages([
            {
              id: 'welcome',
              sender: 'assistant',
              text: 'Hello! I am your AI Research Assistant. Ask me any question grounded in your ingested research papers.',
            },
          ]);
        }
      }
    } catch (e) {
      console.error('Error loading conversation:', e);
    }
  };

  // Start brand new conversation
  const handleNewConversation = async () => {
    if (!authToken) return;
    try {
      const res = await fetch(`${apiBase}/api/v1/conversations/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: 'New Research Session' }),
      });
      if (res.ok) {
        const newConv = await res.json();
        setActiveConversationId(newConv.id);
        setActiveSummaryMemory(null);
        setMessages([
          {
            id: 'welcome',
            sender: 'assistant',
            text: 'Hello! New research session created. Ask me any question grounded in your ingested papers.',
          },
        ]);
        await fetchConversations();
      }
    } catch (e) {
      console.error('Error creating new conversation:', e);
    }
  };

  // Delete a conversation
  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!authToken || !confirm('Delete this conversation session?')) return;
    try {
      const res = await fetch(`${apiBase}/api/v1/conversations/${convId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        if (activeConversationId === convId) {
          setActiveConversationId(null);
          setActiveSummaryMemory(null);
          setMessages([
            {
              id: 'welcome',
              sender: 'assistant',
              text: 'Conversation deleted. Ask any question to begin a new research session.',
            },
          ]);
        }
        await fetchConversations();
      }
    } catch (e) {
      console.error('Error deleting conversation:', e);
    }
  };

  const handleCitationClick = (citation: CitationDetail) => {
    setSelectedCitation(citation);
    setIsDrawerOpen(true);
  };

  // Inline citations renderer
  const renderInlineCitations = (text: string, citations: CitationDetail[]) => {
    if (!text) return null;
    const parts = text.split(/(\[\d+(?:\s*,\s*\d+)*\])/g);

    return parts.map((part, idx) => {
      const match = part.match(/^\[(\d+(?:\s*,\s*\d+)*)\]$/);
      if (match) {
        const ids = match[1].split(',').map((s) => parseInt(s.trim()));
        return (
          <span key={idx} className="inline-flex items-center gap-1 mx-1">
            {ids.map((idVal) => {
              const citObj = citations.find((c) => c.citation_id === idVal) || {
                citation_id: idVal,
              };
              const titleTooltip = citObj.filename
                ? `Source [${idVal}]: ${citObj.filename} (Page ${citObj.page_number || 1})`
                : `Click to inspect source [${idVal}]`;

              return (
                <button
                  key={idVal}
                  onClick={() => handleCitationClick(citObj)}
                  className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-mono font-bold bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 hover:bg-indigo-600 hover:text-white transition-all shadow-sm cursor-pointer hover:scale-105"
                  title={titleTooltip}
                >
                  [{idVal}]
                </button>
              );
            })}
          </span>
        );
      }

      // Simple Markdown Bold Parser (**text**)
      const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
      return (
        <span key={idx}>
          {boldParts.map((bPart, bIdx) => {
            if (bPart.startsWith('**') && bPart.endsWith('**')) {
              return (
                <strong key={bIdx} className="font-semibold text-slate-100">
                  {bPart.slice(2, -2)}
                </strong>
              );
            }
            return bPart;
          })}
        </span>
      );
    });
  };

  // Structured Markdown Blocks Formatter
  const renderFormattedMarkdown = (fullText: string, citations: CitationDetail[] = []) => {
    if (!fullText) return null;

    const lines = fullText.split('\n');
    const elements: React.ReactNode[] = [];

    let currentList: React.ReactNode[] = [];
    let currentTableRows: string[][] = [];

    const flushList = () => {
      if (currentList.length > 0) {
        elements.push(
          <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-1.5 my-2 pl-2 text-slate-300">
            {currentList}
          </ul>
        );
        currentList = [];
      }
    };

    const flushTable = () => {
      if (currentTableRows.length > 0) {
        const headerRow = currentTableRows[0];
        const bodyRows = currentTableRows.slice(1).filter((r) => !r[0]?.startsWith('---'));

        elements.push(
          <div key={`table-${elements.length}`} className="my-4 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60 p-1">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-900 border-b border-slate-800 text-slate-200">
                  {headerRow.map((cell, cIdx) => (
                    <th key={cIdx} className="px-3.5 py-2.5 font-bold uppercase tracking-wider text-[11px] text-indigo-400">
                      {renderInlineCitations(cell.trim(), citations)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {bodyRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-900/40 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3.5 py-2 leading-relaxed">
                        {renderInlineCitations(cell.trim(), citations)}
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
        flushList();
        const cells = trimmed.split('|').slice(1, -1);
        currentTableRows.push(cells);
        continue;
      } else {
        flushTable();
      }

      if (trimmed === '---') {
        flushList();
        elements.push(<hr key={`hr-${i}`} className="border-slate-800 my-4" />);
        continue;
      }

      if (trimmed.startsWith('### ')) {
        flushList();
        elements.push(
          <h3 key={`h3-${i}`} className="text-sm font-bold text-slate-100 mt-4 mb-2 flex items-center gap-2 border-b border-slate-800/60 pb-1">
            <span className="h-2 w-2 rounded-full bg-indigo-500" />
            {renderInlineCitations(trimmed.slice(4), citations)}
          </h3>
        );
        continue;
      }
      if (trimmed.startsWith('## ')) {
        flushList();
        elements.push(
          <h2 key={`h2-${i}`} className="text-base font-bold text-white mt-5 mb-2">
            {renderInlineCitations(trimmed.slice(3), citations)}
          </h2>
        );
        continue;
      }
      if (trimmed.startsWith('# ')) {
        flushList();
        elements.push(
          <h1 key={`h1-${i}`} className="text-lg font-bold text-white mt-6 mb-3">
            {renderInlineCitations(trimmed.slice(2), citations)}
          </h1>
        );
        continue;
      }

      const bulletMatch = trimmed.match(/^[\*\-\•]\s+(.*)/) || trimmed.match(/^\d+\.\s+(.*)/);
      if (bulletMatch) {
        currentList.push(
          <li key={`li-${i}`} className="leading-relaxed">
            {renderInlineCitations(bulletMatch[1], citations)}
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
        <p key={`p-${i}`} className="leading-relaxed my-1">
          {renderInlineCitations(trimmed, citations)}
        </p>
      );
    }

    flushList();
    flushTable();

    return <div className="space-y-1">{elements}</div>;
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || !authToken || isGenerating) return;

    const userText = inputQuery.trim();
    setInputQuery('');

    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', text: userText },
      { id: assistantMsgId, sender: 'assistant', text: '', isStreaming: true, citations: [] },
    ]);

    setIsGenerating(true);

    try {
      const response = await fetch(`${apiBase}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userText,
          search_mode: searchMode,
          top_k: 5,
          temperature: 0.2,
          conversation_id: activeConversationId,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Streaming connection failed');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let streamedText = '';
      let parsedCitations: CitationDetail[] = [];
      let sourcesUsed: any[] = [];
      let isCached = false;
      let cacheSimilarity: number | undefined = undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunkStr = decoder.decode(value, { stream: true });
        const lines = chunkStr.split('\n\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.replace('data: ', '').trim();

          if (payload.startsWith('[CITATION_DATA]')) {
            const rawMeta = payload.replace('[CITATION_DATA]', '');
            try {
              const metaObj = JSON.parse(rawMeta);
              parsedCitations = metaObj.citations || [];
              sourcesUsed = metaObj.sources_used || [];
              if (metaObj.cached) {
                isCached = true;
                cacheSimilarity = metaObj.cache_similarity;
              }
              if (metaObj.conversation_id) {
                setActiveConversationId(metaObj.conversation_id);
              }
              if (metaObj.summary_memory) {
                setActiveSummaryMemory(metaObj.summary_memory);
              }
            } catch (e) {
              console.error('Error parsing citation metadata frame:', e);
            }
          } else {
            try {
              const tokObj = JSON.parse(payload);
              if (tokObj.token) {
                streamedText += tokObj.token;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsgId
                      ? { ...msg, text: streamedText }
                      : msg
                  )
                );
              }
            } catch (e) {
              // Ignore non-JSON frames
            }
          }
        }
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                text: streamedText,
                isStreaming: false,
                citations: parsedCitations,
                sources_used: sourcesUsed,
                cached: isCached,
                cacheSimilarity: cacheSimilarity,
              }
            : msg
        )
      );

      // Refresh conversations list in background to update message counts & title
      fetchConversations();
    } catch (err) {
      console.error('Streaming Chat Error:', err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                text: 'An error occurred while streaming the AI response. Please ensure your backend is running.',
                isStreaming: false,
              }
            : msg
        )
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Session Controls */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Bot className="h-5 w-5 text-indigo-400" />
                Grounded RAG AI Research Studio
              </h2>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-600/20 text-indigo-300 border border-indigo-500/30">
                STAGE 5
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Ask questions across all ingested PDF/DOCX papers. Answers are strictly grounded with inline bracket citations <span className="text-indigo-400 font-mono font-semibold">[1]</span>.
            </p>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center flex-wrap gap-2">
            {/* Conversation Session Switcher */}
            <div className="relative">
              <button
                onClick={() => setIsSessionDropdownOpen(!isSessionDropdownOpen)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 hover:text-white transition-all shadow-sm"
              >
                <History className="h-3.5 w-3.5 text-indigo-400" />
                <span className="max-w-[120px] truncate">
                  {conversations.find((c) => c.id === activeConversationId)?.title || 'Sessions'}
                </span>
                <ChevronDown className="h-3 w-3 text-slate-500" />
              </button>

              {isSessionDropdownOpen && (
                <div className="absolute right-0 mt-2 w-72 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-2 z-30 space-y-1">
                  <div className="flex items-center justify-between px-2 py-1.5 border-b border-slate-800/80">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Research Sessions
                    </span>
                    <button
                      onClick={() => {
                        handleNewConversation();
                        setIsSessionDropdownOpen(false);
                      }}
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300"
                    >
                      <Plus className="h-3 w-3" /> New
                    </button>
                  </div>

                  <div className="max-h-56 overflow-y-auto space-y-1">
                    {conversations.length === 0 ? (
                      <p className="text-xs text-slate-500 p-2">No saved sessions yet.</p>
                    ) : (
                      conversations.map((c) => (
                        <div
                          key={c.id}
                          onClick={() => {
                            loadConversation(c.id);
                            setIsSessionDropdownOpen(false);
                          }}
                          className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-colors ${
                            c.id === activeConversationId
                              ? 'bg-indigo-600/20 text-indigo-200 border border-indigo-500/30'
                              : 'text-slate-300 hover:bg-slate-800/60'
                          }`}
                        >
                          <span className="truncate flex-1">{c.title}</span>
                          <button
                            onClick={(e) => handleDeleteConversation(c.id, e)}
                            className="p-1 text-slate-500 hover:text-rose-400 rounded transition-colors ml-2 shrink-0"
                            title="Delete session"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Running Memory Indicator Badge */}
            {activeSummaryMemory && (
              <button
                onClick={() => setIsMemoryDrawerOpen(!isMemoryDrawerOpen)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-purple-950/40 text-purple-300 border border-purple-800/50 text-xs font-semibold hover:bg-purple-900/50 transition-all shadow-sm"
                title="Click to view long-term summarized memory"
              >
                <BrainCircuit className="h-3.5 w-3.5 text-purple-400 animate-pulse" />
                <span>Memory Active</span>
              </button>
            )}

            {/* Compare Papers (Map-Reduce) Studio Button */}
            <button
              onClick={() => setIsCompareModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/20 transition-all"
            >
              <Scale className="h-3.5 w-3.5" /> Compare Papers
            </button>

            {/* Search Mode Toggles */}
            <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
              <button
                onClick={() => setSearchMode('rerank')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg font-semibold transition-all ${
                  searchMode === 'rerank'
                    ? 'bg-emerald-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Cpu className="h-3 w-3" /> Rerank
              </button>
              <button
                onClick={() => setSearchMode('hybrid')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg font-semibold transition-all ${
                  searchMode === 'hybrid'
                    ? 'bg-pink-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sliders className="h-3 w-3" /> Hybrid
              </button>
              <button
                onClick={() => setSearchMode('vector')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg font-semibold transition-all ${
                  searchMode === 'vector'
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Sparkles className="h-3 w-3" /> Vector
              </button>
            </div>
          </div>
        </div>

        {/* Expandable Memory Preview Banner */}
        {isMemoryDrawerOpen && activeSummaryMemory && (
          <div className="p-4 rounded-xl bg-purple-950/20 border border-purple-800/40 text-xs text-purple-200 space-y-2">
            <div className="flex items-center justify-between font-bold text-[11px] uppercase tracking-wider text-purple-400">
              <span className="flex items-center gap-1.5">
                <BrainCircuit className="h-3.5 w-3.5" />
                Long-Term Conversation Memory (Running Summary of Older Turns)
              </span>
              <button
                onClick={() => setIsMemoryDrawerOpen(false)}
                className="text-purple-400 hover:text-white"
              >
                Close
              </button>
            </div>
            <p className="leading-relaxed text-purple-200/90 font-mono text-[11px]">
              {activeSummaryMemory}
            </p>
          </div>
        )}
      </div>

      {/* Chat Messages Timeline */}
      <div className="bg-slate-900/60 rounded-2xl border border-slate-800 h-[560px] flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start gap-3.5 ${
                msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'
              }`}
            >
              <div
                className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 font-bold text-xs ${
                  msg.sender === 'user'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'bg-slate-800 text-indigo-400 border border-slate-700'
                }`}
              >
                {msg.sender === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>

              <div
                className={`max-w-3xl rounded-2xl px-5 py-4 text-xs leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-indigo-600 text-white rounded-tr-none shadow-lg'
                    : 'bg-slate-950/90 text-slate-200 border border-slate-800 rounded-tl-none space-y-3'
                }`}
              >
                {msg.sender === 'assistant' && msg.cached && (
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-semibold mb-1 shadow-sm">
                    <Zap className="h-3 w-3 text-emerald-400 fill-emerald-400" />
                    <span>
                      Semantic Cache Hit {msg.cacheSimilarity ? `(${(msg.cacheSimilarity * 100).toFixed(1)}% match)` : '(<10ms)'}
                    </span>
                  </div>
                )}
                <div>
                  {msg.sender === 'user' ? (
                    msg.text
                  ) : (
                    renderFormattedMarkdown(msg.text, msg.citations)
                  )}
                  {msg.isStreaming && (
                    <span className="inline-block w-2 h-4 bg-indigo-400 ml-1 animate-pulse align-middle" />
                  )}
                </div>

                {/* Grounded Citation Sources Footer */}
                {msg.sender === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <div className="pt-3 border-t border-slate-800/80 space-y-2">
                    <span className="text-[11px] font-bold text-slate-400 flex items-center gap-1">
                      <BookOpen className="h-3 w-3 text-indigo-400" /> Grounded Source Citations:
                    </span>
                    <div className="flex flex-wrap items-center gap-2">
                      {msg.citations.map((c) => (
                        <button
                          key={c.citation_id}
                          onClick={() => handleCitationClick(c)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-slate-900 text-indigo-300 border border-indigo-800/50 hover:bg-indigo-900/50 hover:text-white transition-all shadow-sm"
                        >
                          <span className="font-mono text-indigo-400 font-bold">[{c.citation_id}]</span>
                          <span className="font-semibold text-slate-200">
                            {c.filename ? (c.filename.length > 22 ? c.filename.slice(0, 20) + '...' : c.filename) : 'Source'}
                          </span>
                          <span className="text-slate-400 border-l border-slate-800 pl-1.5 text-[10px]">
                            {c.section && c.section !== 'Section Overview' ? c.section.slice(0, 18) : `p. ${c.page_number || 1}`}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSendMessage} className="p-4 bg-slate-950 border-t border-slate-800 flex items-center gap-3">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Ask any research question grounded in your documents..."
            disabled={isGenerating}
            className="flex-1 bg-slate-900/90 border border-slate-800 rounded-xl px-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <button
            type="submit"
            disabled={isGenerating || !inputQuery.trim()}
            className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs transition-all shadow-md shadow-indigo-600/30 flex items-center gap-2 shrink-0"
          >
            {isGenerating ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" /> Thinking...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" /> Ask RAG AI
              </>
            )}
          </button>
        </form>
      </div>

      {/* Slide-over Source Inspector Drawer */}
      <SourceInspectorDrawer
        citation={selectedCitation}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />

      {/* Multi-Doc Map-Reduce Compare Modal */}
      <MultiDocCompareModal
        isOpen={isCompareModalOpen}
        onClose={() => setIsCompareModalOpen(false)}
        documents={documents}
        authToken={authToken}
        apiBase={apiBase}
      />
    </div>
  );
}
