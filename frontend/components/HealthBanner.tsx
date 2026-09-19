'use client';

import React, { useEffect, useState } from 'react';
import { getHealth } from '@/lib/api';
import { HealthStatus } from '@/types';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';

export const HealthBanner: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let active = true;

    const check = () => {
      getHealth()
        .then((res) => {
          if (active) setHealth(res);
        })
        .catch(() => {
          if (active) {
            setHealth({
              status: 'degraded',
              services: { postgres: 'unhealthy', model_service: 'unhealthy', ollama: 'unhealthy' },
            });
          }
        });
    };

    check();
    const interval = setInterval(check, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  if (!health) return null;

  const isDegraded =
    health.status === 'degraded' ||
    health.services?.model_service === 'unhealthy' ||
    health.services?.ollama === 'unhealthy' ||
    health.services?.postgres === 'unhealthy';

  if (!isDegraded) return null;

  return (
    <div className="bg-amber-100 border-b border-amber-300 text-amber-900 px-4 py-2 text-xs font-medium flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
        <span>
          AI Model Service or Ollama local server is currently offline or degraded. Deterministic SQL fallbacks active.
        </span>
      </div>
      <span className="text-[10px] text-amber-800 font-mono">
        Services: Postgres [{health.services?.postgres || 'unknown'}], Model-Service [{health.services?.model_service || 'unknown'}], Ollama [{health.services?.ollama || 'unknown'}]
      </span>
    </div>
  );
};
