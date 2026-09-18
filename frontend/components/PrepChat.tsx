'use client';

import React, { useEffect, useState } from 'react';
import { PrepAnswerEvaluation } from '@/types';
import { evaluatePrepAnswer } from '@/lib/api';
import { RefreshCw, Send } from 'lucide-react';

interface PrepChatProps {
  applicationId?: number;
}

const DEFAULT_QUESTION =
  'Walk me through your approach to hard-negative mining in the DronaMaps pipeline.';
const DEFAULT_TAGS = [
  'hard negative mining',
  'sliding window tiling',
  'confidence thresholding',
];
const DEFAULT_ANSWER =
  'I used sliding window tiling and filtered false positives based on confidence thresholds.';

export const PrepChat: React.FC<PrepChatProps> = ({ applicationId = 1 }) => {
  const [question] = useState(DEFAULT_QUESTION);
  const [tags] = useState(DEFAULT_TAGS);
  const [answer, setAnswer] = useState(DEFAULT_ANSWER);
  const [submitted, setSubmitted] = useState(false);
  const [evaluation, setEvaluation] = useState<PrepAnswerEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    evaluatePrepAnswer(applicationId, {
      question,
      student_answer: answer,
      question_tags: tags,
    })
      .then((data) => {
        if (!cancelled) {
          setEvaluation(data);
          setSubmitted(true);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Failed to evaluate answer');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [applicationId, question, tags]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!answer.trim()) return;

    setEvaluating(true);
    setError(null);

    try {
      const data = await evaluatePrepAnswer(applicationId, {
        question,
        student_answer: answer,
        question_tags: tags,
      });
      setEvaluation(data);
      setSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'Failed to evaluate preparation answer');
    } finally {
      setEvaluating(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl space-y-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Interview Prep Agent
          </h2>
          <p className="text-sm text-text/60 mt-1">Loading prep evaluation…</p>
        </div>
      </div>
    );
  }

  if (error && !evaluation) {
    return (
      <div className="max-w-4xl space-y-8">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-text">
            Interview Prep Agent
          </h2>
          <p className="text-sm text-rejected mt-1">
            Couldn&apos;t reach the backend: {error}
          </p>
        </div>
      </div>
    );
  }

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

            {evaluation.actionable_suggestions && evaluation.actionable_suggestions.length > 0 && (
              <div className="pt-2 border-t border-accent/20 space-y-1">
                <span className="text-[11px] font-semibold text-text/70">Actionable Suggestions:</span>
                <ul className="list-disc list-outside ml-4 text-xs text-text/70 space-y-1">
                  {evaluation.actionable_suggestions.map((sug, idx) => (
                    <li key={idx}>{sug}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {error && evaluation && (
          <p className="text-xs text-rejected">{error}</p>
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
              disabled={evaluating}
              className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{evaluating ? 'Evaluating...' : 'Evaluate answer'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
