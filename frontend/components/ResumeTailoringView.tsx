'use client';

import React, { useEffect, useState } from 'react';
import { Application } from '@/types';
import { getApplication, tailorResume } from '@/lib/api';
import { Download, Check } from 'lucide-react';

interface ResumeTailoringViewProps {
  applicationId?: number;
}

interface TailorResponseData {
  tailored_resume_id: number;
  resume_data: {
    ordered_bullets: Array<{
      project: string;
      bullet: string;
      score: number;
    }>;
  };
}

const BASE_RESUME = {
  name: 'Alex Chen',
  contact: 'alex.chen@email.com • San Francisco, CA • linkedin.com/in/alexchen',
  experience: [
    {
      role: 'Frontend Developer Intern',
      company: 'TechCorp',
      period: 'May 2023 – Aug 2023',
      bullets: [
        'Developed responsive UI components using React and Tailwind CSS for a dashboard used by 50k+ daily users.',
        'Optimized bundle sizes by 15% through code splitting and tree shaking techniques.',
        'Collaborated with design team to implement a new design system across the legacy platform.',
      ],
    },
    {
      role: 'Open Source Contributor',
      company: 'Distributed DB',
      period: 'Jan 2023 – Present',
      bullets: [
        'Implemented a custom caching layer in Go to reduce database latency by 200ms.',
        'Documented API endpoints and provided code samples for the developer community.',
        'Fixed critical race condition bugs in the networking module using advanced debugging tools.',
      ],
    },
  ],
  projects: [
    {
      title: 'Personal Portfolio & Blog',
      desc: 'Built with Next.js and MDX, featuring high SEO and accessibility scores.',
    },
    {
      title: 'Real-time Chat App',
      desc: 'Node.js and Socket.io implementation for secure, low-latency communication.',
    },
  ],
  skills: {
    core: ['JavaScript (ES6+)', 'TypeScript', 'React', 'Next.js', 'Node.js', 'Go', 'Python', 'SQL', 'Git', 'Docker', 'AWS'],
  },
};

export const ResumeTailoringView: React.FC<ResumeTailoringViewProps> = ({
  applicationId = 1,
}) => {
  const [application, setApplication] = useState<Application | null>(null);
  const [tailorData, setTailorData] = useState<TailorResponseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      getApplication(applicationId).catch(() => null),
      tailorResume(applicationId),
    ])
      .then(([appRes, tailorRes]) => {
        if (!cancelled) {
          if (appRes) setApplication(appRes);
          setTailorData(tailorRes);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to tailor resume');
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
        <h2 className="text-2xl font-semibold tracking-tight text-text">
          Resume Tailoring
        </h2>
        <p className="text-sm text-text/60">Tailoring resume with backend...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <h2 className="text-2xl font-semibold tracking-tight text-text">
          Resume Tailoring
        </h2>
        <p className="text-sm text-rejected">
          Couldn&apos;t reach the backend: {error}. Is it running on{' '}
          {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}?
        </p>
      </div>
    );
  }

  const companyName = application?.company || 'Target Company';
  const roleTitle = application?.role || 'Target Role';
  const matchScorePercent = application?.match_score
    ? Math.round(application.match_score * 100)
    : 85;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Resume Tailoring
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Aligning &quot;{BASE_RESUME.name}&quot; with &quot;{companyName} — {roleTitle}&quot;.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            type="button"
            className="inline-flex items-center space-x-2 px-3.5 py-2 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download PDF</span>
          </button>
          <button
            type="button"
            className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Apply with Tailored Resume</span>
          </button>
        </div>
      </div>

      {/* 3-Column Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Column 1: Base Resume */}
        <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
          <div className="flex items-baseline justify-between border-b border-accent/20 pb-3">
            <h3 className="text-xs font-semibold text-text">Base Resume</h3>
            <span className="text-[11px] text-text/50">Updated 2 days ago</span>
          </div>

          <div className="space-y-4">
            <div className="text-center pb-2 border-b border-accent/20">
              <h4 className="text-base font-semibold text-text">{BASE_RESUME.name}</h4>
              <p className="text-xs text-text/60 mt-0.5">{BASE_RESUME.contact}</p>
            </div>

            <div className="space-y-3">
              <h5 className="text-xs font-semibold text-text/70">Experience</h5>
              {BASE_RESUME.experience.map((exp, idx) => (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-medium text-text">
                    <span>{exp.role} • {exp.company}</span>
                    <span className="text-text/50">{exp.period}</span>
                  </div>
                  <ul className="list-disc list-outside ml-4 text-xs text-text/70 space-y-1 leading-relaxed">
                    {exp.bullets.map((b, bIdx) => (
                      <li key={bIdx}>{b}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="space-y-3 pt-2">
              <h5 className="text-xs font-semibold text-text/70">Projects</h5>
              {BASE_RESUME.projects.map((proj, pIdx) => (
                <div key={pIdx} className="text-xs space-y-0.5">
                  <p className="font-medium text-text">{proj.title}</p>
                  <p className="text-text/70 leading-relaxed">{proj.desc}</p>
                </div>
              ))}
            </div>

            <div className="space-y-1.5 pt-2">
              <h5 className="text-xs font-semibold text-text/70">Skills</h5>
              <p className="text-xs text-text/70 leading-relaxed">
                {BASE_RESUME.skills.core.join(', ')}
              </p>
            </div>
          </div>
        </div>

        {/* Column 2: Job Description */}
        <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
          <div className="flex items-baseline justify-between border-b border-accent/20 pb-3">
            <h3 className="text-xs font-semibold text-text">
              Job Description: {companyName}
            </h3>
            <span className="text-[11px] text-text/50">{roleTitle}</span>
          </div>

          <div className="space-y-5">
            <div className="space-y-1.5">
              <h5 className="text-xs font-semibold text-text/70">About the role</h5>
              <p className="text-xs text-text/70 leading-relaxed">
                {application?.jd_text ||
                  `We are hiring a ${roleTitle} at ${companyName}. Key focus on high quality engineering, scalable systems, and collaboration.`}
              </p>
            </div>
          </div>
        </div>

        {/* Column 3: Tailored Resume */}
        <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
          <div className="flex items-baseline justify-between border-b border-accent/20 pb-3">
            <h3 className="text-xs font-semibold text-text">Tailored Resume</h3>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-primary/15 text-primary">
              {matchScorePercent}% Match
            </span>
          </div>

          <div className="space-y-4">
            <div className="text-center pb-2 border-b border-accent/20">
              <h4 className="text-base font-semibold text-text">{BASE_RESUME.name}</h4>
              <p className="text-xs text-text/60 mt-0.5">{BASE_RESUME.contact}</p>
            </div>

            <div className="space-y-3">
              <h5 className="text-xs font-semibold text-text/70">
                Ordered Bullets (Relevance Scored)
              </h5>
              <div className="space-y-3">
                {tailorData?.resume_data?.ordered_bullets?.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded border border-accent/20 bg-bg/40 space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-text">{item.project}</span>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-primary/15 text-primary">
                        Score: {item.score}
                      </span>
                    </div>
                    <p className="text-xs text-text/80 leading-relaxed">• {item.bullet}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
