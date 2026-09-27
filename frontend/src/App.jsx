import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import DocumentManager from './components/DocumentManager';
import RetrievalTuner from './components/RetrievalTuner';
import InterviewPrepModal from './components/InterviewPrepModal';
import SourceModal from './components/SourceModal';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [health, setHealth] = useState(null);
  const [loadingChat, setLoadingChat] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const [showInterviewPrep, setShowInterviewPrep] = useState(false);

  // Initial load
  useEffect(() => {
    loadHealth();
    loadDocuments();
    loadConversations();
  }, []);

  const loadHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (e) {
      console.error("Health check error:", e);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (e) {
      console.error("Error fetching documents:", e);
    }
  };

  const loadConversations = async () => {
    try {
      const data = await api.getConversations();
      setConversations(data);
      if (data.length > 0 && !activeConvId) {
        selectConversation(data[0].id);
      }
    } catch (e) {
      console.error("Error fetching conversations:", e);
    }
  };

  const selectConversation = async (convId) => {
    setActiveConvId(convId);
    try {
      const data = await api.getConversation(convId);
      setMessages(data.messages || []);
    } catch (e) {
      console.error("Error fetching conversation history:", e);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation("New Conversation");
      setConversations([newConv, ...conversations]);
      setActiveConvId(newConv.id);
      setMessages([]);
      setActiveTab('chat');
    } catch (e) {
      console.error("Error creating conversation:", e);
    }
  };

  const handleDeleteConversation = async (convId) => {
    try {
      await api.deleteConversation(convId);
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);
      if (activeConvId === convId) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          setActiveConvId(null);
          setMessages([]);
        }
      }
    } catch (e) {
      console.error("Error deleting conversation:", e);
    }
  };

  const handleSendMessage = async ({ message, retrieval_strategy, top_k, similarity_threshold }) => {
    // Add user message optimistically
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: message,
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setLoadingChat(true);

    try {
      const res = await api.sendMessage({
        conversation_id: activeConvId,
        message,
        retrieval_strategy,
        top_k,
        similarity_threshold,
      });

      if (!activeConvId) {
        setActiveConvId(res.conversation_id);
        loadConversations();
      }

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        { role: 'user', content: message },
        res.message,
      ]);
    } catch (e) {
      alert("Chat error: " + e.message);
    } finally {
      setLoadingChat(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        conversations={conversations}
        activeConvId={activeConvId}
        onSelectConversation={selectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onOpenInterviewPrep={() => setShowInterviewPrep(true)}
        health={health}
        docCount={documents.length}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {activeTab === 'chat' && (
          <ChatInterface
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={loadingChat}
            onSelectSource={(source) => setSelectedSource(source)}
            documentsCount={documents.length}
            onNavigateToDocs={() => setActiveTab('documents')}
          />
        )}

        {activeTab === 'documents' && (
          <div className="flex-1 overflow-y-auto">
            <DocumentManager
              documents={documents}
              onRefresh={loadDocuments}
              onSelectSource={(source) => setSelectedSource(source)}
            />
          </div>
        )}

        {activeTab === 'retrieval' && (
          <div className="flex-1 overflow-y-auto">
            <RetrievalTuner
              onSelectSource={(source) => setSelectedSource(source)}
            />
          </div>
        )}
      </main>

      {/* Modals */}
      {selectedSource && (
        <SourceModal
          source={selectedSource}
          onClose={() => setSelectedSource(null)}
        />
      )}

      {showInterviewPrep && (
        <InterviewPrepModal
          onClose={() => setShowInterviewPrep(false)}
        />
      )}
    </div>
  );
}
