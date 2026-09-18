// Types matching schema.sql, API_CONTRACT.md, and mock-data.json exactly

export type ApplicationStatus =
  | 'DISCOVERED'
  | 'READY_TO_APPLY'
  | 'APPLIED'
  | 'OA_INVITE'
  | 'INTERVIEW'
  | 'REJECTED'
  | 'GHOSTED'
  | 'OFFER';

export type StatusSourceType = 'gmail_auto' | 'auto_ghost' | 'manual';

export type ApplicationSource = 'serpapi' | 'unstop';

export interface Application {
  id: number;
  company: string;
  role: string;
  jd_text?: string;
  summary?: string;
  source: ApplicationSource;
  status: ApplicationStatus;
  status_source: StatusSourceType | null;
  match_score: number | null;
  tailored_resume_id: number | null;
  gap_report_id: number | null;
  last_contact_date: string;
  last_updated: string;
  created_at: string;
  status_label?: string; // e.g. "Online Assessment", "Resume Screen Rejected"
}

export interface TailoredResume {
  id: number;
  application_id: number;
  match_score: number;
  resume_data: {
    ordered_bullets: Array<{
      project: string;
      bullet: string;
      score: number;
      matched_tags?: string[];
    }>;
  };
  created_at: string;
}

export interface GapReportDetails {
  jd_required_skills?: string[];
  matched_skills?: string[];
  missing_skills?: string[];
  by_role_tag?: Record<
    string,
    {
      total: number;
      rejected_or_ghosted_at_oa?: number;
      rejected_or_ghosted_at_interview?: number;
      rejected_at_oa?: number;
      rejected_at_interview?: number;
    }
  >;
}

export interface GapReport {
  id: number;
  application_id: number | null;
  report_type: 'per_row' | 'aggregate';
  summary_text: string;
  details: GapReportDetails;
  created_at: string;
}

export interface ScamCheck {
  id: number;
  application_id: number | null;
  recruiter_name: string;
  recruiter_domain: string;
  claimed_company: string;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
  risk_score: number;
  flagged_reasons: string[];
  explanation_text: string | null;
  created_at: string;
}

export interface ActivityEvent {
  id: string;
  agent: 'Scout' | 'Tracker' | 'Tailoring' | 'Result';
  text: string;
  timestamp: string;
  date_group: 'TODAY' | 'YESTERDAY' | 'SEPTEMBER 15' | 'SEPTEMBER 12';
  color: string;
}

export interface PrepAnswerEvaluation {
  question?: string;
  question_tags?: string[];
  student_answer?: string;
  keyword_coverage: number;
  feedback_text: string;
  flagged_as_weak: boolean;
  recommended_resources?: Array<{
    skill: string;
    title: string;
    url: string;
  }>;
  actionable_suggestions?: string[];
}
