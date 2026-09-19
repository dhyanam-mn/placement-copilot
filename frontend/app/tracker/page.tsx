'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getApplications, getStaleNudges, syncGmailTracker, updateApplicationStatus } from '@/lib/api';
import { Application, ApplicationStatus } from '@/types';
import { MailCheck, RefreshCw, AlertCircle, Clock, Check, Loader2 } from 'lucide-react';

const STATUS_OPTIONS: ApplicationStatus[] = [
  'DISCOVERED',
  'READY_TO_APPLY',
  'APPLIED',
  'OA_INVITE',
  'INTERVIEW',
  'REJECTED',
  'GHOSTED',
  'OFFER',
];

export default function TrackerPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [nudges, setNudges] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<any | null>(null);

  const loadTrackerData = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getApplications(),
      getStaleNudges(14).catch(() => []),
    ])
      .then(([appsRes, nudgesRes]) => {
        setApplications(appsRes.applications);
        setNudges(nudgesRes);
      })
      .catch((err) => setError(err.message || 'Failed to load tracker data'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTrackerData();
  }, []);

  const handleGmailSync = async () => {
    setSyncing(true);
    setError(null);
    setSyncResult(null);
    try {
      const res = await syncGmailTracker();
      setSyncResult(res);
      loadTrackerData();
    } catch (err: any) {
      setError(err.message || 'Gmail sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const handleStatusChange = async (appId: number, newStatus: string) => {
    setUpdatingId(appId);
    try {
      await updateApplicationStatus(appId, newStatus, 'manual');
      loadTrackerData();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Gmail Tracker & Stale Nudges
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Automated email parsing for interview/rejection signals and proactive follow-up nudges for stale applications.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleGmailSync}
            disabled={syncing}
            className="px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors inline-flex items-center space-x-2 disabled:opacity-50"
          >
            {syncing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <MailCheck className="w-3.5 h-3.5" />}
            <span>{syncing ? 'Syncing Gmail...' : 'Sync Gmail Now'}</span>
          </button>
        </div>
      </div>

      {syncResult && (
        <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs">
          Gmail Sync Complete: Matched {syncResult.updated_applications?.length || 0} application status updates.
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs">
          Error: {error}
        </div>
      )}

      {/* Stale Nudges Section */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-4">
        <div className="flex items-center space-x-2 pb-2 border-b border-accent/20">
          <Clock className="w-4 h-4 text-amber-600" />
          <h3 className="text-xs font-semibold text-text">
            Stale Application Nudges (14+ Days Without Contact)
          </h3>
          <span className="text-xs text-text/50">({nudges.length})</span>
        </div>

        {nudges.length === 0 ? (
          <p className="text-xs text-text/50">No stale applications requiring follow-up action currently.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {nudges.map((app) => (
              <div key={app.id} className="p-4 rounded border border-amber-200 bg-amber-50/50 space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="text-xs font-semibold text-text">{app.company}</h4>
                    <p className="text-[11px] text-text/70">{app.role}</p>
                  </div>
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                    Stale {Math.round((Date.now() - new Date(app.last_contact_date).getTime()) / (1000 * 3600 * 24))} days
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs pt-1">
                  <span className="text-[11px] text-text/60">Current: {app.status}</span>
                  <Link href={`/applications/${app.id}`} className="text-xs text-primary font-medium hover:underline">
                    View Details
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Manual Status Editor List */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-4">
        <h3 className="text-xs font-semibold text-text border-b border-accent/20 pb-2">
          Manual Application Status Management
        </h3>

        {loading ? (
          <div className="p-8 text-center text-text/50 animate-pulse">Loading applications...</div>
        ) : applications.length === 0 ? (
          <p className="text-xs text-text/50">No applications tracked in database.</p>
        ) : (
          <div className="space-y-3">
            {applications.map((app) => (
              <div key={app.id} className="p-3.5 rounded border border-accent/20 bg-bg/30 flex items-center justify-between flex-wrap gap-3">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-text">{app.role}</span>
                    {app.is_demo && (
                      <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 border border-amber-300">
                        DEMO
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-text/60">{app.company} • Last contact: {new Date(app.last_contact_date).toLocaleDateString()}</p>
                </div>

                <div className="flex items-center space-x-3">
                  {app.status_source && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white text-text/70 border border-accent/30">
                      {app.status_source}
                    </span>
                  )}

                  <select
                    value={app.status}
                    disabled={updatingId === app.id}
                    onChange={(e) => handleStatusChange(app.id, e.target.value)}
                    className="p-1.5 text-xs text-text bg-white border border-accent/40 rounded focus:outline-none focus:border-primary"
                  >
                    {STATUS_OPTIONS.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
