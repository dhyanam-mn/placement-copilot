'use client';

import React, { useEffect, useState } from 'react';
import { Application, PrepRecommendationItem, PrepResponse } from '@/types';
import {
  getApplications,
  getPrepRecommendations,
  generatePrepRecommendations,
} from '@/lib/api';
import { BookOpen, ExternalLink, Clock, CheckCircle, RefreshCw, AlertCircle } from 'lucide-react';

export default function PrepPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [prepData, setPrepData] = useState<PrepResponse | null>(null);
  const [loadingApps, setLoadingApps] = useState(true);
  const [loadingPrep, setLoadingPrep] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getApplications()
      .then((data) => {
        setApplications(data.applications || []);
        if (data.applications && data.applications.length > 0) {
          // Default to first application or first interview application
          const interviewApp = data.applications.find((a) => a.status === 'INTERVIEW');
          setSelectedAppId(interviewApp ? interviewApp.id : data.applications[0].id);
        }
      })
      .catch((err) => {
        setError(err.message || 'Failed to load applications');
      })
      .finally(() => {
        setLoadingApps(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedAppId) return;

    setLoadingPrep(true);
    setError(null);
    getPrepRecommendations(selectedAppId)
      .then((res) => {
        setPrepData(res);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch recommendations');
        setPrepData(null);
      })
      .finally(() => {
        setLoadingPrep(false);
      });
  }, [selectedAppId]);

  const handleRegenerate = async () => {
    if (!selectedAppId) return;
    setRegenerating(true);
    setError(null);
    try {
      const res = await generatePrepRecommendations(selectedAppId);
      setPrepData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to regenerate study recommendations');
    } finally {
      setRegenerating(false);
    }
  };

  const selectedApp = applications.find((a) => a.id === selectedAppId);

  return (
    <div className="max-w-5xl space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Interview Prep Agent</h1>
          <p className="text-sm text-text/60 mt-1">
            Tailored learning resources matched to JD skill gaps for active interview roles.
          </p>
        </div>

        {/* Application Selector */}
        {applications.length > 0 && (
          <div className="flex items-center space-x-3">
            <label className="text-xs font-medium text-text/70">Application:</label>
            <select
              value={selectedAppId || ''}
              onChange={(e) => setSelectedAppId(Number(e.target.value))}
              className="p-2 text-xs bg-white border border-accent/40 rounded shadow-sm focus:outline-none focus:border-primary text-text"
            >
              {applications.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.company} - {app.role} ({app.status})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {loadingApps ? (
        <div className="p-8 text-center text-sm text-text/60">Loading applications pipeline...</div>
      ) : applications.length === 0 ? (
        <div className="p-8 rounded-lg bg-white border border-accent/30 text-center space-y-2">
          <BookOpen className="w-8 h-8 text-text/30 mx-auto" />
          <h3 className="text-sm font-semibold text-text">No Applications Found</h3>
          <p className="text-xs text-text/60">
            Create or discover applications to view tailored prep recommendations.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Selected Application Context Banner */}
          {selectedApp && (
            <div className="p-4 rounded-lg bg-white border border-accent/30 flex items-center justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-base font-semibold text-text">{selectedApp.role}</h2>
                  <span className="text-xs text-text/60">at</span>
                  <span className="text-sm font-medium text-text">{selectedApp.company}</span>
                  {selectedApp.is_demo && (
                    <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 border border-amber-300">
                      DEMO
                    </span>
                  )}
                </div>
                <p className="text-xs text-text/50 mt-0.5">
                  Source: {selectedApp.source} • Status: {selectedApp.status}
                </p>
              </div>

              <button
                onClick={handleRegenerate}
                disabled={regenerating || loadingPrep}
                className="inline-flex items-center space-x-2 px-3.5 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors disabled:opacity-50 shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
                <span>{regenerating ? 'Regenerating...' : 'Regenerate Study Plan'}</span>
              </button>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div className="p-4 rounded-lg bg-rejected/10 border border-rejected/30 flex items-center space-x-3 text-rejected text-xs">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Prep Recommendations List */}
          {loadingPrep ? (
            <div className="p-8 text-center text-sm text-text/60">
              Generating tailored prep recommendations with Ollama & SQL ranker...
            </div>
          ) : !prepData || !prepData.recommendations || prepData.recommendations.length === 0 ? (
            <div className="p-8 rounded-lg bg-white border border-accent/30 text-center space-y-2">
              <BookOpen className="w-8 h-8 text-text/30 mx-auto" />
              <h3 className="text-sm font-semibold text-text">No Recommendations Available</h3>
              <p className="text-xs text-text/60 max-w-md mx-auto">
                No prep recommendations exist for this application yet. Click &quot;Regenerate Study Plan&quot; to extract skills and rank relevant learning resources.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-text tracking-tight">
                Recommended Learning Resources ({prepData.recommendations.length})
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {prepData.recommendations.map((rec: PrepRecommendationItem, idx: number) => (
                  <div
                    key={rec.id || idx}
                    className="p-5 rounded-lg bg-white border border-accent/30 flex flex-col justify-between space-y-4 hover:border-primary/50 transition-colors"
                  >
                    <div className="space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-[11px] font-bold text-primary px-2 py-0.5 rounded bg-primary/10">
                          #{idx + 1} Recommendation
                        </span>
                        {rec.est_hours && (
                          <span className="inline-flex items-center space-x-1 text-xs text-text/60 bg-bg px-2 py-0.5 rounded">
                            <Clock className="w-3 h-3 text-text/40" />
                            <span>{rec.est_hours} hrs</span>
                          </span>
                        )}
                      </div>

                      <h4 className="text-sm font-semibold text-text leading-snug">{rec.title}</h4>
                      <p className="text-xs text-text/70 leading-relaxed">{rec.reason}</p>
                    </div>

                    <div className="pt-3 border-t border-accent/20 flex items-center justify-between text-xs">
                      {rec.verified_at ? (
                        <span className="inline-flex items-center space-x-1 text-[11px] text-emerald-700">
                          <CheckCircle className="w-3 h-3 text-emerald-600" />
                          <span>Verified {new Date(rec.verified_at).toLocaleDateString()}</span>
                        </span>
                      ) : (
                        <span className="text-[11px] text-text/40">URL Active</span>
                      )}

                      <a
                        href={rec.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 font-medium text-primary hover:underline"
                      >
                        <span>Open Link</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
