'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  getApplication,
  getApplicationEvents,
  getStoredScamCheck,
  confirmApplicationApplied,
  tailorResume,
} from '@/lib/api';
import { Application, StatusEvent, ScamCheck, TailoredResume } from '@/types';
import { ResumeTailoringView } from '@/components/ResumeTailoringView';
import {
  CheckCircle,
  FileText,
  History,
  ShieldAlert,
  ArrowLeft,
  Download,
  Loader2,
  Sparkles,
} from 'lucide-react';

export default function ApplicationDetailPage() {
  const params = useParams();
  const appId = Number(params?.id);

  const [application, setApplication] = useState<Application | null>(null);
  const [events, setEvents] = useState<StatusEvent[]>([]);
  const [scamCheck, setScamCheck] = useState<ScamCheck | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const loadData = () => {
    if (!appId || isNaN(appId)) return;
    setLoading(true);
    setError(null);

    Promise.all([
      getApplication(appId),
      getApplicationEvents(appId).catch(() => ({ events: [] })),
      getStoredScamCheck(appId).catch(() => null),
    ])
      .then(([appRes, eventsRes, scamRes]) => {
        setApplication(appRes);
        setEvents(eventsRes.events || []);
        setScamCheck(scamRes);
      })
      .catch((err) => setError(err.message || 'Failed to load application details'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [appId]);

  const handleConfirmApplied = async () => {
    if (!application) return;
    setConfirming(true);
    try {
      const updated = await confirmApplicationApplied(application.id);
      setApplication(updated);
      loadData();
      alert('Confirmed! Application status set to APPLIED.');
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setConfirming(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="p-12 text-center text-text/50 bg-white/50 rounded-lg border border-accent/20 animate-pulse">
          Loading application details...
        </div>
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="space-y-8">
        <Link href="/" className="inline-flex items-center space-x-1.5 text-xs text-text/60 hover:text-text">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dashboard</span>
        </Link>
        <div className="p-6 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs">
          Error: {error || 'Application not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Top Bar */}
      <div className="flex items-center justify-between">
        <Link href="/" className="inline-flex items-center space-x-1.5 text-xs text-text/60 hover:text-text">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Dashboard</span>
        </Link>

        {application.status === 'READY_TO_APPLY' && (
          <button
            onClick={handleConfirmApplied}
            disabled={confirming}
            className="px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors inline-flex items-center space-x-2 disabled:opacity-50"
          >
            {confirming ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
            <span>Confirm I Applied</span>
          </button>
        )}
      </div>

      {/* Hero Card */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-4">
        <div className="flex items-start justify-between flex-wrap gap-2">
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-semibold text-text">{application.role}</h1>
              {application.is_demo && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
                  DEMO
                </span>
              )}
            </div>
            <p className="text-sm text-text/70 mt-0.5">{application.company} • Source: {application.source}</p>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-xs font-semibold px-2.5 py-1 rounded bg-bg text-text/80 border border-accent/30">
              Status: {application.status}
            </span>
            {application.status_source && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                {application.status_source}
              </span>
            )}
            {application.match_score != null && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded bg-primary/15 text-primary">
                {Math.round(application.match_score * 100)}% Match
              </span>
            )}
          </div>
        </div>

        <p className="text-xs text-text/80 leading-relaxed pt-2 border-t border-accent/20">
          {application.jd_text}
        </p>
      </div>

      {/* Scam Check Card (if available) */}
      {scamCheck && (
        <div className="p-5 rounded-lg bg-white border border-accent/30 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <h3 className="text-xs font-semibold text-text">Scam Check Evidence</h3>
            </div>
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-amber-100 text-amber-800">
              Risk Score: {scamCheck.risk_score}
            </span>
          </div>

          {scamCheck.flagged_reasons && scamCheck.flagged_reasons.length > 0 && (
            <ul className="list-disc list-outside ml-4 text-xs text-text/70 space-y-1">
              {scamCheck.flagged_reasons.map((r, idx) => (
                <li key={idx}>{r}</li>
              ))}
            </ul>
          )}

          {scamCheck.explanation_text && (
            <p className="text-xs text-text/80 italic p-2.5 rounded bg-bg border border-accent/20">
              &quot;{scamCheck.explanation_text}&quot;
            </p>
          )}
        </div>
      )}

      {/* Tailored Resume View */}
      <ResumeTailoringView applicationId={application.id} />

      {/* Status Transition History Timeline */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-4">
        <div className="flex items-center space-x-2 pb-2 border-b border-accent/20">
          <History className="w-4 h-4 text-primary" />
          <h3 className="text-xs font-semibold text-text">Status Event History</h3>
        </div>

        {events.length === 0 ? (
          <p className="text-xs text-text/50">No status transition events recorded yet.</p>
        ) : (
          <div className="space-y-3">
            {events.map((evt) => (
              <div key={evt.id} className="flex items-center justify-between text-xs py-1.5 border-b border-accent/15">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-text">{evt.old_status || 'CREATED'} → {evt.new_status}</span>
                  {evt.event_source && (
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-bg text-text/70 border border-accent/20">
                      {evt.event_source}
                    </span>
                  )}
                </div>
                <span className="text-[11px] text-text/50">
                  {new Date(evt.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
