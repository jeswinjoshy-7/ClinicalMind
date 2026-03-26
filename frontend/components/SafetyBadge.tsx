"use client";

import React from 'react';

// --- Types ---

export type SafetyLevel = 'LOW' | 'MEDIUM' | 'HIGH' | string;

interface SafetyBadgeProps {
  level?: SafetyLevel;
  showIcon?: boolean;
}

// --- Component ---

/**
 * A reusable safety indicator for clinical risk assessment.
 * 
 * Provides color-coded visual feedback and status icons based on 
 * the determined risk level of a query or response.
 */
export const SafetyBadge: React.FC<SafetyBadgeProps> = ({ level, showIcon = true }) => {
  if (!level) return null;

  const normalizedLevel = level.toUpperCase();

  const config = {
    LOW: {
      container: "bg-emerald-50 text-emerald-700 border-emerald-200",
      dot: "bg-emerald-500",
      text: "Low Clinical Risk",
      icon: (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
        </svg>
      )
    },
    MEDIUM: {
      container: "bg-amber-50 text-amber-700 border-amber-200",
      dot: "bg-amber-500",
      text: "Moderate Risk",
      icon: (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      )
    },
    HIGH: {
      container: "bg-red-50 text-red-700 border-red-200 ring-2 ring-red-100",
      dot: "bg-red-500 animate-pulse",
      text: "HIGH RISK WARNING",
      icon: (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    }
  };

  const style = config[normalizedLevel as keyof typeof config] || {
    container: "bg-slate-50 text-slate-600 border-slate-200",
    dot: "bg-slate-400",
    text: normalizedLevel,
    icon: null
  };

  return (
    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full border text-[10px] font-black uppercase tracking-wider shadow-sm transition-all duration-300 ${style.container}`}>
      {showIcon && style.icon && (
        <span className="flex-shrink-0">
          {style.icon}
        </span>
      )}
      {!showIcon && <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`}></span>}
      
      <span>{style.text}</span>
      
      {normalizedLevel === 'HIGH' && (
        <span className="ml-1 px-1.5 py-0.5 bg-red-600 text-white rounded-md text-[8px] animate-bounce">
          CRITICAL
        </span>
      )}
    </div>
  );
};
