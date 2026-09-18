'use client';

import React, { useState, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import DocumentUploadZone from '@/components/DocumentUploadZone';
import SearchConsole from '@/components/SearchConsole';
import RAGChatConsole from '@/components/RAGChatConsole';
import FlashcardsConsole from '@/components/FlashcardsConsole';
import DocSummaryDrawer from '@/components/DocSummaryDrawer';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'documents' | 'search' | 'chat' | 'flashcards'>('chat');
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [summaryDoc, setSummaryDoc] = useState<{ id: string; filename: string } | null>(null);

  // Auto-authenticate & validate session token
  useEffect(() => {
    async function initAuth() {
      const storedToken = localStorage.getItem('auth_token');
      if (storedToken) {
        try {
          const checkRes = await fetch(`${API_BASE}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${storedToken}` },
          });
          if (checkRes.ok) {
            setAuthToken(storedToken);
            return;
          }
        } catch (e) {
          console.warn('Stored token invalid, re-authenticating...');
        }
        localStorage.removeItem('auth_token');
      }

      // Login / Register studio_user@ai.com
      try {
        const loginRes = await fetch(`${API_BASE}/api/v1/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: 'username=studio_user%40ai.com&password=password123',
        });
        if (loginRes.ok) {
          const loginData = await loginRes.json();
          setAuthToken(loginData.access_token);
          localStorage.setItem('auth_token', loginData.access_token);
          return;
        }

        // Register if user does not exist yet
        const regRes = await fetch(`${API_BASE}/api/v1/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'studio_user@ai.com',
            password: 'password123',
            full_name: 'Studio Researcher',
            workspace_name: 'Quantum AI Lab',
          }),
        });
        if (regRes.ok) {
          const regData = await regRes.json();
          setAuthToken(regData.access_token);
          localStorage.setItem('auth_token', regData.access_token);
        }
      } catch (err) {
        console.error('Auth Error:', err);
      }
    }
    initAuth();
  }, []);

  // Fetch document list
  const fetchDocuments = async () => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents/`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error('Fetch Documents Error:', err);
    }
  };

  useEffect(() => {
    if (authToken) {
      fetchDocuments();
    }
  }, [authToken]);

  // Handle Document Upload
  const handleUpload = async (file: File) => {
    if (!authToken) return;
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
        body: formData,
      });
      if (res.ok) {
        await fetchDocuments();
      }
    } catch (err) {
      console.error('Upload Error:', err);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle Document Deletion
  const handleDeleteDocument = async (documentId: string) => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents/${documentId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok || res.status === 204) {
        await fetchDocuments();
      }
    } catch (err) {
      console.error('Delete Document Error:', err);
    }
  };

  // Handle Search Execution
  const handleSearch = async (query: string, mode: 'vector' | 'keyword' | 'hybrid' | 'rerank') => {
    if (!authToken) return [];
    const endpoint = `${API_BASE}/api/v1/search/${mode}`;
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, top_k: 5 }),
    });
    if (res.ok) {
      return await res.json();
    }
    return [];
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white">
      {/* Header Navbar */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'documents' && (
          <DocumentUploadZone
            documents={documents}
            onUpload={handleUpload}
            onDelete={handleDeleteDocument}
            onOpenSummary={(id, filename) => setSummaryDoc({ id, filename })}
            onRefresh={fetchDocuments}
            isUploading={isUploading}
          />
        )}
        {activeTab === 'search' && (
          <SearchConsole onSearch={handleSearch} />
        )}
        {activeTab === 'chat' && (
          <RAGChatConsole authToken={authToken} apiBase={API_BASE} documents={documents} />
        )}
        {activeTab === 'flashcards' && (
          <FlashcardsConsole authToken={authToken} documents={documents} />
        )}
      </main>

      {/* Slide-over Executive Document Summary Drawer */}
      <DocSummaryDrawer
        documentId={summaryDoc?.id || null}
        filename={summaryDoc?.filename || null}
        isOpen={!!summaryDoc}
        onClose={() => setSummaryDoc(null)}
        authToken={authToken}
      />
    </div>
  );
}
