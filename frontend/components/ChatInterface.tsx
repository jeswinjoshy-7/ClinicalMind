"use client";

import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// --- Types ---

interface Message {
  role: 'user' | 'assistant';
  content: string;
  safety_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  sources?: string[];
}

interface QueryResponse {
  response: string;
  safety_level: string;
  sources: string[];
  query_time: number;
}

// --- Components ---

const SafetyBadge: React.FC<{ level?: string }> = ({ level }) => {
  if (!level) return null;

  const styles = {
    HIGH: "bg-red-100 text-red-700 border-red-200",
    MEDIUM: "bg-amber-100 text-amber-700 border-amber-200",
    LOW: "bg-emerald-100 text-emerald-700 border-emerald-200",
  };

  const currentStyle = styles[level as keyof typeof styles] || "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <div className={`mt-2 inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border uppercase tracking-wider ${currentStyle}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
        level === 'HIGH' ? 'bg-red-500' : level === 'MEDIUM' ? 'bg-amber-500' : 'bg-emerald-500'
      }`}></span>
      Safety Risk: {level}
    </div>
  );
};

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput('');
    
    // Add user message to history
    const userMessage: Message = { role: 'user', content: userQuery };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const { data } = await axios.post<QueryResponse>('http://localhost:8000/query', {
        query: userQuery,
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        safety_level: data.safety_level as any,
        sources: data.sources,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Clinical Query Error:", error);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: "Error: Unable to connect to clinical intelligence server." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[650px] bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Live Clinical Session</span>
        </div>
      </div>

      {/* Message Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-6 bg-gradient-to-b from-white to-slate-50/30"
      >
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-600">No active clinical reasoning.</p>
            <p className="text-xs text-slate-400">Query the knowledge base to begin.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
              <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-tr-none' 
                  : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'
              }`}>
                <div className="whitespace-pre-wrap">{msg.content}</div>
                
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <p className="text-[10px] font-bold text-slate-400 uppercase mb-2 tracking-tighter">Verified Sources</p>
                    <div className="flex flex-wrap gap-1">
                      {msg.sources.map((source, sIdx) => (
                        <span key={sIdx} className="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded border border-slate-200">
                          {source}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <SafetyBadge level={msg.safety_level} />
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-200 p-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-3">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-bounce"></div>
              </div>
              <span className="text-xs font-medium text-slate-400">Reasoning over clinical stores...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <form onSubmit={handleSendMessage} className="p-4 bg-white border-t border-slate-100">
        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Search guidelines, drug interactions, or history..."
            className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-sm rounded-xl pl-4 pr-12 py-3.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-30 disabled:hover:bg-blue-600"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </button>
        </div>
        <p className="mt-2 text-[10px] text-center text-slate-400 font-medium uppercase tracking-widest">
          AI-generated clinical support • Always verify with professional judgment
        </p>
      </form>
    </div>
  );
};
