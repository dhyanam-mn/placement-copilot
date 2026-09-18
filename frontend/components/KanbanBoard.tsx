'use client';

import React, { useEffect, useState } from 'react';
import { Application, ApplicationStatus } from '@/types';
import { getApplications } from '@/lib/api';
import { FolderArchive, Plus } from 'lucide-react';

interface KanbanBoardProps {
  onSelectApplication?: (app: Application) => void;
}

interface ColumnConfig {
  status: ApplicationStatus;
  title: string;
  badgeClass: string;
  pillColor: string;
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({ onSelectApplication }) => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getApplications()
      .then((data) => {
        if (!cancelled) setApplications(data.applications);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to load applications');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const activeColumns: ColumnConfig[] = [
    { status: 'DISCOVERED', title: 'Discovered', badgeClass: 'text-discovered', pillColor: '#9aa0a0' },
    { status: 'READY_TO_APPLY', title: 'Ready to Apply', badgeClass: 'text-primary', pillColor: '#6d8669' },
    { status: 'APPLIED', title: 'Applied', badgeClass: 'text-applied', pillColor: '#7b93ad' },
    { status: 'OA_INVITE', title: 'OA', badgeClass: 'text-oa', pillColor: '#b3936a' },
    { status: 'INTERVIEW', title: 'Interview', badgeClass: 'text-interview', pillColor: '#8a7bab' },
    { status: 'OFFER', title: 'Result', badgeClass: 'text-primary', pillColor: '#6d8669' },
  ];

  const archivedColumns: ColumnConfig[] = [
    { status: 'GHOSTED', title: 'Ghosted', badgeClass: 'text-ghosted', pillColor: '#a89a8c' },
    { status: 'REJECTED', title: 'Rejected', badgeClass: 'text-rejected', pillColor: '#b06a5f' },
  ];

  const getAppsByStatus = (status: ApplicationStatus) =>
    applications.filter((app) => app.status === status);

  if (loading) {
    return (
      <div className="space-y-8">
        <h2 className="text-2xl font-semibold tracking-tight text-text">
          Your active applications
        </h2>
        <p className="text-sm text-text/60">Loading your pipeline…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <h2 className="text-2xl font-semibold tracking-tight text-text">
          Your active applications
        </h2>
        <p className="text-sm text-rejected">
          Couldn&apos;t reach the backend: {error}. Is it running on{' '}
          {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}?
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {/* Top Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Your active applications
          </h2>
          <p className="text-sm text-text/60 mt-1">
            A quiet space to organize, review, and track without the panic.
          </p>
        </div>

        <button
          type="button"
          className="inline-flex items-center space-x-2 px-3.5 py-2 text-xs font-medium text-text bg-white/70 hover:bg-white border border-accent/40 rounded transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Track new role</span>
        </button>
      </div>

      {/* Active Pipeline Grid (6 columns) */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 items-start">
        {activeColumns.map((col) => {
          const colApps = getAppsByStatus(col.status);
          return (
            <div key={col.status} className="space-y-3">
              {/* Column Header */}
              <div className="flex items-baseline space-x-2 pb-2 border-b border-accent/30">
                <span className="text-xs font-semibold text-text">{col.title}</span>
                <span className="text-xs text-text/50">{colApps.length}</span>
              </div>

              {/* Cards list */}
              <div className="space-y-3 min-h-[150px]">
                {colApps.map((app) => (
                  <div
                    key={app.id}
                    onClick={() => onSelectApplication?.(app)}
                    className="p-3.5 rounded-lg border border-accent/30 bg-white/80 hover:bg-white transition-colors cursor-pointer space-y-2.5"
                  >
                    <div>
                      <h3 className="text-sm font-semibold text-text leading-snug">
                        {app.role}
                      </h3>
                      <p className="text-xs text-text/70">{app.company}</p>
                    </div>

                    {app.summary && (
                      <p className="text-xs text-text/60 line-clamp-3 leading-relaxed">
                        {app.summary}
                      </p>
                    )}

                    <div className="pt-1 flex items-center justify-between">
                      <span
                        className="text-[11px] font-medium px-2 py-0.5 rounded bg-bg text-text/80"
                        style={{ color: col.pillColor }}
                      >
                        {app.status_label || col.title}
                      </span>
                      {app.match_score != null && (
                        <span className="text-[11px] text-text/50">
                          {Math.round(app.match_score * 100)}% match
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Completed Out of Process Section */}
      <div className="pt-8 border-t border-accent/40 space-y-4">
        <div className="flex items-center space-x-2 text-text/70">
          <FolderArchive className="w-4 h-4 text-accent" />
          <h3 className="text-xs font-medium tracking-tight">
            Completed Out of Process • Archived outcomes to declutter your mind
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 items-start">
          {archivedColumns.map((col) => {
            const colApps = getAppsByStatus(col.status);
            return (
              <div key={col.status} className="space-y-3">
                <div className="flex items-baseline space-x-2 pb-2 border-b border-accent/30">
                  <span className="text-xs font-semibold text-text">{col.title}</span>
                  <span className="text-xs text-text/50">{colApps.length}</span>
                </div>

                <div className="space-y-3">
                  {colApps.map((app) => (
                    <div
                      key={app.id}
                      onClick={() => onSelectApplication?.(app)}
                      className="p-3.5 rounded-lg border border-accent/30 bg-white/60 hover:bg-white/90 transition-colors cursor-pointer space-y-2.5"
                    >
                      <div>
                        <h4 className="text-sm font-semibold text-text leading-snug">
                          {app.role}
                        </h4>
                        <p className="text-xs text-text/70">{app.company}</p>
                      </div>

                      {app.summary && (
                        <p className="text-xs text-text/60 line-clamp-2 leading-relaxed">
                          {app.summary}
                        </p>
                      )}

                      <div className="pt-1">
                        <span
                          className="text-[11px] font-medium"
                          style={{ color: col.pillColor }}
                        >
                          {app.status_label || col.title}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};