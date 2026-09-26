export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DocumentItem {
  id: number;
  user_id: number;
  filename: string;
  file_type: string;
  file_size: number;
  status: "uploaded" | "processing" | "completed" | "failed";
  error_message?: string;
  total_pages: number;
  total_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentStats {
  total_documents: number;
  processing_documents: number;
  completed_documents: number;
  failed_documents: number;
}

export interface SourceCitation {
  id?: number;
  document_id?: number;
  document_name: string;
  page_number: number;
  section?: string;
  evidence_snippet: string;
  relevance_score?: number;
}

export interface MessageItem {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  sources?: SourceCitation[];
}

export interface ConversationItem {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
  messages?: MessageItem[];
}

export interface ChatResponse {
  conversation_id: number;
  message_id: number;
  answer: string;
  sources: SourceCitation[];
  has_insufficient_evidence: boolean;
  has_conflicting_info: boolean;
}

export interface SearchResult {
  chunk_id: number;
  document_id: number;
  filename: string;
  page_number: number;
  section?: string;
  content: string;
  relevance_score: number;
}
