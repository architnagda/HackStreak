import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { 
  Files, 
  CheckCircle2, 
  UploadCloud, 
  ArrowRight,
  FileText,
  Sparkles,
  ChevronRight
} from "lucide-react";
import { api } from "../services/api";
import type { DocumentItem, DocumentStats } from "../types";
import { formatDateTime } from "../utils/date";

export const Dashboard: React.FC<{ onOpenUpload: () => void }> = ({ onOpenUpload }) => {
  const [stats, setStats] = useState<DocumentStats>({
    total_documents: 0,
    processing_documents: 0,
    completed_documents: 0,
    failed_documents: 0,
  });
  const [recentDocs, setRecentDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      const [statsData, docsData] = await Promise.all([
        api.getDocumentStats(),
        api.getDocuments(),
      ]);
      setStats(statsData);
      setRecentDocs(docsData.slice(0, 5));
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const statCards = [
    {
      title: "Total Documents",
      value: stats.total_documents,
      icon: Files,
      color: "bg-blue-50 text-blue-700",
      border: "border-blue-200",
      textColor: "text-blue-800",
      desc: "Uploaded to knowledge base",
    },
    {
      title: "Indexed & Completed",
      value: stats.completed_documents,
      icon: CheckCircle2,
      color: "bg-emerald-50 text-emerald-700",
      border: "border-emerald-200",
      textColor: "text-emerald-800",
      desc: "ChromaDB vector searchable",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-r from-white via-slate-50 to-cyan-50/50 p-8 sm:p-10 shadow-sm text-center">
        <div className="relative z-10 flex flex-col items-center gap-5 max-w-3xl mx-auto">
          <div className="space-y-3 flex flex-col items-center">
            <div className="inline-flex items-center gap-2 rounded-full bg-cyan-100/80 border border-cyan-200 px-4 py-1.5 text-sm font-bold text-cyan-800 shadow-xs">
              <Sparkles className="h-4 w-4 text-cyan-700" />
              <span>Multi-Source Document Intelligence</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
              Grounded AI Intelligence Across All Your Files
            </h1>
            <p className="text-base sm:text-lg text-slate-600 max-w-2xl leading-relaxed mx-auto">
              Upload digital PDFs, scanned OCR documents, and images. Query them with strict evidence citations, exact page provenance, and multi-source reasoning.
            </p>
          </div>

          <div className="pt-2 flex justify-center w-full">
            <button
              onClick={onOpenUpload}
              className="inline-flex items-center gap-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-7 py-3.5 text-base font-semibold text-white shadow-md shadow-cyan-600/25 hover:from-cyan-500 hover:to-blue-500 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 cursor-pointer"
            >
              <UploadCloud className="h-5 w-5" />
              <span>Upload Document</span>
            </button>
          </div>
        </div>

        {/* Decorative corner glow */}
        <div className="absolute -right-10 -bottom-10 h-48 w-48 rounded-full bg-cyan-200/40 blur-3xl pointer-events-none" />
      </div>

      {/* Primary Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className={`relative overflow-hidden rounded-xl border bg-white p-6 shadow-sm transition-all hover:shadow-md ${card.border}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  {card.title}
                </span>
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${card.color}`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4">
                <p className={`text-4xl font-black ${card.textColor}`}>
                  {loading ? "..." : card.value}
                </p>
                <p className="mt-1.5 text-xs text-slate-500">{card.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Documents Table & Suggested Queries */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Documents Table */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-cyan-600" />
              <h3 className="text-base font-bold text-slate-900">Recent Documents</h3>
            </div>
            <Link
              to="/documents"
              className="text-xs font-bold text-cyan-700 hover:text-cyan-600 flex items-center gap-1"
            >
              View all ({stats.total_documents})
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-slate-500">Loading documents...</div>
          ) : recentDocs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center space-y-3">
              <p className="text-sm text-slate-500 font-medium">No documents uploaded yet.</p>
              <button
                onClick={onOpenUpload}
                className="inline-flex items-center gap-2 rounded-lg bg-white hover:bg-slate-50 px-4 py-2 text-xs font-semibold text-cyan-700 border border-slate-300 shadow-xs"
              >
                Upload your first document
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-500 uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-4 font-bold">Document Name</th>
                    <th className="py-3 px-3 font-bold">Type</th>
                    <th className="py-3 px-3 font-bold">Status</th>
                    <th className="py-3 px-3 font-bold">Pages / Chunks</th>
                    <th className="py-3 px-4 font-bold">Uploaded (Real Time)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {recentDocs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4 font-medium text-slate-800 flex items-center gap-2 max-w-[200px] truncate">
                        <FileText className="h-4 w-4 text-cyan-600 shrink-0" />
                        <span className="truncate font-semibold">{doc.filename}</span>
                      </td>
                      <td className="py-3 px-3 text-slate-500 uppercase text-[10px] font-mono">
                        {doc.filename.split('.').pop() || "doc"}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
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
                      <td className="py-3 px-3 text-slate-600 font-medium">
                        {doc.total_pages} p / {doc.total_chunks} ch
                      </td>
                      <td className="py-3 px-4 text-slate-600" title={formatDateTime(doc.created_at)}>
                        {formatDateTime(doc.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Guided Intelligence Prompts */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-cyan-600" />
            <h3 className="text-base font-bold text-slate-900">Suggested Queries</h3>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed">
            Test multi-document reasoning, citation verification, and strict grounding:
          </p>

          <div className="space-y-3">
            {[
              {
                title: "Multi-Source Comparison",
                query: "Compare gross revenue and R&D outlook between 2024 and 2025.",
              },
              {
                title: "Specific Page Citation",
                query: "What was the operating profit margin in fiscal year 2025?",
              },
              {
                title: "Zero-Hallucination Test",
                query: "What is the secret recipe for chocolate cake in Mars?",
              },
            ].map((prompt, i) => (
              <Link
                key={i}
                to={`/chat?prompt=${encodeURIComponent(prompt.query)}`}
                className="block rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 hover:border-cyan-400 hover:bg-cyan-50/40 transition-all group shadow-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800 group-hover:text-cyan-700 transition-colors">
                    {prompt.title}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-cyan-700 group-hover:translate-x-0.5 transition-all" />
                </div>
                <p className="text-[11px] text-slate-500 mt-1 italic line-clamp-2">
                  "{prompt.query}"
                </p>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
