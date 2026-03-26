"use client";

import React, { useState } from 'react';
import { clinicalApi } from '../lib/api';

export const FileUploadPanel: React.FC = () => {
  const [loading, setLoading] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>, type: 'guidelines' | 'drugs' | 'patients') => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(type);
    setMsg(null);

    try {
      await clinicalApi.uploadDocument(file, type);
      setMsg({ type: 'success', text: `Successfully indexed ${file.name} to ${type}.` });
    } catch (err) {
      setMsg({ type: 'error', text: `Failed to upload ${file.name}.` });
    } finally {
      setLoading(null);
      e.target.value = ''; // Reset input
    }
  };

  const uploadSections = [
    { label: 'Clinical Guidelines', type: 'guidelines' as const, color: 'border-blue-200' },
    { label: 'Drug Database', type: 'drugs' as const, color: 'border-emerald-200' },
    { label: 'Patient Records', type: 'patients' as const, color: 'border-purple-200' },
  ];

  return (
    <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-6">
      <h3 className="font-bold text-slate-800 border-b pb-2">Knowledge Base Management</h3>
      
      {uploadSections.map((section) => (
        <div key={section.type} className={`p-4 border-2 border-dashed ${section.color} rounded-lg hover:bg-slate-50 transition relative`}>
          <div className="flex flex-col gap-2">
            <span className="text-sm font-semibold text-slate-700">{section.label}</span>
            <input
              type="file"
              onChange={(e) => handleUpload(e, section.type)}
              disabled={!!loading}
              className="text-xs text-slate-500 file:mr-4 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 cursor-pointer"
            />
          </div>
          {loading === section.type && (
            <div className="absolute inset-0 bg-white/80 flex items-center justify-center text-xs font-bold text-blue-600 animate-pulse">
              Indexing document...
            </div>
          )}
        </div>
      ))}

      {msg && (
        <div className={`p-3 rounded text-xs font-medium ${
          msg.type === 'success' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
        }`}>
          {msg.text}
        </div>
      )}
    </div>
  );
};

export const SystemStatusPanel: React.FC = () => {
  const [status, setStatus] = useState<any>(null);

  const fetchStatus = async () => {
    const data = await clinicalApi.getStatus();
    setStatus(data);
  };

  React.useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);

  if (!status) return null;

  return (
    <div className="bg-slate-900 text-slate-300 p-5 rounded-lg border border-slate-700 shadow-lg space-y-4">
      <div className="flex items-center justify-between border-b border-slate-700 pb-2">
        <h3 className="font-bold text-white text-sm">System Health</h3>
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
      </div>

      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <p className="text-slate-500 mb-1">LLM Model</p>
          <p className="font-mono text-emerald-400">{status.llm_model}</p>
        </div>
        <div>
          <p className="text-slate-500 mb-1">Safety Filter</p>
          <p className={status.safety_filter_enabled ? 'text-emerald-400' : 'text-red-400'}>
            {status.safety_filter_enabled ? 'ACTIVE' : 'DISABLED'}
          </p>
        </div>
        <div>
          <p className="text-slate-500 mb-1">Memory Depth</p>
          <p className="text-white font-bold">{status.memory_depth} exchanges</p>
        </div>
      </div>

      <div className="mt-4 border-t border-slate-700 pt-3">
        <p className="text-slate-500 text-[10px] mb-2 uppercase tracking-widest font-bold">Vector Stores</p>
        <div className="space-y-2 text-[11px]">
          {Object.entries(status.database).map(([key, db]: [string, any]) => (
            <div key={key} className="flex justify-between items-center bg-slate-800 p-2 rounded">
              <span className="capitalize">{key}</span>
              <span className="text-blue-400">{db.document_count || 0} chunks</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
