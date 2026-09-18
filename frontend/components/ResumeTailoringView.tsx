'use client';

import React from 'react';
import {
  mockBaseResume,
  mockJobDescription,
  mockTailoredResume,
} from '@/data/mockData';
import { Download, Check } from 'lucide-react';

export const ResumeTailoringView: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Resume Tailoring
          </h2>
          <p className="text-sm text-text/60 mt-1">
            Aligning &quot;{mockBaseResume.name} - SWE&quot; with &quot;{mockJobDescription.company} {mockJobDescription.role}&quot;.
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
              <h4 className="text-base font-semibold text-text">{mockBaseResume.name}</h4>
              <p className="text-xs text-text/60 mt-0.5">{mockBaseResume.contact}</p>
            </div>

            <div className="space-y-3">
              <h5 className="text-xs font-semibold text-text/70">Experience</h5>
              {mockBaseResume.experience.map((exp, idx) => (
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
              {mockBaseResume.projects.map((proj, pIdx) => (
                <div key={pIdx} className="text-xs space-y-0.5">
                  <p className="font-medium text-text">{proj.title}</p>
                  <p className="text-text/70 leading-relaxed">{proj.desc}</p>
                </div>
              ))}
            </div>

            <div className="space-y-1.5 pt-2">
              <h5 className="text-xs font-semibold text-text/70">Skills</h5>
              <p className="text-xs text-text/70 leading-relaxed">
                {mockBaseResume.skills.core.join(', ')}
              </p>
            </div>
          </div>
        </div>

        {/* Column 2: Job Description */}
        <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
          <div className="flex items-baseline justify-between border-b border-accent/20 pb-3">
            <h3 className="text-xs font-semibold text-text">
              Job Description: {mockJobDescription.company}
            </h3>
            <span className="text-[11px] text-text/50">{mockJobDescription.role}</span>
          </div>

          <div className="space-y-5">
            <div className="space-y-1.5">
              <h5 className="text-xs font-semibold text-text/70">About the role</h5>
              <p className="text-xs text-text/70 leading-relaxed">
                {mockJobDescription.about}
              </p>
            </div>

            <div className="space-y-2">
              <h5 className="text-xs font-semibold text-text/70">Responsibilities</h5>
              <ul className="list-disc list-outside ml-4 text-xs text-text/70 space-y-1.5 leading-relaxed">
                {mockJobDescription.responsibilities.map((resp, rIdx) => (
                  <li key={rIdx}>{resp}</li>
                ))}
              </ul>
            </div>

            <div className="space-y-2">
              <h5 className="text-xs font-semibold text-text/70">Requirements</h5>
              <ul className="list-disc list-outside ml-4 text-xs text-text/70 space-y-1.5 leading-relaxed">
                {mockJobDescription.requirements.map((req, qIdx) => (
                  <li key={qIdx}>{req}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Column 3: Tailored Resume */}
        <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
          <div className="flex items-baseline justify-between border-b border-accent/20 pb-3">
            <h3 className="text-xs font-semibold text-text">Tailored Resume</h3>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-primary/15 text-primary">
              {mockTailoredResume.match_score}% Match
            </span>
          </div>

          <div className="space-y-4">
            <div className="text-center pb-2 border-b border-accent/20">
              <h4 className="text-base font-semibold text-text">{mockBaseResume.name}</h4>
              <p className="text-xs text-text/60 mt-0.5">{mockBaseResume.contact}</p>
            </div>

            <div className="space-y-3">
              <h5 className="text-xs font-semibold text-text/70">Experience (Reordered)</h5>
              {mockTailoredResume.reordered_experience.map((exp, idx) => (
                <div key={idx} className="space-y-2">
                  <div className="flex justify-between text-xs font-medium text-text">
                    <span>{exp.role} • {exp.company}</span>
                    <span className="text-text/50">{exp.period}</span>
                  </div>
                  <div className="space-y-2">
                    {exp.bullets.map((b, bIdx) => (
                      <div key={bIdx} className="space-y-1">
                        <p className="text-xs text-text/80 leading-relaxed">• {b.text}</p>
                        <div className="flex flex-wrap gap-1.5 ml-3">
                          {b.matched_tags.map((tag, tIdx) => (
                            <span
                              key={tIdx}
                              className="text-[10px] font-medium px-2 py-0.5 rounded bg-bg text-primary border border-accent/30"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="space-y-2 pt-2">
              <h5 className="text-xs font-semibold text-text/70">Skills (Prioritized)</h5>
              <div className="text-xs space-y-1">
                <p>
                  <span className="font-medium text-text">Core: </span>
                  <span className="text-text/70">
                    {mockTailoredResume.skills.core.join(', ')}
                  </span>
                </p>
                <p>
                  <span className="font-medium text-text">Support: </span>
                  <span className="text-text/70">
                    {mockTailoredResume.skills.support.join(', ')}
                  </span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
