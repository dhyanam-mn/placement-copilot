'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { getApplications, triggerScoutSync, getStoredScamCheck } from '@/lib/api';
import { Application, ScamCheck } from '@/types';
import { Search, RefreshCw, ShieldAlert, CheckCircle, Sparkles, ExternalLink, Loader2 } from 'lucide-react';

export default function ScoutPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<any | null>(null);

  const loadScoutData = () => {
    setLoading(true);
    setError(null);
    getApplications()
      .then((res) => {
        setApplications(res.applications);
      })
      .catch((err) => setError(err.message || 'Failed to load scout listings'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadScoutData();
  }, []);

  const handleSync = async (dryRun: boolean = false) => {
    setSyncing(true);
    setError(null);
    setSyncResult(null);
    try {
      const res = await triggerScoutSync(dryRun);
      setSyncResult(res);
      loadScoutData();
    } catch (err: any) {
      setError(err.message || 'Scout job sourcing failed');
    } finally {
      setSyncing(false);
    }
  };

  const discoveredApps = applications.filter(
    (app) => app.status === 'DISCOVERED' || app.status === 'READY_TO_APPLY'
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Scout Job Sourcing
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Autonomous sourcing agent fetching listings from Adzuna, Greenhouse, Lever, and Unstop with scam checks.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => handleSync(true)}
            disabled={syncing}
            className="px-3.5 py-2 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors disabled:opacity-50"
          >
            Preview Dry Run
          </button>
          <button
            onClick={() => handleSync(false)}
            disabled={syncing}
            className="px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors inline-flex items-center space-x-2 disabled:opacity-50"
          >
            {syncing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            <span>{syncing ? 'Sourcing Jobs...' : 'Sync Scout Live'}</span>
          </button>
        </div>
      </div>

      {/* Sync Summary Result Banner */}
      {syncResult && (
        <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs space-y-1">
          <p className="font-semibold">
            Scout Sync Complete ({syncResult.dry_run ? 'Dry Run' : 'Live'})
          </p>
          <p>
            Fetched: {syncResult.total_fetched || 0} listings | Processed: {syncResult.processed_count || 0} | Skipped Duplicates: {syncResult.duplicates_skipped || 0}
          </p>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs">
          Error: {error}
        </div>
      )}

      {/* Discovered Listings Grid */}
      {loading ? (
        <div className="p-12 text-center text-text/50 bg-white/50 rounded-lg border border-accent/20 animate-pulse">
          Loading discovered jobs from Scout...
        </div>
      ) : discoveredApps.length === 0 ? (
        <div className="p-12 text-center bg-white/70 rounded-lg border border-accent/30 space-y-3">
          <Search className="w-8 h-8 text-accent mx-auto" />
          <h3 className="text-base font-semibold text-text">No Discovered Jobs</h3>
          <p className="text-xs text-text/60">
            Click &quot;Sync Scout Live&quot; to fetch active software engineering roles from Greenhouse, Lever, and Adzuna.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {discoveredApps.map((app) => {
            const matchScorePercent = app.match_score
              ? Math.round(app.match_score * 100)
              : 75;

            return (
              <div
                key={app.id}
                className="p-5 rounded-lg bg-white border border-accent/30 space-y-4 hover:border-primary/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="text-sm font-semibold text-text">{app.role}</h3>
                      {app.is_demo && (
                        <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 border border-amber-300">
                          DEMO
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-text/70">{app.company} • {app.source}</p>
                  </div>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-primary/15 text-primary shrink-0">
                    {matchScorePercent}% Match
                  </span>
                </div>

                <p className="text-xs text-text/70 line-clamp-3 leading-relaxed">
                  {app.jd_text || 'Job description available.'}
                </p>

                <div className="pt-2 border-t border-accent/20 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-text/50">Status: {app.status}</span>
                  <Link
                    href={`/applications/${app.id}`}
                    className="inline-flex items-center space-x-1 text-xs text-primary font-medium hover:underline"
                  >
                    <span>View Application</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
