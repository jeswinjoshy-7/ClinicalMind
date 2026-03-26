"use client";

import React, { useState } from 'react';
import axios from 'axios';

// --- Types ---

type DocType = 'guidelines' | 'drugs' | 'patients';

interface UploadState {
  isUploading: boolean;
  message: string | null;
  status: 'idle' | 'success' | 'error';
}

// --- Components ---

const UploadCard: React.FC<{
  title: string;
  description: string;
  type: DocType;
  icon: React.ReactNode;
}> = ({ title, description, type, icon }) => {
  const [state, setState] = useState<UploadState>({
    isUploading: false,
    message: null,
    status: 'idle',
  });

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type (basic)
    const allowedExtensions = ['.pdf', '.docx', '.txt'];
    const fileExt = file.name.slice(((file.name.lastIndexOf(".") - 1) >>> 0) + 2).toLowerCase();
    
    setState({ isUploading: true, message: 'Processing document...', status: 'idle' });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const { data } = await axios.post(`http://localhost:8000/upload/${type}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setState({
        isUploading: false,
        message: `Successfully indexed: ${file.name} (${data.chunks_added} chunks)`,
        status: 'success',
      });
    } catch (error: any) {
      console.error(`Upload error for ${type}:`, error);
      setState({
        isUploading: false,
        message: error.response?.data?.detail || "Failed to index document.",
        status: 'error',
      });
    } finally {
      // Reset input
      e.target.value = '';
    }
  };

  return (
    <div className={`p-5 rounded-2xl border bg-white shadow-sm transition-all ${
      state.status === 'success' ? 'border-emerald-200 bg-emerald-50/10' : 
      state.status === 'error' ? 'border-red-200 bg-red-50/10' : 'border-slate-100 hover:border-blue-200'
    }`}>
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-xl ${
          type === 'guidelines' ? 'bg-blue-50 text-blue-600' :
          type === 'drugs' ? 'bg-emerald-50 text-emerald-600' : 'bg-purple-50 text-purple-600'
        }`}>
          {icon}
        </div>
        
        <div className="flex-1">
          <h4 className="text-sm font-bold text-slate-800">{title}</h4>
          <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{description}</p>
          
          <div className="mt-4 relative">
            <input
              type="file"
              onChange={handleFileChange}
              disabled={state.isUploading}
              className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
            />
            <button className={`w-full py-2 px-3 border-2 border-dashed rounded-lg text-[11px] font-bold transition-colors ${
              state.isUploading ? 'bg-slate-50 border-slate-200 text-slate-400' :
              'border-slate-200 text-slate-600 hover:border-blue-400 hover:text-blue-600'
            }`}>
              {state.isUploading ? 'INDEXING...' : 'CHOOSE FILE'}
            </button>
          </div>

          {state.message && (
            <div className={`mt-3 text-[10px] font-medium p-2 rounded flex items-center gap-2 ${
              state.status === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
            }`}>
              <div className={`w-1 h-1 rounded-full ${state.status === 'success' ? 'bg-emerald-500' : 'bg-red-500'}`}></div>
              {state.message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const FileUploadPanel: React.FC = () => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">Knowledge Base Ingestion</h3>
      </div>

      <UploadCard
        title="Clinical Guidelines"
        type="guidelines"
        description="Medical protocols, standard procedures, and clinical practice guidelines (PDF/DOCX)."
        icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
      />

      <UploadCard
        title="Drug Database"
        type="drugs"
        description="Pharmacological data, dosage, interactions, and contraindications for indexing."
        icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.673.337a4 4 0 01-2.506.326l-1.423-.237a2 2 0 00-1.072.05l-1.35.45a2 2 0 01-1.235 0l-1.35-.45a2 2 0 00-1.072-.05l-1.423.237a4 4 0 01-2.506-.326l-.673-.337A6 6 0 003.38 14.5l-2.387.477a2 2 0 00-1.022.547l-.993.993a2 2 0 000 2.828l.993.993a2 2 0 001.022.547l2.387.477a6 6 0 003.86-.517l.673-.337a4 4 0 012.506-.326l1.423.237a2 2 0 001.072-.05l1.35-.45a2 2 0 011.235 0l1.35.45a2 2 0 001.072.05l1.423-.237a4 4 0 012.506.326l.673.337a6 6 0 003.86.517l2.387-.477a2 2 0 001.022-.547l.993-.993a2 2 0 000-2.828l-.993-.993z" /></svg>}
      />

      <UploadCard
        title="Patient Records"
        type="patients"
        description="Anonymized case studies and medical histories for historical clinical analysis."
        icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>}
      />
    </div>
  );
};
