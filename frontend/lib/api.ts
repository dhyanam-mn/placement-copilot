import {
  Application,
  CompanyWatchlist,
  GapReport,
  HealthStatus,
  Notification,
  PrepResponse,
  Profile,
  ProfileProject,
  Resource,
  ScamCheck,
  ScamPattern,
  Setting,
  Skill,
  StatusEvent,
  TailoredResume,
} from '@/types';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!response.ok) {
    let errorMsg = `Request to ${endpoint} failed with status ${response.status}`;
    try {
      const errData = await response.json();
      if (errData.detail) {
        errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      } else if (errData.error) {
        errorMsg = errData.error;
      }
    } catch {
      // Use fallback errorMsg
    }
    throw new Error(errorMsg);
  }

  // Return empty object for 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// --- Health Check ---
export async function getHealth(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>("/health");
}

// --- Applications ---
export async function getApplications(params?: {
  status?: string;
  source?: string;
  is_demo?: boolean;
}): Promise<{ applications: Application[] }> {
  const query = new URLSearchParams();
  if (params?.status) query.append("status", params.status);
  if (params?.source) query.append("source", params.source);
  if (params?.is_demo !== undefined) query.append("is_demo", String(params.is_demo));
  const queryString = query.toString() ? `?${query.toString()}` : "";
  return fetchJson<{ applications: Application[] }>(`/applications${queryString}`);
}

export async function getApplication(id: number): Promise<Application> {
  return fetchJson<Application>(`/applications/${id}`);
}

