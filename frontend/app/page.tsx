'use client';

import React, { useState } from 'react';
import { Sidebar, NavTab } from '@/components/Sidebar';
import { KanbanBoard } from '@/components/KanbanBoard';
import { ActivityFeed } from '@/components/ActivityFeed';
import { ResumeTailoringView } from '@/components/ResumeTailoringView';
import { ScamCheckAlertCard } from '@/components/ScamCheckAlertCard';
import { PrepChat } from '@/components/PrepChat';
import { GapReportView } from '@/components/GapReportView';
import { Application } from '@/types';

export default function DashboardPage() {
  const [currentTab, setCurrentTab] = useState<NavTab>('pipeline');
  const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);

  const handleSelectApplication = (app: Application) => {
    setSelectedApplication(app);
    if (app.status === 'READY_TO_APPLY' || app.status === 'DISCOVERED') {
      setCurrentTab('tailoring');
    } else if (app.status === 'GHOSTED' || app.status === 'REJECTED') {
      setCurrentTab('gap-report');
    } else if (app.status === 'INTERVIEW' || app.status === 'OA_INVITE') {
      setCurrentTab('prep');
    }
  };

  return (
    <div className="flex min-h-screen bg-bg">
      {/* Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
        }}
      />

      {/* Main Content Area */}
      <main className="flex-1 p-8 lg:p-12 overflow-y-auto max-h-screen">
        {currentTab === 'pipeline' && (
          <KanbanBoard onSelectApplication={handleSelectApplication} />
        )}

        {currentTab === 'tailoring' && <ResumeTailoringView />}

        {currentTab === 'activity' && <ActivityFeed />}

        {currentTab === 'scam-check' && <ScamCheckAlertCard />}

        {currentTab === 'prep' && <PrepChat />}

        {currentTab === 'gap-report' && <GapReportView />}
      </main>
    </div>
  );
}
