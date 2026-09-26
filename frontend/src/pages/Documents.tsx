import React, { useState, useEffect } from "react";
import { 
  Files, 
  Trash2, 
  Eye, 
  Search, 
  UploadCloud, 
  FileText, 
  AlertCircle,
  X,
  Database
} from "lucide-react";
import { api } from "../services/api";
import type { DocumentItem } from "../types";
import { formatDateTime } from "../utils/date";

export const Documents: React.FC<{ onOpenUpload: () => void }> = ({ onOpenUpload }) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);

  const fetchDocs = async () => {
    try {
      setLoading(true);
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleDelete = async (id: number, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}" and all its vector embeddings?`)) {
      return;
    }

    try {
      setDeletingId(id);
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selectedDoc?.id === id) setSelectedDoc(null);
    } catch (err) {
      console.error("Delete error:", err);
      alert("Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  };

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Files className="h-6 w-6 text-cyan-600" />
            Document Management
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage your knowledge store, examine indexed chunks, and inspect parsing statuses.
          </p>
        </div>

        <button
          onClick={onOpenUpload}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-cyan-600/20 hover:from-cyan-500 hover:to-blue-500 transition-all"
        >
          <UploadCloud className="h-4 w-4" />
          <span>Upload Document</span>
        </button>
      </div>

      {/* Search & Filter Bar */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
        <div className="relative max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search documents by filename..."
            className="w-full rounded-lg border border-slate-300 bg-slate-50 pl-9 pr-4 py-2 text-xs text-slate-900 placeholder-slate-400 focus:border-cyan-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-cyan-500 transition-colors"
          />
        </div>
      </div>

      {/* Documents Table */}
      <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm">
        {loading ? (
          <div className="py-16 text-center text-xs text-slate-500">Loading document catalog...</div>
        ) : filteredDocs.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
              <Files className="h-6 w-6" />
            </div>
            <p className="text-sm text-slate-800 font-bold">No documents found</p>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              {searchQuery ? "No documents match your search query." : "Upload a PDF, Scanned Image, or DOCX to start."}
            </p>
            {!searchQuery && (
              <button
                onClick={onOpenUpload}
                className="mt-2 inline-flex items-center gap-2 rounded-lg bg-white hover:bg-slate-50 px-4 py-2 text-xs font-semibold text-cyan-700 border border-slate-300 shadow-xs"
              >
                Upload now
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 uppercase tracking-wider text-[10px]">
                  <th className="py-3.5 px-6 font-bold">Document</th>
                  <th className="py-3.5 px-4 font-bold">File Type</th>
                  <th className="py-3.5 px-4 font-bold">Size</th>
                  <th className="py-3.5 px-4 font-bold">Status</th>
                  <th className="py-3.5 px-4 font-bold">Pages / Chunks</th>
                  <th className="py-3.5 px-4 font-bold">Uploaded (Real Time)</th>
                  <th className="py-3.5 px-6 font-bold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-4 px-6 font-medium text-slate-800 flex items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-cyan-700 border border-slate-200">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div className="truncate max-w-[240px]">
                        <p className="truncate font-bold text-slate-900">{doc.filename}</p>
                        <p className="text-[10px] text-slate-400">ID: #{doc.id}</p>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-slate-500 uppercase font-mono text-[11px]">
                      {doc.filename.split('.').pop() || "doc"}
                    </td>
                    <td className="py-4 px-4 text-slate-600 font-medium">
                      {(doc.file_size / (1024 * 1024)).toFixed(2)} MB
                    </td>
                    <td className="py-4 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                          doc.status === "completed"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : doc.status === "processing" || doc.status === "uploaded"
                            ? "bg-amber-50 text-amber-700 border border-amber-200"
                            : "bg-rose-50 text-rose-700 border border-rose-200"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            doc.status === "completed"
                              ? "bg-emerald-500"
                              : doc.status === "processing" || doc.status === "uploaded"
                              ? "bg-amber-500 animate-pulse"
                              : "bg-rose-500"
                          }`}
                        />
                        {doc.status}
                      </span>
                    </td>
                    <td className="py-4 px-4 text-slate-700">
                      <span className="font-bold text-slate-900">{doc.total_pages}</span> pages · <span className="font-bold text-cyan-700">{doc.total_chunks}</span> chunks
                    </td>
                    <td className="py-4 px-4 text-slate-600 font-medium" title={formatDateTime(doc.created_at)}>
                      {formatDateTime(doc.created_at)}
                    </td>
                    <td className="py-4 px-6 text-right space-x-2">
                      <button
                        onClick={() => setSelectedDoc(doc)}
                        title="View Document Details"
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-cyan-700 transition-colors"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id, doc.filename)}
                        disabled={deletingId === doc.id}
                        title="Delete Document"
                        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-rose-600 disabled:opacity-50 transition-colors"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* View Document Details Modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-2xl p-6 space-y-5 max-h-[85vh] overflow-y-auto">
            <button
              onClick={() => setSelectedDoc(null)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-800"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700 border border-cyan-200">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 truncate max-w-md">{selectedDoc.filename}</h3>
                <p className="text-xs text-slate-500">Document Details & Metadata</p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Status</span>
                <p className="text-xs font-bold text-emerald-700 capitalize mt-0.5">{selectedDoc.status}</p>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Pages</span>
                <p className="text-xs font-bold text-cyan-700 mt-0.5">{selectedDoc.total_pages}</p>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Vector Chunks</span>
                <p className="text-xs font-bold text-indigo-700 mt-0.5">{selectedDoc.total_chunks}</p>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">File Size</span>
                <p className="text-xs font-bold text-slate-800 mt-0.5">{(selectedDoc.file_size / (1024 * 1024)).toFixed(2)} MB</p>
              </div>
            </div>

            {selectedDoc.error_message && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-500 mt-0.5" />
                <span>Error details: {selectedDoc.error_message}</span>
              </div>
            )}

            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-cyan-700">
                <Database className="h-4 w-4" />
                <span>ChromaDB Vector Index Status</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                All {selectedDoc.total_chunks} chunks are indexed with 384-dimensional dense vectors via <code className="text-slate-800 font-mono bg-slate-200/60 px-1 py-0.5 rounded">all-MiniLM-L6-v2</code>. Each chunk retains exact page number references and section provenance.
              </p>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedDoc(null)}
                className="rounded-lg bg-slate-100 hover:bg-slate-200 px-4 py-2 text-xs font-semibold text-slate-700 border border-slate-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
