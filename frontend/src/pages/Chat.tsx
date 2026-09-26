import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { 
  MessageSquare, 
  Send, 
  Sparkles, 
  Plus, 
  Trash2, 
  FileText, 
  BookOpen, 
  AlertTriangle, 
  ShieldCheck, 
  Loader2, 
  Copy, 
  Check, 
  Info,
  Filter,
  ChevronDown,
  X,
  Layers
} from "lucide-react";
import { api } from "../services/api";
import type { ConversationItem, MessageItem, DocumentItem } from "../types";
import { formatTimeOnly } from "../utils/date";

export const Chat: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialPrompt = searchParams.get("prompt");

  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Document Selection Filter State
  const [availableDocuments, setAvailableDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [isDocSelectorOpen, setIsDocSelectorOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDocSelectorOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Fetch available documents for the selector
  const fetchDocs = async () => {
    try {
      const docs = await api.getDocuments();
      setAvailableDocuments(docs.filter((d) => d.status === "completed"));
    } catch (err) {
      console.error("Failed to load documents for selector:", err);
    }
  };

  // Load conversations list
  const fetchConversations = async () => {
    try {
      setLoadingConversations(true);
      const data = await api.getConversations();
      setConversations(data);
      if (data.length > 0 && !activeConversationId) {
        loadConversation(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoadingConversations(false);
    }
  };

  useEffect(() => {
    fetchConversations();
    fetchDocs();
  }, []);

  // Handle URL query parameter prompt
  useEffect(() => {
    if (initialPrompt) {
      setInputQuestion(initialPrompt);
    }
  }, [initialPrompt]);

  const loadConversation = async (id: number) => {
    setActiveConversationId(id);
    try {
      const conv = await api.getConversationHistory(id);
      setMessages(conv.messages || []);
    } catch (err) {
      console.error("Failed to load conversation history:", err);
    }
  };

  const handleNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setInputQuestion("");
    inputRef.current?.focus();
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        handleNewConversation();
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const question = inputQuestion.trim();
    if (!question || loading) return;

    // Optimistic user message
    const tempUserMsg: MessageItem = {
      id: Date.now(),
      conversation_id: activeConversationId || 0,
      role: "user",
      content: question,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setInputQuestion("");
    setLoading(true);

    try {
      const response = await api.sendMessage({
        question,
        conversation_id: activeConversationId || undefined,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      });

      const assistantMsg: MessageItem = {
        id: response.message_id,
        conversation_id: response.conversation_id,
        role: "assistant",
        content: response.answer,
        created_at: new Date().toISOString(),
        sources: response.sources,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setActiveConversationId(response.conversation_id);

      // Refresh conversations list to update titles
      fetchConversations();
    } catch (err: any) {
      console.error("Chat error:", err);
      const errMsg = err?.response?.data?.detail || "Could not retrieve response from AI engine. Please verify the backend service is running.";
      const errorMsg: MessageItem = {
        id: Date.now() + 1,
        conversation_id: activeConversationId || 0,
        role: "assistant",
        content: `Error: ${errMsg}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const sampleQuestions = [
    "Compare gross revenue and R&D outlook between 2024 and 2025.",
    "What was the operating profit margin in fiscal year 2025?",
    "What are our rest encryption standards and MFA policies?",
    "What is the secret recipe for Martian chocolate cake?",
  ];

  return (
    <div className="flex h-[calc(100vh-6.5rem)] rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
      {/* Conversations History Sidebar */}
      <div className="w-72 border-r border-slate-200 bg-slate-50/80 flex flex-col justify-between hidden md:flex">
        <div className="p-4 space-y-3">
          <button
            onClick={handleNewConversation}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm shadow-cyan-600/20 hover:from-cyan-500 hover:to-blue-500 transition-all cursor-pointer"
          >
            <Plus className="h-4 w-4" />
            <span>New Conversation</span>
          </button>

          <div className="space-y-1 overflow-y-auto max-h-[calc(100vh-14rem)] pr-1">
            <p className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 py-1">
              Recent Sessions
            </p>
            {loadingConversations ? (
              <div className="py-4 text-center text-xs text-slate-400">Loading history...</div>
            ) : conversations.length === 0 ? (
              <div className="py-4 text-center text-xs text-slate-400">No previous sessions</div>
            ) : (
              conversations.map((c) => (
                <div
                  key={c.id}
                  onClick={() => loadConversation(c.id)}
                  className={`group flex items-center justify-between rounded-lg px-3 py-2.5 text-xs font-medium cursor-pointer transition-colors ${
                    activeConversationId === c.id
                      ? "bg-cyan-100/70 text-cyan-900 border border-cyan-300 font-bold"
                      : "text-slate-600 hover:bg-slate-200/60 hover:text-slate-900"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate max-w-[170px]">
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 text-slate-400 group-hover:text-cyan-700" />
                    <span className="truncate">{c.title}</span>
                  </div>
                  <button
                    onClick={(e) => handleDeleteConversation(c.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 transition-opacity"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Grounding Info Footer */}
        <div className="p-3 border-t border-slate-200 bg-white text-[10px] text-slate-500 flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
          <span>Grounded RAG: citations & zero hallucination</span>
        </div>
      </div>

      {/* Main Chat Conversation Column */}
      <div className="flex-1 flex flex-col justify-between bg-slate-50/30">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-6 py-12">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-600 to-indigo-600 shadow-md shadow-cyan-600/20 text-white">
                <Sparkles className="h-8 w-8" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-slate-900">Ask Anything Across Your Documents</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
                  DocuMind uses dense vector retrieval with Sentence Transformers and Google Gemini to provide factual answers with exact real-time page citations.
                </p>
              </div>

              {/* Preset Sample Prompts */}
              <div className="w-full space-y-2">
                <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                  Try asking:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                  {sampleQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInputQuestion(q);
                        inputRef.current?.focus();
                      }}
                      className="rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-700 hover:border-cyan-400 hover:text-cyan-800 hover:bg-cyan-50/40 transition-all text-left shadow-xs cursor-pointer"
                    >
                      <span className="line-clamp-2 italic">"{q}"</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((msg, index) => {
              const isUser = msg.role === "user";
              const isInsufficient = msg.content.toLowerCase().includes("insufficient evidence");
              const isConflict = msg.content.toLowerCase().includes("conflict identified");

              return (
                <div
                  key={msg.id || index}
                  className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-2`}
                >
                  <div className="flex items-center gap-2 px-1 text-[11px] text-slate-500 font-medium">
                    {isUser ? (
                      <span className="font-semibold text-slate-700">You</span>
                    ) : (
                      <span className="flex items-center gap-1.5 text-cyan-800 font-bold">
                        <Sparkles className="h-3 w-3 text-cyan-600" />
                        DocuMind Intelligence
                      </span>
                    )}
                    <span>·</span>
                    <span title={new Date(msg.created_at).toLocaleString()}>{formatTimeOnly(msg.created_at)}</span>
                  </div>

                  <div
                    className={`relative rounded-2xl px-5 py-4 max-w-3xl text-xs sm:text-sm leading-relaxed shadow-sm ${
                      isUser
                        ? "bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-br-none"
                        : "bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-xs"
                    }`}
                  >
                    {/* Insufficient Evidence Warning Banner */}
                    {!isUser && isInsufficient && (
                      <div className="mb-3 flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 p-2.5 text-xs text-amber-800">
                        <Info className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
                        <span><strong>Strict Grounding Notice:</strong> The requested information was not found in your {selectedDocIds.length > 0 ? "selected documents" : "uploaded documents"}. DocuMind refuses to hallucinate external facts.</span>
                      </div>
                    )}

                    {/* Conflict Detected Banner */}
                    {!isUser && isConflict && (
                      <div className="mb-3 flex items-start gap-2 rounded-lg bg-rose-50 border border-rose-200 p-2.5 text-xs text-rose-800">
                        <AlertTriangle className="h-4 w-4 shrink-0 text-rose-600 mt-0.5" />
                        <span><strong>Contradiction Detected:</strong> Conflicting statements or figures were identified across documents.</span>
                      </div>
                    )}

                    {/* Message Body */}
                    <div className="whitespace-pre-wrap font-sans">{msg.content}</div>

                    {/* Copy Button */}
                    {!isUser && (
                      <button
                        onClick={() => handleCopy(msg.content, index)}
                        className="mt-3 inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800 cursor-pointer"
                      >
                        {copiedIndex === index ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-600" />
                            <span className="text-emerald-700 font-medium">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Copy response</span>
                          </>
                        )}
                      </button>
                    )}

                    {/* Grounded Source Citations */}
                    {!isUser && msg.sources && msg.sources.length > 0 && !isInsufficient && (
                      <div className="mt-4 pt-3 border-t border-slate-200 space-y-2">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                          <BookOpen className="h-3.5 w-3.5 text-cyan-600" />
                          <span>Grounded Source Citations ({msg.sources.length})</span>
                        </p>
                        <div className="grid grid-cols-1 gap-2 pt-1">
                          {msg.sources.map((src, sIdx) => (
                            <div
                              key={sIdx}
                              className="rounded-xl border border-slate-200 bg-slate-50 p-3 space-y-1.5 text-left"
                            >
                              <div className="flex items-center justify-between text-xs">
                                <div className="flex items-center gap-2 font-bold text-slate-800 truncate max-w-[280px]">
                                  <FileText className="h-3.5 w-3.5 text-cyan-600 shrink-0" />
                                  <span className="truncate">{src.document_name}</span>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  <span className="rounded-md bg-cyan-100 border border-cyan-200 px-2 py-0.5 text-[10px] font-bold text-cyan-800">
                                    Page {src.page_number}
                                  </span>
                                  {src.relevance_score && (
                                    <span className="rounded-md bg-white border border-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                                      {(src.relevance_score * 100).toFixed(0)}% match
                                    </span>
                                  )}
                                </div>
                              </div>
                              <p className="text-[11px] text-slate-600 italic line-clamp-3 bg-white p-2 rounded-lg border border-slate-200">
                                "{src.evidence_snippet}"
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Assistant Loading Indicator */}
          {loading && (
            <div className="flex flex-col items-start space-y-2">
              <div className="flex items-center gap-2 px-1 text-[11px] text-cyan-700 font-semibold">
                <Sparkles className="h-3 w-3 animate-spin" />
                <span>Searching ChromaDB & synthesizing with Gemini...</span>
              </div>
              <div className="rounded-2xl rounded-bl-none border border-slate-200 bg-white px-5 py-4 text-xs text-slate-600 flex items-center gap-3 shadow-xs">
                <Loader2 className="h-4 w-4 animate-spin text-cyan-600" />
                <span>Retrieving semantic chunks and verifying page citations...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Document Selection & Input Bar */}
        <div className="border-t border-slate-200 bg-white p-4 space-y-3">
          <div className="max-w-4xl mx-auto space-y-2">
            {/* Document Selector Header */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <Filter className="h-3.5 w-3.5 text-cyan-600" />
                  Search in:
                </span>
                <div className="relative" ref={dropdownRef}>
                  <button
                    type="button"
                    onClick={() => setIsDocSelectorOpen((prev) => !prev)}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-800 transition-colors shadow-xs cursor-pointer"
                  >
                    <span>
                      {selectedDocIds.length === 0
                        ? "All Documents"
                        : selectedDocIds.length === 1
                        ? availableDocuments.find((d) => d.id === selectedDocIds[0])?.filename || "1 Document Selected"
                        : `${selectedDocIds.length} Documents Selected`}
                    </span>
                    <ChevronDown className={`h-3.5 w-3.5 text-slate-500 transition-transform ${isDocSelectorOpen ? "rotate-180" : ""}`} />
                  </button>

                  {/* Dropdown Menu */}
                  {isDocSelectorOpen && (
                    <div className="absolute bottom-full left-0 mb-2 w-72 max-h-60 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl z-30 space-y-1">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedDocIds([]);
                          setIsDocSelectorOpen(false);
                        }}
                        className={`w-full flex items-center justify-between rounded-lg px-3 py-2 text-left text-xs font-medium transition-colors cursor-pointer ${
                          selectedDocIds.length === 0
                            ? "bg-cyan-50 text-cyan-800 font-bold border border-cyan-200"
                            : "text-slate-700 hover:bg-slate-100"
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <Layers className="h-3.5 w-3.5 text-cyan-600" />
                          All Documents (Default)
                        </span>
                        {selectedDocIds.length === 0 && <Check className="h-3.5 w-3.5 text-cyan-700" />}
                      </button>

                      <div className="border-t border-slate-100 my-1 pt-1">
                        <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                          Uploaded Documents
                        </p>
                        {availableDocuments.length === 0 ? (
                          <p className="px-3 py-2 text-xs text-slate-400 italic">No documents uploaded</p>
                        ) : (
                          availableDocuments.map((doc) => {
                            const isSelected = selectedDocIds.includes(doc.id);
                            return (
                              <button
                                key={doc.id}
                                type="button"
                                onClick={() => {
                                  setSelectedDocIds((prev) => {
                                    if (prev.includes(doc.id)) {
                                      return prev.filter((id) => id !== doc.id);
                                    } else {
                                      return [...prev, doc.id];
                                    }
                                  });
                                }}
                                className={`w-full flex items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors cursor-pointer ${
                                  isSelected
                                    ? "bg-cyan-50 text-cyan-900 font-semibold"
                                    : "text-slate-700 hover:bg-slate-100"
                                }`}
                              >
                                <span className="truncate max-w-[200px] flex items-center gap-2">
                                  <FileText className="h-3.5 w-3.5 text-cyan-600 shrink-0" />
                                  <span className="truncate">{doc.filename}</span>
                                </span>
                                <span className={`h-4 w-4 rounded flex items-center justify-center border text-[10px] ${
                                  isSelected ? "bg-cyan-600 border-cyan-600 text-white" : "border-slate-300"
                                }`}>
                                  {isSelected && <Check className="h-3 w-3" />}
                                </span>
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {selectedDocIds.length > 0 && (
                <button
                  type="button"
                  onClick={() => setSelectedDocIds([])}
                  className="text-[11px] font-medium text-cyan-700 hover:text-cyan-800 hover:underline cursor-pointer"
                >
                  Reset to All Documents
                </button>
              )}
            </div>

            {/* Selected Document Tags Pills */}
            {selectedDocIds.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-[11px] text-slate-500 font-medium">Selected:</span>
                {selectedDocIds.map((id) => {
                  const doc = availableDocuments.find((d) => d.id === id);
                  const name = doc?.filename || `Doc #${id}`;
                  return (
                    <span
                      key={id}
                      className="inline-flex items-center gap-1 rounded-md bg-cyan-50 border border-cyan-200 px-2 py-0.5 text-xs font-semibold text-cyan-900 shadow-2xs"
                    >
                      <FileText className="h-3 w-3 text-cyan-600 shrink-0" />
                      <span className="max-w-[180px] truncate">{name}</span>
                      <button
                        type="button"
                        onClick={() => setSelectedDocIds((prev) => prev.filter((docId) => docId !== id))}
                        className="rounded hover:bg-cyan-100 p-0.5 text-cyan-700 hover:text-rose-600 transition-colors cursor-pointer"
                        title="Remove document filter"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  );
                })}
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSendMessage} className="relative flex items-end gap-2 pt-1">
              <textarea
                ref={inputRef}
                rows={1}
                value={inputQuestion}
                onChange={(e) => setInputQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder={
                  selectedDocIds.length === 0
                    ? "Ask a question about your uploaded documents (e.g. Compare 2024 vs 2025 financials)..."
                    : selectedDocIds.length === 1
                    ? `Ask a question scoped only to ${availableDocuments.find(d => d.id === selectedDocIds[0])?.filename || 'selected document'}...`
                    : `Ask a question scoped only to ${selectedDocIds.length} selected documents...`
                }
                className="w-full resize-none rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-xs sm:text-sm text-slate-900 placeholder-slate-400 focus:border-cyan-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-colors"
              />
              <button
                type="submit"
                disabled={!inputQuestion.trim() || loading}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-sm shadow-cyan-600/20 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 transition-all cursor-pointer"
              >
                {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-4 w-4" />}
              </button>
            </form>
            <p className="text-center text-[10px] text-slate-400">
              Press Enter to send · Shift + Enter for new line · Strict grounding enforced
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
