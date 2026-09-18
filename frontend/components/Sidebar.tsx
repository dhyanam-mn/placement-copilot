'use client';

import React from 'react';
import {
  Columns3,
  FileText,
  Activity,
  ShieldCheck,
  MessageSquare,
  BarChart3,
  Archive,
} from 'lucide-react';

export type NavTab =
  | 'pipeline'
  | 'tailoring'
  | 'activity'
  | 'scam-check'
  | 'prep'
  | 'gap-report';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const navItems = [
    { id: 'pipeline' as NavTab, label: 'Pipeline', icon: Columns3 },
    { id: 'tailoring' as NavTab, label: 'Resume Tailoring', icon: FileText },
    { id: 'activity' as NavTab, label: 'Activity Feed', icon: Activity },
    { id: 'scam-check' as NavTab, label: 'Scam Check', icon: ShieldCheck },
    { id: 'prep' as NavTab, label: 'Interview Prep', icon: MessageSquare },
    { id: 'gap-report' as NavTab, label: 'Gap Analysis', icon: BarChart3 },
  ];

  return (
    <aside className="w-64 min-h-screen bg-[#2c392c] text-white flex flex-col justify-between p-6 select-none shrink-0 border-r border-accent/20">
      <div className="space-y-8">
        {/* Brand Header */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-primary flex items-center justify-center text-white">
            <span className="font-semibold text-sm">PC</span>
          </div>
          <div>
            <h1 className="text-base font-medium tracking-tight text-white">Placement Copilot</h1>
            <p className="text-xs text-accent/80">VIT Student Assistant</p>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-sm transition-colors text-left ${
                  isActive
                    ? 'bg-white/10 text-white font-medium'
                    : 'text-accent/90 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Grounding / Calm message at bottom */}
      <div className="pt-6 border-t border-white/10 space-y-2">
        <p className="text-xs font-medium text-accent">Daily breathing check-in</p>
        <p className="text-xs text-white/70 leading-relaxed">
          You are doing fine. One application at a time is perfect.
        </p>
      </div>
    </aside>
  );
};
