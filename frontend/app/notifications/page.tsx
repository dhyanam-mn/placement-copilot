'use client';

import React, { useEffect, useState } from 'react';
import { getNotifications, markNotificationRead } from '@/lib/api';
import { Notification } from '@/types';
import { Bell, Check, Filter, AlertCircle, RefreshCw } from 'lucide-react';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = () => {
    setLoading(true);
    setError(null);
    getNotifications(unreadOnly)
      .then((res) => setNotifications(res.notifications))
      .catch((err) => setError(err.message || 'Failed to fetch notifications'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadNotifications();
  }, [unreadOnly]);

  const handleMarkRead = async (id: number) => {
    try {
      await markNotificationRead(id);
      loadNotifications();
    } catch (err: any) {
      alert(`Failed to mark read: ${err.message}`);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Notifications Feed
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Real system feed for status transitions (GHOSTED, REJECTED), gap report alerts, and scam checks.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-xs text-text cursor-pointer select-none bg-white px-3 py-2 rounded border border-accent/40">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => setUnreadOnly(e.target.checked)}
              className="rounded text-primary focus:ring-primary"
            />
            <span>Unread Only</span>
          </label>
          <button
            onClick={loadNotifications}
            className="px-3.5 py-2 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors inline-flex items-center space-x-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs">
          Error loading notifications: {error}
        </div>
      )}

      {loading ? (
        <div className="p-12 text-center text-text/50 bg-white/50 rounded-lg border border-accent/20 animate-pulse">
          Loading notification feed...
        </div>
      ) : notifications.length === 0 ? (
        <div className="p-12 text-center bg-white/70 rounded-lg border border-accent/30 space-y-3">
          <Bell className="w-8 h-8 text-accent mx-auto" />
          <h3 className="text-base font-semibold text-text">No Notifications</h3>
          <p className="text-xs text-text/60">
            {unreadOnly ? 'No unread notifications present.' : 'System notification log is clear.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map((notif) => {
            const isAlert = notif.type.includes('GHOSTED') || notif.type.includes('REJECTED') || notif.type.includes('scam');
            let borderClass = 'border-accent/30 bg-white';
            if (isAlert) {
              borderClass = 'border-amber-300 bg-amber-50/40';
            }

            return (
              <div
                key={notif.id}
                className={`p-4 rounded-lg border ${borderClass} flex items-start justify-between gap-4 transition-colors`}
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-text">{notif.type}</span>
                    {!notif.read && (
                      <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-primary/15 text-primary">
                        NEW
                      </span>
                    )}
                    {notif.is_demo && (
                      <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 border border-amber-300">
                        DEMO
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text/80 leading-relaxed">{notif.content}</p>
                  <p className="text-[10px] text-text/50 pt-1">
                    {new Date(notif.created_at).toLocaleString()}
                  </p>
                </div>

                {!notif.read && (
                  <button
                    onClick={() => handleMarkRead(notif.id)}
                    className="px-2.5 py-1 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-bg transition-colors inline-flex items-center space-x-1 shrink-0"
                  >
                    <Check className="w-3 h-3 text-primary" />
                    <span>Mark Read</span>
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
