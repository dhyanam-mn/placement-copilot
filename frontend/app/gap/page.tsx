'use client';

import React, { useEffect, useState } from 'react';
import { getAggregateGapReport, getApplications, getGapReport, generateGapReport } from '@/lib/api';
import { Application, GapReport } from '@/types';
import { BarChart2, AlertCircle, RefreshCw, FileText, Loader2 } from 'lucide-react';

export default function GapPage() {
  const [aggregateReport, setAggregateReport] = useState<GapReport | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [perRowReport, setLogRowReport] = useState<GapReport | null>(null);
  const [loadingAgg, setLoadingAgg] = useState(true);
  const [loadingRow, setLoadingRow] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGapData = () => {
    setLoadingAgg(true);
    setError(null);
    Promise.all([
      getAggregateGapReport(),
      getApplications(),
    ])
      .then(([aggRes, appsRes]) => {
        setAggregateReport(aggRes);
        setApplications(appsRes.applications);
        const rejectedOrGhosted = appsRes.applications.filter(
          (a) => a.status === 'REJECTED' || a.status === 'GHOSTED'
        );
        if (rejectedOrGhosted.length > 0 && !selectedAppId) {
          setSelectedAppId(rejectedOrGhosted[0].id);
        }
      })
      .catch((err) => setError(err.message || 'Failed to fetch aggregate gap analysis'))
      .finally(() => setLoadingAgg(false));
  };

  useEffect(() => {
    loadGapData();
  }, []);

  useEffect(() => {
    if (!selectedAppId) return;
    setLoadingRow(true);
    getGapReport(selectedAppId)
      .then((res) => setLogRowReport(res))
      .catch(() => setLogRowReport(null))
      .finally(() => setLoadingRow(false));
  }, [selectedAppId]);

  const handleGenerateLogRow = async () => {
    if (!selectedAppId) return;
    setGenerating(true);
    try {
      const res = await generateGapReport(selectedAppId);
      setLogRowReport(res);
    } catch (err: any) {
      alert(`Error generating per-row gap report: ${err.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const roleTags = Object.entries(aggregateReport?.details?.by_role_tag || {});

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Gap Analysis Center
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Deterministic and LLM-synthesized gap reporting per-application and aggregated across unfulfilled applications.
          </p>
        </div>

        <button
          onClick={loadGapData}
          className="px-3.5 py-2 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors inline-flex items-center space-x-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Analysis</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs">
          Error: {error}
        </div>
      )}

      {/* Aggregate Report Section */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
        <div className="flex items-center space-x-2 border-b border-accent/20 pb-3">
          <BarChart2 className="w-4 h-4 text-primary" />
          <h3 className="text-xs font-semibold text-text">Weekly Aggregate Gap Analysis</h3>
        </div>

        {loadingAgg ? (
          <div className="p-8 text-center text-text/50 animate-pulse">Loading aggregate report...</div>
        ) : !aggregateReport ? (
          <p className="text-xs text-text/50">No aggregate report generated yet.</p>
        ) : (
          <div className="space-y-6">
            <div className="p-4 rounded-lg bg-bg border border-accent/30 space-y-2">
              <div className="flex items-center space-x-2 text-xs font-semibold text-text">
                <AlertCircle className="w-4 h-4 text-primary" />
                <span>Synthesis & Pattern Insight</span>
              </div>
              <p className="text-xs text-text/80 leading-relaxed font-normal">
                &quot;{aggregateReport.summary_text}&quot;
              </p>
            </div>

            {roleTags.length > 0 && (
              <div className="space-y-4">
                <h4 className="text-xs font-semibold text-text/70">Role Tag Stage Breakdown</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {roleTags.map(([role, stats]) => (
                    <div key={role} className="p-4 rounded border border-accent/20 bg-bg/30 space-y-2 text-xs">
                      <div className="font-semibold text-text">{role} Roles</div>
                      <div className="text-text/70">Total unfulfilled: {stats.total}</div>
                      <div className="text-text/60 text-[11px]">
                        OA stage: {stats.rejected_at_oa ?? stats.rejected_or_ghosted_at_oa ?? 0}
                      </div>
                      <div className="text-text/60 text-[11px]">
                        Interview stage: {stats.rejected_at_interview ?? stats.rejected_or_ghosted_at_interview ?? 0}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Per-Row Gap Report Section */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3 border-b border-accent/20 pb-3">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-primary" />
            <h3 className="text-xs font-semibold text-text">Per-Application Gap Report</h3>
          </div>

          <div className="flex items-center space-x-3">
            <select
              value={selectedAppId || ''}
              onChange={(e) => setSelectedAppId(Number(e.target.value))}
              className="p-1.5 text-xs text-text bg-white border border-accent/40 rounded focus:outline-none"
            >
              <option value="">Select Application...</option>
              {applications.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.company} — {app.role} ({app.status})
                </option>
              ))}
            </select>

            {selectedAppId && (
              <button
                onClick={handleGenerateLogRow}
                disabled={generating}
                className="px-3 py-1.5 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors inline-flex items-center space-x-1.5 disabled:opacity-50"
              >
                {generating ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                <span>{generating ? 'Generating...' : 'Generate Report'}</span>
              </button>
            )}
          </div>
        </div>

        {loadingRow ? (
          <div className="p-8 text-center text-text/50 animate-pulse">Loading per-row gap report...</div>
        ) : !perRowReport ? (
          <div className="p-6 text-center text-text/50 bg-bg/40 rounded border border-dashed border-accent/30 text-xs">
            {selectedAppId ? 'No per-row report generated for this application yet. Click "Generate Report" above.' : 'Select an application above to inspect or generate its gap report.'}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 rounded bg-bg border border-accent/30 text-xs space-y-2">
              <span className="font-semibold text-text">Summary:</span>
              <p className="text-text/80 leading-relaxed">&quot;{perRowReport.summary_text}&quot;</p>
            </div>

            {perRowReport.details && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div className="p-3 rounded bg-white border border-accent/20 space-y-1">
                  <span className="font-semibold text-text">Required Skills:</span>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {perRowReport.details.jd_required_skills?.map((s, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-bg text-text/80 text-[10px]">{s}</span>
                    )) || <span className="text-text/50">None</span>}
                  </div>
                </div>

                <div className="p-3 rounded bg-white border border-accent/20 space-y-1">
                  <span className="font-semibold text-emerald-800">Matched Skills:</span>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {perRowReport.details.matched_skills?.map((s, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px]">{s}</span>
                    )) || <span className="text-text/50">None</span>}
                  </div>
                </div>

                <div className="p-3 rounded bg-white border border-accent/20 space-y-1">
                  <span className="font-semibold text-red-800">Missing Skills:</span>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {perRowReport.details.missing_skills?.map((s, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-red-100 text-red-800 text-[10px]">{s}</span>
                    )) || <span className="text-emerald-700 text-[10px]">All skills matched!</span>}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