export async function updateApplicationStatus(
  id: number,
  status: string,
  status_source: string = "manual"
): Promise<Application> {
  return fetchJson<Application>(`/applications/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, status_source }),
  });
}

export async function confirmApplicationApplied(id: number): Promise<Application> {
  return fetchJson<Application>(`/applications/${id}/confirm-applied`, {
    method: "POST",
  });
}

export async function getApplicationEvents(id: number): Promise<{ events: StatusEvent[] }> {
  return fetchJson<{ events: StatusEvent[] }>(`/applications/${id}/events`);
}

// --- Scout Sync ---
export async function triggerScoutSync(dryRun: boolean = false): Promise<any> {
  return fetchJson<any>(`/scout/sync?dry_run=${dryRun}`, {
    method: "POST",
  });
}

// --- Tailoring ---
export async function tailorResume(id: number): Promise<TailoredResume> {
  return fetchJson<TailoredResume>(`/applications/${id}/tailor`, {
    method: "POST",
  });
}

// --- Gap Reports ---
export async function getGapReport(id: number): Promise<GapReport> {
  return fetchJson<GapReport>(`/applications/${id}/gap-report`);
}

export async function generateGapReport(id: number): Promise<GapReport> {
  return fetchJson<GapReport>(`/applications/${id}/gap-report`, {
    method: "POST",
  });
}

export async function getAggregateGapReport(): Promise<GapReport> {
  return fetchJson<GapReport>("/gap-report");
}

// --- Scam Check ---
export async function runScamCheck(id: number, data: any): Promise<ScamCheck> {
  return fetchJson<ScamCheck>(`/applications/${id}/scam-check`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getStoredScamCheck(id: number): Promise<ScamCheck> {
  return fetchJson<ScamCheck>(`/applications/${id}/scam-check`);
}

// --- Prep Agent ---
export async function getPrepRecommendations(id: number): Promise<PrepResponse> {
  return fetchJson<PrepResponse>(`/applications/${id}/prep`);
}

export async function generatePrepRecommendations(id: number): Promise<PrepResponse> {
  return fetchJson<PrepResponse>(`/applications/${id}/prep`, {
    method: "POST",
  });
}

// --- Notifications ---
export async function getNotifications(unreadOnly: boolean = false): Promise<{ notifications: Notification[] }> {
  return fetchJson<{ notifications: Notification[] }>(`/notifications?unread_only=${unreadOnly}`);
}

export async function markNotificationRead(id: number): Promise<Notification> {
  return fetchJson<Notification>(`/notifications/${id}/read`, {
    method: "POST",
  });
}

// --- Gmail Tracker ---
export async function syncGmailTracker(): Promise<any> {
  return fetchJson<any>("/tracker/gmail/sync", {
    method: "POST",
  });
}

export interface NudgesResponse {
  threshold_days: number;
  ghost_days: number;
  total_nudges: number;
  nudges: Application[];
}

export async function getStaleNudges(days: number = 14): Promise<NudgesResponse> {
  return fetchJson<NudgesResponse>(`/tracker/nudges?days=${days}`);
}

// --- Profile & Projects ---
export async function getProfile(): Promise<Profile> {
  return fetchJson<Profile>("/profile");
}

export async function updateProfile(data: { name: string; email?: string; contact_info?: string }): Promise<Profile> {
  return fetchJson<Profile>("/profile", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getProfileProjects(): Promise<ProfileProject[]> {
  return fetchJson<ProfileProject[]>("/profile/projects");
}

export async function createProfileProject(data: { project_name: string; bullet_text: string; skill_tags?: string[] }): Promise<ProfileProject> {
  return fetchJson<ProfileProject>("/profile/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProfileProject(id: number, data: { project_name: string; bullet_text: string; skill_tags?: string[] }): Promise<ProfileProject> {
  return fetchJson<ProfileProject>(`/profile/projects/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteProfileProject(id: number): Promise<void> {
  return fetchJson<void>(`/profile/projects/${id}`, {
    method: "DELETE",
  });
}

export async function importProfile(data: { name: string; email?: string; contact_info?: string; projects?: any[] }): Promise<Profile> {
  return fetchJson<Profile>("/profile/import", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// --- Resources ---
export async function getResources(): Promise<Resource[]> {
  return fetchJson<Resource[]>("/resources");
}

export async function createResource(data: { title: string; url: string; is_active?: boolean; skills?: any[] }): Promise<Resource> {
  return fetchJson<Resource>("/resources", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateResource(id: number, data: { title: string; url: string; is_active?: boolean; skills?: any[] }): Promise<Resource> {
  return fetchJson<Resource>(`/resources/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteResource(id: number): Promise<void> {
  return fetchJson<void>(`/resources/${id}`, {
    method: "DELETE",
  });
}

export async function checkResourceLinks(): Promise<any> {
  return fetchJson<any>("/resources/check-links", {
    method: "POST",
  });
}

// --- Skills ---
export async function getSkills(): Promise<Skill[]> {
  return fetchJson<Skill[]>("/skills");
}

export async function createSkill(data: { name: string; category?: string; aliases?: string[] }): Promise<Skill> {
  return fetchJson<Skill>("/skills", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSkill(id: number, data: { name: string; category?: string; aliases?: string[] }): Promise<Skill> {
  return fetchJson<Skill>(`/skills/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSkill(id: number): Promise<void> {
  return fetchJson<void>(`/skills/${id}`, {
    method: "DELETE",
  });
}

// --- Scam Patterns ---
export async function getScamPatterns(): Promise<ScamPattern[]> {
  return fetchJson<ScamPattern[]>("/scam-patterns");
}

export async function createScamPattern(data: { category: string; pattern: string; weight: number; source_note?: string }): Promise<ScamPattern> {
  return fetchJson<ScamPattern>("/scam-patterns", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateScamPattern(id: number, data: { category: string; pattern: string; weight: number; source_note?: string }): Promise<ScamPattern> {
  return fetchJson<ScamPattern>(`/scam-patterns/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteScamPattern(id: number): Promise<void> {
  return fetchJson<void>(`/scam-patterns/${id}`, {
    method: "DELETE",
  });
}

// --- Watchlist ---
export async function getWatchlist(): Promise<CompanyWatchlist[]> {
  return fetchJson<CompanyWatchlist[]>("/watchlist");
}

export async function createWatchlistItem(data: { company: string; ats?: string; token?: string; active?: boolean }): Promise<CompanyWatchlist> {
  return fetchJson<CompanyWatchlist>("/watchlist", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateWatchlistItem(id: number, data: { company: string; ats?: string; token?: string; active?: boolean }): Promise<CompanyWatchlist> {
  return fetchJson<CompanyWatchlist>(`/watchlist/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteWatchlistItem(id: number): Promise<void> {
  return fetchJson<void>(`/watchlist/${id}`, {
    method: "DELETE",
  });
}

// --- Settings ---
export async function getSettings(): Promise<Setting[]> {
  return fetchJson<Setting[]>("/settings");
}

export async function updateSetting(key: string, value: any): Promise<Setting> {
  return fetchJson<Setting>(`/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  });
}