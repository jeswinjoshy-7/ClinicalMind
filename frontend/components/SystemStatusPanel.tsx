"use client";

import React, { useState, useEffect } from 'react';
import axios from 'axios';

// --- Types ---

interface StoreMetadata {
  document_count: number;
  status: string;
  last_updated?: string;
}

interface StatusResponse {
  database: Record<string, StoreMetadata>;
  memory_depth: number;
  safety_filter_enabled: boolean;
  llm_model: string;
}

// --- Components ---

const StatusItem: React.FC<{ 
  label: string; 
  value: string | number; 
  icon?: React.ReactNode;
  colorClass?: string;
}> = ({ label, value, icon, colorClass = "text-slate-800" }) => (
  <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
    <div className="flex items-center gap-3">
      {icon && <div className="text-slate-400">{icon}</div>}
      <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight">{label}</span>
    </div>
    <span className={`text-sm font-black ${colorClass}`}>{value}</span>
  </div>
);

export const SystemStatusPanel: React.FC = () => {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<string>('');

  const fetchStatus = async () => {
    try {
      const { data } = await axios.get<StatusResponse>('http://localhost:8000/status');
      setStatus(data);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (error) {
      console.error("Failed to fetch system status:", error);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  if (!status) return (
    <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-sm animate-pulse">
      <div className="h-4 w-32 bg-slate-100 rounded mb-4"></div>
      <div className="space-y-3">
        <div className="h-10 bg-slate-50 rounded-xl"></div>
        <div className="h-10 bg-slate-50 rounded-xl"></div>
        <div className="h-10 bg-slate-50 rounded-xl"></div>
      </div>
    </div>
  );

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">Engine Metrics</h3>
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-[9px] font-bold uppercase">
            <span className="w-1 h-1 bg-emerald-500 rounded-full animate-ping"></span>
            Live
          </div>
        </div>
        <span className="text-[9px] font-medium text-slate-400">Refreshed: {lastRefreshed}</span>
      </div>

      {/* Stats Grid */}
      <div className="p-5 space-y-3">
        {/* Vector Stores */}
        <div className="grid grid-cols-1 gap-2">
          <StatusItem 
            label="Clinical Guidelines" 
            value={status.database.guidelines?.document_count || 0} 
            colorClass="text-blue-600"
            icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>}
          />
          <StatusItem 
            label="Drug Database" 
            value={status.database.drugs?.document_count || 0} 
            colorClass="text-emerald-600"
            icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19.423 15.423a2 2 0 00-1.023-.547l-2.387-.477a6 6 0 00-3.86.517l-.673.338a4 4 0 01-2.506.326l-1.423-.237a2 2 0 00-1.072.05l-1.35.45a2 2 0 01-1.235 0l-1.35-.45a2 2 0 00-1.072-.05l-1.423.237a4 4 0 01-2.506-.326l-.673-.338A6 6 0 003.38 14.5l-2.387.477a2 2 0 00-1.023.547l-.993.993a2 2 0 000 2.828l.993.993z" /></svg>}
          />
          <StatusItem 
            label="Patient History" 
            value={status.database.patients?.document_count || 0} 
            colorClass="text-purple-600"
            icon={<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>}
          />
        </div>

        {/* System Details */}
        <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 gap-2">
          <div className="p-3 bg-slate-900 rounded-xl">
            <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">Session Memory</p>
            <p className="text-lg font-black text-white">{status.memory_depth} <span className="text-[10px] font-medium text-slate-400 uppercase tracking-tighter">Turns</span></p>
          </div>
          <div className="p-3 bg-slate-900 rounded-xl">
            <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">AI Logic</p>
            <p className="text-[10px] font-mono text-emerald-400 break-all">{status.llm_model.split('-')[0].toUpperCase()}</p>
            <p className="text-[8px] text-slate-500 font-bold uppercase mt-1">Multi-Agent</p>
          </div>
        </div>

        {/* Safety Indicator */}
        <div className={`mt-2 p-2 rounded-lg flex items-center justify-center gap-2 border ${
          status.safety_filter_enabled ? 'bg-blue-50 border-blue-100' : 'bg-red-50 border-red-100'
        }`}>
          <div className={`w-1.5 h-1.5 rounded-full ${status.safety_filter_enabled ? 'bg-blue-500' : 'bg-red-500'}`}></div>
          <span className={`text-[10px] font-bold uppercase tracking-widest ${
            status.safety_filter_enabled ? 'text-blue-700' : 'text-red-700'
          }`}>
            Safety Guard: {status.safety_filter_enabled ? 'Active' : 'Disabled'}
          </span>
        </div>
      </div>
    </div>
  );
};
