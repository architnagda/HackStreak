import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Navbar } from "./components/Navbar";
import { Sidebar } from "./components/Sidebar";
import { UploadModal } from "./components/UploadModal";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { Dashboard } from "./pages/Dashboard";
import { Documents } from "./pages/Documents";
import { Chat } from "./pages/Chat";
import type { DocumentItem } from "./types";

// Protected Layout Component
const AppLayout: React.FC<{ children: (onOpenUpload: () => void) => React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-cyan-700 text-sm">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-600 border-t-transparent" />
          <span className="font-medium text-slate-700">Initializing DocuMind Workspace...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto max-w-7xl mx-auto w-full">
          {children(() => setIsUploadOpen(true))}
        </main>
      </div>

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={(doc: DocumentItem) => {
          console.log("Document successfully processed:", doc);
        }}
      />
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          {/* Protected Application Routes */}
          <Route
            path="/dashboard"
            element={
              <AppLayout>
                {(openUpload) => <Dashboard onOpenUpload={openUpload} />}
              </AppLayout>
            }
          />
          <Route
            path="/documents"
            element={
              <AppLayout>
                {(openUpload) => <Documents onOpenUpload={openUpload} />}
              </AppLayout>
            }
          />
          <Route
            path="/chat"
            element={
              <AppLayout>
                {() => <Chat />}
              </AppLayout>
            }
          />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
