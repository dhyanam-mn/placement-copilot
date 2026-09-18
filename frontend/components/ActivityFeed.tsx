'use client';

import React from 'react';
import { mockActivityFeed } from '@/data/mockData';
import { CheckCircle2 } from 'lucide-react';

export const ActivityFeed: React.FC = () => {
  const dateGroups: Array<'TODAY' | 'YESTERDAY' | 'SEPTEMBER 15' | 'SEPTEMBER 12'> = [
    'TODAY',
    'YESTERDAY',
    'SEPTEMBER 15',
    'SEPTEMBER 12',
  ];

  const groupLabels: Record<string, string> = {
    TODAY: 'Today',
    YESTERDAY: 'Yesterday',
    'SEPTEMBER 15': 'September 15',
    'SEPTEMBER 12': 'September 12',
  };

  return (
    <div className="max-w-4xl space-y-10">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">Activity Feed</h2>
          <p className="text-sm text-text/60 mt-1">
            A quiet chronological log of what your copilot agents have been doing.
          </p>
        </div>

        <div className="flex items-center space-x-1.5 text-xs text-text/70 bg-white/60 px-3 py-1.5 rounded border border-accent/30">
          <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
          <span>Copilot Synced</span>
        </div>
      </div>

      {/* Grouped Logs */}
      <div className="space-y-8">
        {dateGroups.map((group) => {
          const events = mockActivityFeed.filter((evt) => evt.date_group === group);
          if (events.length === 0) return null;

          return (
            <div key={group} className="space-y-4">
              <h3 className="text-xs font-semibold text-text/50 tracking-wider">
                {groupLabels[group]}
              </h3>

              <div className="space-y-3">
                {events.map((evt) => (
                  <div
                    key={evt.id}
                    className="flex items-center justify-between py-2 border-b border-accent/20 text-sm"
                  >
                    <div className="flex items-center space-x-3">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: evt.color }}
                      />
                      <span className="text-text/90 font-normal">{evt.text}</span>
                    </div>
                    <span className="text-xs text-text/50 shrink-0 ml-4">
                      {evt.timestamp}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
