'use client';

import React, { useState } from 'react';
import { mockPrepEvaluation } from '@/data/mockData';
import { MessageSquare, Check, RefreshCw, Send } from 'lucide-react';

export const PrepChat: React.FC = () => {
  const [question] = useState(mockPrepEvaluation.question);
  const [tags] = useState(mockPrepEvaluation.question_tags);
  const [answer, setAnswer] = useState(mockPrepEvaluation.student_answer);
  const [submitted, setSubmitted] = useState(true);
  const [evaluation, setEvaluation] = useState(mockPrepEvaluation);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!answer.trim()) return;

    // Deterministic keyword coverage check per MODEL_SERVICE_CONTRACT
    const lowerAnswer = answer.toLowerCase();
    const matchedCount = tags.filter((t) => lowerAnswer.includes(t.toLowerCase())).length;
    const coverage = tags.length > 0 ? matchedCount / tags.length : 0;
    const isWeak = coverage < 0.3;

    setEvaluation({
      question,
      question_tags: tags,
      student_answer: answer,
      keyword_coverage: Number(coverage.toFixed(2)),
      feedback_text:
        coverage >= 0.66
          ? "Solid coverage of core pipeline concepts. Focus on directly connecting each step to computational complexity and throughput."
          : "Consider mentioning the key terms directly to ensure automated filters and interviewers capture all requirements.",
      flagged_as_weak: isWeak,
    });
    setSubmitted(true);
  };

  return (
    <div className="max-w-4xl space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-text">
          Interview Prep Agent
        </h2>
        <p className="text-sm text-text/60 mt-1">
          Quiet rehearsal space for role-specific technical questions.
        </p>
      </div>

      {/* Main Question Card */}
      <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-primary">Technical Question</span>
            <span className="text-xs text-text/50">DronaMaps • Computer Vision Intern</span>
          </div>
          <h3 className="text-base font-medium text-text leading-relaxed">
            {question}
          </h3>

          {/* Expected topics / tags */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-[11px] text-text/50">Target concepts:</span>
            {tags.map((tag, idx) => (
              <span
                key={idx}
                className="text-[11px] font-medium px-2.5 py-0.5 rounded bg-bg text-text/80 border border-accent/20"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {/* Evaluation Feedback Callout (if submitted) */}
        {submitted && evaluation && (
          <div className="p-4 rounded-lg bg-bg border border-accent/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-text">Prep Feedback</span>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-text/60">Keyword coverage:</span>
                <span className="text-xs font-semibold text-primary">
                  {Math.round(evaluation.keyword_coverage * 100)}%
                </span>
                {evaluation.flagged_as_weak && (
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-rejected/15 text-rejected">
                    Needs practice
                  </span>
                )}
              </div>
            </div>

            <p className="text-xs text-text/80 leading-relaxed">
              {evaluation.feedback_text}
            </p>
          </div>
        )}

        {/* Answer Input Area */}
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-text/70">
              Your response:
            </label>
            <textarea
              rows={4}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your technical explanation here..."
              className="w-full p-3 text-xs text-text bg-bg/50 border border-accent/40 rounded focus:outline-none focus:border-primary transition-colors resize-none leading-relaxed"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              type="button"
              onClick={() => {
                setAnswer('');
                setSubmitted(false);
              }}
              className="inline-flex items-center space-x-1.5 text-xs text-text/60 hover:text-text transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Clear answer</span>
            </button>

            <button
              type="submit"
              className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Evaluate answer</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
