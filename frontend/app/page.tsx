import React from 'react';
import { ChatInterface } from '../components/ChatInterface';
import { FileUploadPanel, SystemStatusPanel } from '../components/StatusAndUpload';

export default function Dashboard() {
  return (
    <main className="min-h-screen bg-slate-50 font-sans antialiased text-slate-900">
      {/* Header */}
      <nav className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-200">
              <span className="text-white font-black text-xl">C</span>
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tight text-slate-800">ClinicalMind<span className="text-blue-600 italic">.AI</span></h1>
              <p className="text-[10px] uppercase tracking-widest font-bold text-slate-400">Multi-Agent Intelligence System</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-[10px] font-bold text-slate-600 uppercase">System Ready</span>
            </div>
            <button className="text-slate-500 hover:text-red-600 transition p-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Sidebar: Tools & Status */}
        <aside className="lg:col-span-4 space-y-8 order-2 lg:order-1">
          <SystemStatusPanel />
          <FileUploadPanel />
          
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg">
            <h4 className="text-xs font-bold text-blue-800 uppercase mb-2">Clinical Protocol</h4>
            <p className="text-[11px] text-blue-600 leading-relaxed">
              This system uses multi-agent LangGraph orchestration. All responses are verified against current vector store knowledge and pass through a high-risk safety validator.
            </p>
          </div>
        </aside>

        {/* Center: Chat Interface */}
        <section className="lg:col-span-8 space-y-6 order-1 lg:order-2">
          <div className="bg-blue-600 p-6 rounded-2xl shadow-xl shadow-blue-100 text-white relative overflow-hidden mb-8">
            <div className="relative z-10">
              <h2 className="text-2xl font-bold mb-2">Expert Clinical Reasoning</h2>
              <p className="text-blue-100 text-sm max-w-xl">
                Our multi-agent system integrates guidelines, pharmacology, and patient history to provide evidence-based insights with automated citation tracking.
              </p>
            </div>
            {/* Decorative element */}
            <div className="absolute top-[-20px] right-[-20px] w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
          </div>

          <ChatInterface />
        </section>

      </div>

      {/* Footer Disclaimer */}
      <footer className="max-w-7xl mx-auto px-6 py-10 text-center border-t border-slate-200 mt-12 mb-20">
        <p className="text-slate-400 text-xs font-medium">
          ClinicalMind.AI is a decision-support tool. All clinical decisions must be validated by licensed medical professionals.
        </p>
      </footer>
    </main>
  );
}
