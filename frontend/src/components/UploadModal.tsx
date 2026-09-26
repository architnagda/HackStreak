import React, { useState, useRef } from "react";
import { 
  X, 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Loader2
} from "lucide-react";
import { api } from "../services/api";
import type { DocumentItem } from "../types";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (doc: DocumentItem) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [uploadedDoc, setUploadedDoc] = useState<DocumentItem | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (selectedFile: File) => {
    setError(null);
    setUploadedDoc(null);
    const validExtensions = [".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md"];
    const ext = selectedFile.name.substring(selectedFile.name.lastIndexOf(".")).toLowerCase();

    if (!validExtensions.includes(ext)) {
      setError(`Invalid file format '${ext}'. Please upload a PDF, DOCX, Image (PNG/JPG), or TXT file.`);
      return;
    }

    if (selectedFile.size > 50 * 1024 * 1024) {
      setError("File exceeds maximum allowed size of 50 MB.");
      return;
    }

    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(15);
    setStatusMessage("Uploading document to secure server...");
    setError(null);

    try {
      const doc = await api.uploadDocument(file, (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 70) / progressEvent.total);
          setProgress(percent);
          if (percent > 60) {
            setStatusMessage("Extracting text, OCR scanning & generating ChromaDB vectors...");
          }
        }
      });

      setProgress(100);
      setStatusMessage("Document indexed and ready for semantic intelligence!");
      setUploadedDoc(doc);
      onUploadSuccess(doc);
    } catch (err: any) {
      console.error("Upload error:", err);
      const msg = err.response?.data?.detail || "Failed to process document. Please check file format.";
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  const resetState = () => {
    setFile(null);
    setProgress(0);
    setStatusMessage("");
    setError(null);
    setUploadedDoc(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-2xl p-6">
        {/* Close Button */}
        <button
          onClick={resetState}
          className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 border border-cyan-200 text-cyan-700">
            <UploadCloud className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Upload Knowledge Document</h3>
            <p className="text-xs text-slate-500">
              PDF, OCR Scans, Images, & DOCX (Max 50MB)
            </p>
          </div>
        </div>

        {/* Upload Zone */}
        {!uploadedDoc ? (
          <div className="space-y-4">
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-200 ${
                dragActive
                  ? "border-cyan-500 bg-cyan-50/50"
                  : file
                  ? "border-emerald-500/60 bg-emerald-50/40"
                  : "border-slate-300 bg-slate-50 hover:border-slate-400 hover:bg-slate-100/50"
              }`}
            >
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.txt,.md"
                onChange={handleChange}
              />

              {file ? (
                <div className="flex flex-col items-center gap-2">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                    <FileText className="h-6 w-6" />
                  </div>
                  <span className="text-sm font-semibold text-slate-800 max-w-xs truncate">
                    {file.name}
                  </span>
                  <span className="text-xs text-slate-500">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-200/80 text-slate-600">
                    <UploadCloud className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-700">
                      Drag & drop your file here, or <span className="text-cyan-700 font-semibold underline">browse</span>
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Supports Digital PDF, Scanned PDF, JPG, PNG, DOCX
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="flex items-center gap-2 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700">
                <AlertCircle className="h-4 w-4 shrink-0 text-rose-500" />
                <span>{error}</span>
              </div>
            )}

            {/* Progress Bar & Status */}
            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-slate-600">
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-600" />
                    {statusMessage}
                  </span>
                  <span className="font-semibold text-cyan-700">{progress}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full bg-gradient-to-r from-cyan-600 to-indigo-600 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={resetState}
                disabled={uploading}
                className="rounded-lg px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleUpload}
                disabled={!file || uploading}
                className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-cyan-600/20 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 transition-all"
              >
                {uploading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Processing Pipeline...</span>
                  </>
                ) : (
                  <span>Upload & Index</span>
                )}
              </button>
            </div>
          </div>
        ) : (
          /* Success Screen */
          <div className="space-y-5 text-center py-4">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 border border-emerald-200">
              <CheckCircle2 className="h-8 w-8" />
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-900">Document Processed Successfully!</h4>
              <p className="text-xs text-slate-600 mt-1 max-w-sm mx-auto">
                <span className="font-semibold text-slate-800">{uploadedDoc.filename}</span> has been parsed, chunked ({uploadedDoc.total_chunks} chunks), and embedded into ChromaDB.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 max-w-xs mx-auto">
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-2.5">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Pages</span>
                <p className="text-sm font-bold text-cyan-700">{uploadedDoc.total_pages}</p>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-2.5">
                <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Chunks Indexed</span>
                <p className="text-sm font-bold text-emerald-700">{uploadedDoc.total_chunks}</p>
              </div>
            </div>

            <div className="flex justify-center gap-3 pt-2">
              <button
                onClick={resetState}
                className="rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 px-5 py-2 text-xs font-semibold text-white shadow-sm shadow-cyan-600/20 hover:from-cyan-500 hover:to-blue-500"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
