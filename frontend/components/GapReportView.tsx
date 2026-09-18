'use client';

import React from 'react';
import { mockAggregateGapReport } from '@/data/mockData';
import { AlertCircle, BarChart2 } from 'lucide-react';

export const GapReportView: React.FC = () => {
  const roleTags = Object.entries(
    mockAggregateGapReport.details.by_role_tag || {}
  );

  const perRowExamples = [
    {
      company: 'Zeta Suite',
      role: 'Software Engineer',
      missing: ['cloud deployment'],
      matched: ['React', 'Node.js', 'MongoDB'],
      reason: 'JD required cloud deployment experience — not present in matched resume skills.',
    },
    {
      company: 'Skylark Labs',
      role: 'ML Engineer Intern',
      missing: ['edge inference'],
      matched: ['YOLO', 'model deployment'],
      reason: 'JD required edge inference deployment experience — not present in matched resume skills.',
    },
    {
      company: 'NoBroker',
      role: 'SDE Intern',
      missing: ['system design'],
      matched: ['DSA', 'SQL'],
      reason: 'JD required system design fundamentals — not present in matched resume skills.',
    },
    {
      company: 'CRED',
      role: 'SDE-1',
      missing: ['distributed systems'],
      matched: ['DSA', 'system design'],
      reason: 'JD required distributed systems experience — not present in matched resume skills.',
    },
  ];

  return (
    <div className="max-w-4xl space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-text">
          Aggregate Gap Analysis
        </h2>
        <p className="text-sm text-text/60 mt-1">
          Patterns across unfulfilled applications to inform future skill investments.
        </p>
      </div>

      {/* Plain-English Summary Callout */}
      <div className="p-5 rounded-lg bg-white border border-accent/40 space-y-2">
        <div className="flex items-center space-x-2 text-xs font-semibold text-text">
          <AlertCircle className="w-4 h-4 text-primary" />
          <span>Synthesis & Insight</span>
        </div>
        <p className="text-sm text-text/80 leading-relaxed font-normal">
          &quot;{mockAggregateGapReport.summary_text}&quot;
        </p>
      </div>

      {/* Bar Chart: Stage × Role Tag */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
        <div className="flex items-center justify-between border-b border-accent/20 pb-3">
          <div className="flex items-center space-x-2">
            <BarChart2 className="w-4 h-4 text-accent" />
            <h3 className="text-xs font-semibold text-text">
              Rejections & Ghostings by Role Tag and Stage
            </h3>
          </div>
          {/* Legend */}
          <div className="flex items-center space-x-4 text-xs">
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-oa" />
              <span className="text-text/70">OA stage</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-interview" />
              <span className="text-text/70">Interview stage</span>
            </div>
          </div>
        </div>

        {/* Role Rows */}
        <div className="space-y-6">
          {roleTags.map(([role, stats]) => {
            const oaCount = stats.rejected_or_ghosted_at_oa || 0;
            const interviewCount = stats.rejected_or_ghosted_at_interview || 0;
            const maxVal = 4; // for relative bar widths

            return (
              <div key={role} className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-text">{role} Roles</span>
                  <span className="text-text/50">
                    Total unfulfilled: {stats.total}
                  </span>
                </div>

                {/* Bars */}
                <div className="space-y-1.5">
                  <div className="flex items-center space-x-3 text-xs">
                    <span className="w-20 text-text/60 shrink-0">OA Stage:</span>
                    <div className="flex-1 bg-bg h-4 rounded overflow-hidden">
                      <div
                        className="bg-oa h-full rounded transition-all duration-300"
                        style={{ width: `${(oaCount / maxVal) * 100}%` }}
                      />
                    </div>
                    <span className="w-6 text-right font-medium text-text">
                      {oaCount}
                    </span>
                  </div>

                  <div className="flex items-center space-x-3 text-xs">
                    <span className="w-20 text-text/60 shrink-0">Interview:</span>
                    <div className="flex-1 bg-bg h-4 rounded overflow-hidden">
                      <div
                        className="bg-interview h-full rounded transition-all duration-300"
                        style={{ width: `${(interviewCount / maxVal) * 100}%` }}
                      />
                    </div>
                    <span className="w-6 text-right font-medium text-text">
                      {interviewCount}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Per-Row Gap Reports Breakdown */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-text/60 tracking-wider">
          Per-Row Skill Deficit Details
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {perRowExamples.map((item, idx) => (
            <div
              key={idx}
              className="p-4 rounded-lg bg-white border border-accent/30 space-y-2"
            >
              <div className="flex justify-between items-baseline">
                <h4 className="text-xs font-semibold text-text">{item.company}</h4>
                <span className="text-[11px] text-text/50">{item.role}</span>
              </div>
              <p className="text-xs text-text/70 leading-relaxed">{item.reason}</p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <span className="text-[10px] text-rejected font-medium">Missing:</span>
                {item.missing.map((sk, sIdx) => (
                  <span
                    key={sIdx}
                    className="text-[10px] font-medium px-2 py-0.5 rounded bg-rejected/10 text-rejected"
                  >
                    {sk}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
