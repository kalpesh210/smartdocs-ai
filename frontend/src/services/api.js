const API_BASE = '/api/v1';

export const api = {
  // Health
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  // Documents
  async getDocuments() {
    const res = await fetch(`${API_BASE}/documents`);
    return res.json();
  },

  async getDocument(docId) {
    const res = await fetch(`${API_BASE}/documents/${docId}`);
    return res.json();
  },

  async uploadDocument(file, chunkSize, chunkOverlap) {
    const formData = new FormData();
    formData.append('file', file);
    let url = `${API_BASE}/documents/upload?sync_processing=true`;
    if (chunkSize) url += `&chunk_size=${chunkSize}`;
    if (chunkOverlap) url += `&chunk_overlap=${chunkOverlap}`;

    const res = await fetch(url, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  async deleteDocument(docId) {
    const res = await fetch(`${API_BASE}/documents/${docId}`, {
      method: 'DELETE',
    });
    return res.json();
  },

  // Chat
  async getConversations() {
    const res = await fetch(`${API_BASE}/chat/conversations`);
    return res.json();
  },

  async createConversation(title = 'New Chat') {
    const res = await fetch(`${API_BASE}/chat/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    return res.json();
  },

  async getConversation(convId) {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}`);
    return res.json();
  },

  async deleteConversation(convId) {
    const res = await fetch(`${API_BASE}/chat/conversations/${convId}`, {
      method: 'DELETE',
    });
    return res.json();
  },

  async sendMessage(data) {
    const res = await fetch(`${API_BASE}/chat/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to send message');
    }
    return res.json();
  },

  // Retrieval Tuning & Benchmarking
  async testRetrieval(params) {
    const res = await fetch(`${API_BASE}/retrieval/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return res.json();
  },

  async getBenchmarks() {
    const res = await fetch(`${API_BASE}/evaluation/benchmarks`);
    return res.json();
  }
};
