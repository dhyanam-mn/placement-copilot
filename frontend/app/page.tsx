'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getApplications } from '@/lib/api';
import { Application, ApplicationStatus } from '@/types';
import { KanbanBoard } from '@/components/KanbanBoard';
import { FolderArchive, Plus, AlertCircle, RefreshCw, Sparkles, ExternalLink } from 'lucide-react';

export default function DashboardTimelinePage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApps = () => {
    setLoading(true);
    setError(null);
    getApplications()
      .then((res) => setApplications(res.applications))
      .catch((err) => setError(err.message || 'Failed to load applications'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchApps();
  }, []);

  const getSourceBadge = (source: string | null) => {
    if (source === 'gmail_auto') {
      return (
        <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200">
          gmail_auto
        </span>
      );
    }
    if (source === 'auto_ghost') {
      return (
        <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-200">
          auto_ghost
        </span>
      );
    }
    if (source === 'manual') {
      return (
        <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-gray-100 text-gray-700 border border-gray-200">
          manual
        </span>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">Dashboard Timeline</h2>
          <p className="text-sm text-text/60 mt-1">Loading your pipeline timeline…</p>
        </div>
        <div className="p-12 text-center text-text/50 bg-white/50 rounded-lg border border-accent/20 animate-pulse">
          Loading applications from backend...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">Dashboard Timeline</h2>
          <p className="text-sm text-rejected mt-1">Error fetching applications: {error}</p>
        </div>
        <button
          onClick={fetchApps}
          className="px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors inline-flex items-center space-x-2"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Connection</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Dashboard Timeline
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Real-time pipeline timeline displaying application status updates, status source provenance badges, and demo indicators.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={fetchApps}
            className="px-3.5 py-2 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors inline-flex items-center space-x-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Kanban Board Container */}
      {applications.length === 0 ? (
        <div className="p-12 text-center bg-white/70 rounded-lg border border-accent/30 space-y-3">
          <AlertCircle className="w-8 h-8 text-accent mx-auto" />
          <h3 className="text-base font-semibold text-text">No Applications Tracked</h3>
          <p className="text-xs text-text/60">
            Run Scout discovery or import demo seed applications to get started.
          </p>
          <Link
            href="/scout"
            className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Discover Jobs with Scout</span>
          </Link>
        </div>
      ) : (
        <KanbanBoard
          onSelectApplication={(app) => {
            window.location.href = `/applications/${app.id}`;
          }}
        />
      )}
    </div>
  );
}
