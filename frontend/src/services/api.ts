import axios from "axios";
import type {
  AuthResponse,
  User,
  DocumentItem,
  DocumentStats,
  ConversationItem,
  ChatResponse,
  SearchResult,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: attach Bearer token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("documind_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 Unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token if expired or invalid
      localStorage.removeItem("documind_token");
      if (window.location.pathname !== "/login" && window.location.pathname !== "/signup") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Authentication
  register: async (data: { email: string; password: string; full_name?: string }): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>("/auth/register", data);
    return res.data;
  },
  login: async (data: { email: string; password: string }): Promise<AuthResponse> => {
    const res = await apiClient.post<AuthResponse>("/auth/login", data);
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await apiClient.get<User>("/auth/me");
    return res.data;
  },

  // Documents
  uploadDocument: async (
    file: File,
    onUploadProgress?: (progressEvent: any) => void
  ): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiClient.post<DocumentItem>("/documents/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress,
    });
    return res.data;
  },
  getDocuments: async (): Promise<DocumentItem[]> => {
    const res = await apiClient.get<DocumentItem[]>("/documents");
    return res.data;
  },
  getDocumentStats: async (): Promise<DocumentStats> => {
    const res = await apiClient.get<DocumentStats>("/documents/stats");
    return res.data;
  },
  getDocumentById: async (id: number): Promise<DocumentItem> => {
    const res = await apiClient.get<DocumentItem>(`/documents/${id}`);
    return res.data;
  },
  deleteDocument: async (id: number): Promise<{ message: string }> => {
    const res = await apiClient.delete<{ message: string }>(`/documents/${id}`);
    return res.data;
  },

  // Search
  search: async (query: string, top_k = 5, document_id?: number): Promise<SearchResult[]> => {
    const res = await apiClient.post<SearchResult[]>("/search", { query, top_k, document_id });
    return res.data;
  },

  // Chat & Conversations
  sendMessage: async (data: { question: string; conversation_id?: number; document_ids?: number[] }): Promise<ChatResponse> => {
    const res = await apiClient.post<ChatResponse>("/chat", data);
    return res.data;
  },
  getConversations: async (): Promise<ConversationItem[]> => {
    const res = await apiClient.get<ConversationItem[]>("/conversations");
    return res.data;
  },
  getConversationHistory: async (id: number): Promise<ConversationItem> => {
    const res = await apiClient.get<ConversationItem>(`/conversations/${id}`);
    return res.data;
  },
  deleteConversation: async (id: number): Promise<{ message: string }> => {
    const res = await apiClient.delete<{ message: string }>(`/conversations/${id}`);
    return res.data;
  },
};
