'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Columns3,
  Search,
  MailCheck,
  Bell,
  BarChart3,
  BookOpen,
  User,
  Settings,
  Sparkles,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: 'Dashboard Timeline', icon: Columns3 },
    { href: '/scout', label: 'Scout Discovery', icon: Search },
    { href: '/tracker', label: 'Gmail Tracker & Nudges', icon: MailCheck },
    { href: '/notifications', label: 'Notifications', icon: Bell },
    { href: '/gap', label: 'Gap Analysis', icon: BarChart3 },
    { href: '/prep', label: 'Interview Prep Plan', icon: BookOpen },
    { href: '/profile', label: 'Candidate Profile', icon: User },
    { href: '/admin', label: 'Admin Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 min-h-screen bg-[#2c392c] text-white flex flex-col justify-between p-6 select-none shrink-0 border-r border-accent/20">
      <div className="space-y-8">
        {/* Brand Header */}
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-primary flex items-center justify-center text-white font-bold text-sm">
            PC
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
            const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-sm transition-colors ${
                  isActive
                    ? 'bg-white/10 text-white font-medium'
                    : 'text-accent/90 hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Grounding message at bottom */}
      <div className="pt-6 border-t border-white/10 space-y-2">
        <p className="text-xs font-medium text-accent">Daily breathing check-in</p>
        <p className="text-xs text-white/70 leading-relaxed">
          You are doing fine. One application at a time is perfect.
        </p>
      </div>
    </aside>
  );
};
