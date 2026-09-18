'use client';

import React from 'react';
import { mockScamChecks } from '@/data/mockData';
import { ShieldAlert, ShieldCheck, Shield } from 'lucide-react';

export const ScamCheckAlertCard: React.FC = () => {
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
        {mockScamChecks.map((item) => {
          let badgeBg = 'bg-primary/15 text-primary';
          let borderAccent = 'border-accent/30';
          let RiskIcon = ShieldCheck;

          if (item.risk_level === 'HIGH') {
            badgeBg = 'bg-rejected/15 text-rejected';
            borderAccent = 'border-rejected/30';
            RiskIcon = ShieldAlert;
          } else if (item.risk_level === 'MEDIUM') {
            badgeBg = 'bg-accent/25 text-[#73684a]';
            borderAccent = 'border-accent/40';
            RiskIcon = Shield;
          }

          return (
            <div
              key={item.id}
              className={`p-6 rounded-lg bg-white border ${borderAccent} space-y-5`}
            >
              {/* Card Header */}
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-text">{item.recruiter_name}</h3>
                  <p className="text-xs text-text/60">{item.claimed_company}</p>
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded tracking-wide ${badgeBg}`}>
                  {item.risk_level === 'HIGH' ? 'High Risk' : item.risk_level === 'MEDIUM' ? 'Medium Risk' : 'Low Risk'}
                </span>
              </div>

              {/* Evidence Analysis */}
              <div className="space-y-2">
                <h4 className="text-[11px] font-semibold text-text/50 tracking-wider">
                  Evidence Analysis
                </h4>
                <ul className="list-disc list-outside ml-4 text-xs text-text/70 space-y-2 leading-relaxed">
                  {item.flagged_reasons.map((reason, idx) => (
                    <li key={idx}>{reason}</li>
                  ))}
                </ul>
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
                {item.risk_level === 'HIGH' && (
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
                {item.risk_level === 'MEDIUM' && (
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
                {item.risk_level === 'LOW' && (
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
