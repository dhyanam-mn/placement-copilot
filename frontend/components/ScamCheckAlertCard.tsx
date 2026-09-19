'use client';

import React, { useEffect, useState } from 'react';
import { runScamCheck } from '@/lib/api';
import { ShieldAlert, ShieldCheck, Shield } from 'lucide-react';

interface ScamCheckAlertCardProps {
  applicationId?: number;
}

interface ScamCheckItem {
  id: number;
  risk_score: number;
  flagged_reasons: string[];
  explanation_text?: string | null;
  recruiter_name: string;
  claimed_company: string;
  recruiter_domain: string;
}

const INITIAL_RECRUITERS = [
  {
    recruiter_name: 'Robert Miller',
    claimed_company: 'Meta Recruiting Operations',
    recruiter_domain: 'meta-talent.io',
  },
  {
    recruiter_name: 'Stark Global Solutions',
    claimed_company: 'External Talent Agency',
    recruiter_domain: 'starkglobal-hr.co',
  },
  {
    recruiter_name: 'TechFlow Systems',
    claimed_company: 'Series B Startup',
    recruiter_domain: 'techflow.dev',
  },
];

function getRiskLevel(score: number): 'HIGH' | 'MEDIUM' | 'LOW' {
  if (score >= 0.7) return 'HIGH';
  if (score >= 0.3) return 'MEDIUM';
  return 'LOW';
}

export const ScamCheckAlertCard: React.FC<ScamCheckAlertCardProps> = ({
  applicationId = 1,
}) => {
  const [items, setItems] = useState<ScamCheckItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all(
      INITIAL_RECRUITERS.map((r) =>
        runScamCheck(applicationId, {
          recruiter_name: r.recruiter_name,
          recruiter_domain: r.recruiter_domain,
          claimed_company: r.claimed_company,
        }).then((res) => ({
          ...res,
          recruiter_name: r.recruiter_name,
          claimed_company: r.claimed_company,
          recruiter_domain: r.recruiter_domain,
        }))
      )
    )
      .then((results) => {
        if (!cancelled) setItems(results);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to run scam checks');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [applicationId]);

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Verification Center
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Running verification checks on recruiter contacts…
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Verification Center
          </h2>
          <p className="text-sm text-rejected mt-1">
            Couldn&apos;t reach the backend: {error}. Is it running on{' '}
            {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}?
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Verification Center
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Objective risk assessment for ongoing recruitment communications.
          </p>
        </div>

        <button
          type="button"
          className="px-3.5 py-2 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors"
        >
          Security Settings
        </button>
      </div>

      {/* Grid of Alert Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-start">
        {items.map((item, index) => {
          const riskLevel = getRiskLevel(item.risk_score);
          let badgeBg = 'bg-primary/15 text-primary';
          let borderAccent = 'border-accent/30';
          let RiskIcon = ShieldCheck;

          if (riskLevel === 'HIGH') {
            badgeBg = 'bg-rejected/15 text-rejected';
            borderAccent = 'border-rejected/30';
            RiskIcon = ShieldAlert;
          } else if (riskLevel === 'MEDIUM') {
            badgeBg = 'bg-accent/25 text-[#73684a]';
            borderAccent = 'border-accent/40';
            RiskIcon = Shield;
          }

          return (
            <div
              key={item.id || index}
              className={`p-6 rounded-lg bg-white border ${borderAccent} space-y-5`}
            >
              {/* Card Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-text">{item.recruiter_name}</h3>
                  <p className="text-xs text-text/60">{item.claimed_company} • {item.recruiter_domain}</p>
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded tracking-wide ${badgeBg}`}>
                  {riskLevel === 'HIGH' ? 'High Risk' : riskLevel === 'MEDIUM' ? 'Medium Risk' : 'Low Risk'}
                </span>
              </div>

              {/* Evidence Analysis */}
              <div className="space-y-2">
                <h4 className="text-[11px] font-semibold text-text/50 tracking-wider">
                  Evidence Analysis
                </h4>
                {item.flagged_reasons && item.flagged_reasons.length > 0 ? (
                  <ul className="list-disc list-outside ml-4 text-xs text-text/70 space-y-2 leading-relaxed">
                    {item.flagged_reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-text/60">No suspicious fraud indicators detected.</p>
                )}
              </div>

              {/* Explanation Callout */}
              {item.explanation_text && (
                <div className="p-3 rounded bg-bg text-xs text-text/80 leading-relaxed border border-accent/30">
                  <span className="font-medium text-text">Model summary: </span>
                  {item.explanation_text}
                </div>
              )}

              {/* Card Actions */}
              <div className="pt-2 border-t border-accent/20 flex items-center justify-between text-xs">
                {riskLevel === 'HIGH' && (
                  <>
                    <button
                      type="button"
                      className="text-rejected font-medium hover:underline"
                    >
                      Flag as Fraud
                    </button>
                    <button
                      type="button"
                      className="text-text/60 hover:text-text"
                    >
                      Ignore
                    </button>
                  </>
                )}
                {riskLevel === 'MEDIUM' && (
                  <>
                    <button
                      type="button"
                      className="text-text font-medium hover:underline"
                    >
                      Verify Manually
                    </button>
                    <button
                      type="button"
                      className="text-text/60 hover:text-text"
                    >
                      Archive
                    </button>
                  </>
                )}
                {riskLevel === 'LOW' && (
                  <button
                    type="button"
                    className="w-full py-1.5 text-center text-primary font-medium border border-primary/20 rounded hover:bg-primary/5 transition-colors"
                  >
                    Trusted Sender
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="pt-6 border-t border-accent/30 flex items-center justify-between text-xs text-text/50">
        <span>Scam patterns updated 14m ago • Verified 1,402 recruiters today</span>
        <div className="flex space-x-4">
          <button type="button" className="hover:text-text">Security Policy</button>
          <button type="button" className="hover:text-text">Report False Positive</button>
        </div>
      </div>
    </div>
  );
};
