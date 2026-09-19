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

export type ApplicationSource = 'adzuna' | 'greenhouse' | 'lever' | 'unstop';

export interface Application {
  id: number;
  company: string;
  role: string;
  jd_text?: string;
  source: ApplicationSource;
  status: ApplicationStatus;
  status_source: StatusSourceType | null;
  match_score: number | null;
  tailored_resume_id: number | null;
  gap_report_id: number | null;
  last_contact_date: string;
  last_updated: string;
  created_at: string;
  is_demo?: boolean;
}

export interface StatusEvent {
  id: number;
  application_id: number;
  old_status?: string | null;
  new_status: string;
  event_source?: string | null;
  created_at: string;
  is_demo?: boolean;
}

export interface Notification {
  id: number;
  type: string;
  content: string;
  read: boolean;
  created_at: string;
  is_demo?: boolean;
}

export interface TailoredResume {
  tailored_resume_id: number;
  resume_data: {
    ordered_bullets: Array<{
      project: string;
      bullet: string;
      score: number;
    }>;
  };
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
  details?: GapReportDetails | null;
  created_at: string;
  is_demo?: boolean;
}

export interface ScamCheck {
  id: number;
  application_id?: number | null;
  recruiter_name?: string | null;
  recruiter_domain?: string | null;
  risk_score: number;
  flagged_reasons: string[];
  explanation_text?: string | null;
  created_at: string;
  is_demo?: boolean;
}

export interface PrepRecommendationItem {
  id: number;
  application_id: number;
  resource_id: number;
  title: string;
  url: string;
  reason: string;
  est_hours?: number | null;
  created_at?: string | null;
  verified_at?: string | null;
}

export interface PrepResponse {
  application_id: number;
  recommendations: PrepRecommendationItem[];
}

export interface ProfileProject {
  id: number;
  profile_id: number;
  project_name: string;
  bullet_text: string;
  skill_tags?: string[] | null;
  created_at: string;
  is_demo?: boolean;
}

export interface Profile {
  id: number;
  name: string;
  email?: string | null;
  contact_info?: string | null;
  created_at: string;
  is_demo?: boolean;
  projects?: ProfileProject[];
}

export interface ResourceSkillLink {
  skill_name: string;
  weight: number;
}

export interface Resource {
  id: number;
  title: string;
  url: string;
  is_active: boolean;
  verified_at?: string | null;
  created_at: string;
  is_demo?: boolean;
  skills?: ResourceSkillLink[];
}

export interface Skill {
  id: number;
  name: string;
  category?: string | null;
  aliases?: string[] | null;
  created_at: string;
  is_demo?: boolean;
}

export interface ScamPattern {
  id: number;
  category: string;
  pattern: string;
  weight: number;
  source_note: string;
  created_at: string;
  is_demo?: boolean;
}

export interface CompanyWatchlist {
  id: number;
  company: string;
  ats?: string | null;
  token?: string | null;
  active: boolean;
  created_at: string;
  is_demo?: boolean;
}

export interface Setting {
  key: string;
  value: any;
  updated_at: string;
}

export interface HealthStatus {
  status: string;
  services: Record<string, string>;
}
