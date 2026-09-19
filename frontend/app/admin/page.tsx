'use client';

import React, { useEffect, useState } from 'react';
import {
  Resource,
  Skill,
  ScamPattern,
  CompanyWatchlist,
  Setting,
} from '@/types';
import {
  getResources,
  createResource,
  updateResource,
  deleteResource,
  checkResourceLinks,
  getSkills,
  createSkill,
  updateSkill,
  deleteSkill,
  getScamPatterns,
  createScamPattern,
  updateScamPattern,
  deleteScamPattern,
  getWatchlist,
  createWatchlistItem,
  updateWatchlistItem,
  deleteWatchlistItem,
  getSettings,
  updateSetting,
} from '@/lib/api';
import {
  Settings,
  BookOpen,
  Code2,
  ShieldAlert,
  Building2,
  Sliders,
  Plus,
  Trash2,
  Edit2,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';

type AdminTab = 'resources' | 'skills' | 'scam' | 'watchlist' | 'settings';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<AdminTab>('resources');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Entities state
  const [resources, setResources] = useState<Resource[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [scamPatterns, setScamPatterns] = useState<ScamPattern[]>([]);
  const [watchlist, setWatchlist] = useState<CompanyWatchlist[]>([]);
  const [settings, setSettings] = useState<Setting[]>([]);

  // Action states
  const [checkingLinks, setCheckingLinks] = useState(false);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [resData, skillData, scamData, watchData, settsData] = await Promise.all([
        getResources().catch(() => []),
        getSkills().catch(() => []),
        getScamPatterns().catch(() => []),
        getWatchlist().catch(() => []),
        getSettings().catch(() => []),
      ]);
      setResources(resData || []);
      setSkills(skillData || []);
      setScamPatterns(scamData || []);
      setWatchlist(watchData || []);
      setSettings(settsData || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const notifySuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  // --- Resource Actions ---
  const handleCheckLinks = async () => {
    setCheckingLinks(true);
    setError(null);
    try {
      const res = await checkResourceLinks();
      notifySuccess(`Link check finished! Updated ${res?.checked || 'all'} resource URLs.`);
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Check links failed');
    } finally {
      setCheckingLinks(false);
    }
  };

  const handleCreateResource = async () => {
    const title = prompt('Enter resource title:');
    if (!title) return;
    const url = prompt('Enter resource URL:');
    if (!url) return;
    try {
      await createResource({ title, url, is_active: true });
      notifySuccess('Resource created');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Create resource failed');
    }
  };

  const handleDeleteResource = async (id: number) => {
    if (!confirm('Delete resource?')) return;
    try {
      await deleteResource(id);
      notifySuccess('Resource deleted');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    }
  };

  // --- Skill Actions ---
  const handleCreateSkill = async () => {
    const name = prompt('Enter skill name:');
    if (!name) return;
    const category = prompt('Enter category (e.g. backend, machine_learning):') || undefined;
    const aliasesStr = prompt('Enter comma-separated aliases:') || '';
    const aliases = aliasesStr ? aliasesStr.split(',').map((s) => s.trim()) : [];
    try {
      await createSkill({ name, category, aliases });
      notifySuccess('Skill created');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Create skill failed');
    }
  };

  const handleDeleteSkill = async (id: number) => {
    if (!confirm('Delete skill?')) return;
    try {
      await deleteSkill(id);
      notifySuccess('Skill deleted');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    }
  };

  // --- Scam Pattern Actions ---
  const handleCreateScamPattern = async () => {
    const category = prompt('Enter pattern category (e.g. upfront_fee, unverified_domain):');
    if (!category) return;
    const pattern = prompt('Enter pattern string / domain / regex:');
    if (!pattern) return;
    const weightStr = prompt('Enter risk weight (0 to 1):') || '0.5';
    const weight = parseFloat(weightStr);
    try {
      await createScamPattern({ category, pattern, weight });
      notifySuccess('Scam pattern added');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Create scam pattern failed');
    }
  };

  const handleDeleteScamPattern = async (id: number) => {
    if (!confirm('Delete scam pattern?')) return;
    try {
      await deleteScamPattern(id);
      notifySuccess('Scam pattern deleted');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    }
  };

  // --- Watchlist Actions ---
  const handleCreateWatchlist = async () => {
    const company = prompt('Enter company name:');
    if (!company) return;
    const ats = prompt('Enter ATS platform (greenhouse / lever / ashby):') || undefined;
    const token = prompt('Enter company ATS token:') || undefined;
    try {
      await createWatchlistItem({ company, ats, token, active: true });
      notifySuccess('Watchlist item added');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Create watchlist item failed');
    }
  };

  const handleDeleteWatchlist = async (id: number) => {
    if (!confirm('Delete watchlist entry?')) return;
    try {
      await deleteWatchlistItem(id);
      notifySuccess('Watchlist entry deleted');
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Delete failed');
    }
  };

  // --- Settings Actions ---
  const handleUpdateSetting = async (key: string, currentValue: any) => {
    const newValueStr = prompt(`Update value for key "${key}":`, JSON.stringify(currentValue));
    if (newValueStr === null) return;
    try {
      let val: any;
      try {
        val = JSON.parse(newValueStr);
      } catch {
        val = newValueStr;
      }
      await updateSetting(key, val);
      notifySuccess(`Setting "${key}" updated`);
      loadAllData();
    } catch (err: any) {
      setError(err.message || 'Update setting failed');
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-sm text-text/60">Loading system admin data...</div>;
  }

  return (
    <div className="max-w-6xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-text">System Administration</h1>
        <p className="text-sm text-text/60 mt-1">
          Configure copilot settings, learning resources, skill taxonomy, scam patterns, and ATS watchlist.
        </p>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center space-x-3 text-emerald-800 text-xs">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-rejected/10 border border-rejected/30 flex items-center space-x-3 text-rejected text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-accent/30 space-x-2">
        <button
          onClick={() => setActiveTab('resources')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'resources'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-text/60 hover:text-text'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>Resources ({resources.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('skills')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'skills'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-text/60 hover:text-text'
          }`}
        >
          <Code2 className="w-4 h-4" />
          <span>Skills ({skills.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('scam')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'scam'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-text/60 hover:text-text'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Scam Patterns ({scamPatterns.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('watchlist')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'watchlist'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-text/60 hover:text-text'
          }`}
        >
          <Building2 className="w-4 h-4" />
          <span>ATS Watchlist ({watchlist.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('settings')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'settings'
              ? 'border-primary text-primary font-semibold'
              : 'border-transparent text-text/60 hover:text-text'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>System Settings ({settings.length})</span>
        </button>
      </div>

      {/* TAB 1: RESOURCES */}
      {activeTab === 'resources' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text/60">
              Learning material catalog linked with skill keywords for the Prep Agent.
            </p>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleCheckLinks}
                disabled={checkingLinks}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${checkingLinks ? 'animate-spin' : ''}`} />
                <span>Check Resource Links</span>
              </button>

              <button
                onClick={handleCreateResource}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Resource</span>
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-accent/30 divide-y divide-accent/20 overflow-hidden">
            {resources.length === 0 ? (
              <div className="p-8 text-center text-xs text-text/60">No resources found.</div>
            ) : (
              resources.map((res) => (
                <div key={res.id} className="p-4 flex items-center justify-between hover:bg-bg/40">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-semibold text-text">{res.title}</h4>
                      {res.is_active ? (
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-red-100 text-red-800 border border-red-300">
                          INACTIVE
                        </span>
                      )}
                    </div>
                    <a
                      href={res.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-primary hover:underline inline-flex items-center space-x-1"
                    >
                      <span>{res.url}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                    {res.skills && res.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {res.skills.map((s, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] bg-bg text-text/70 px-1.5 py-0.5 rounded border border-accent/20"
                          >
                            {s.skill_name} (weight {s.weight})
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => handleDeleteResource(res.id)}
                    className="p-1.5 text-text/50 hover:text-rejected transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 2: SKILLS */}
      {activeTab === 'skills' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text/60">
              Taxonomy of known skills and aliases for deterministic extraction from job descriptions.
            </p>
            <button
              onClick={handleCreateSkill}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Skill</span>
            </button>
          </div>

          <div className="bg-white rounded-lg border border-accent/30 divide-y divide-accent/20 overflow-hidden">
            {skills.length === 0 ? (
              <div className="p-8 text-center text-xs text-text/60">No skills found.</div>
            ) : (
              skills.map((sk) => (
                <div key={sk.id} className="p-4 flex items-center justify-between hover:bg-bg/40">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-semibold text-text">{sk.name}</h4>
                      {sk.category && (
                        <span className="text-[10px] font-medium px-2 py-0.5 bg-accent/20 text-text/70 rounded">
                          {sk.category}
                        </span>
                      )}
                    </div>
                    {sk.aliases && sk.aliases.length > 0 && (
                      <p className="text-xs text-text/60">
                        Aliases: {sk.aliases.join(', ')}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={() => handleDeleteSkill(sk.id)}
                    className="p-1.5 text-text/50 hover:text-rejected transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 3: SCAM PATTERNS */}
      {activeTab === 'scam' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text/60">
              Scam detection rule engine keywords, suspicious recruiter domains, and risk weights.
            </p>
            <button
              onClick={handleCreateScamPattern}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Scam Pattern</span>
            </button>
          </div>

          <div className="bg-white rounded-lg border border-accent/30 divide-y divide-accent/20 overflow-hidden">
            {scamPatterns.length === 0 ? (
              <div className="p-8 text-center text-xs text-text/60">No scam patterns found.</div>
            ) : (
              scamPatterns.map((pat) => (
                <div key={pat.id} className="p-4 flex items-center justify-between hover:bg-bg/40">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded border border-amber-300">
                        {pat.category}
                      </span>
                      <code className="text-xs font-mono text-text bg-bg px-2 py-0.5 rounded">
                        {pat.pattern}
                      </code>
                    </div>
                    <p className="text-xs text-text/60">
                      Risk Weight: {pat.weight} • Source Note: {pat.source_note || 'N/A'}
                    </p>
                  </div>

                  <button
                    onClick={() => handleDeleteScamPattern(pat.id)}
                    className="p-1.5 text-text/50 hover:text-rejected transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 4: ATS WATCHLIST */}
      {activeTab === 'watchlist' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-text/60">
              Target companies scanned by Scout for Greenhouse and Lever job postings.
            </p>
            <button
              onClick={handleCreateWatchlist}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Company Watchlist</span>
            </button>
          </div>

          <div className="bg-white rounded-lg border border-accent/30 divide-y divide-accent/20 overflow-hidden">
            {watchlist.length === 0 ? (
              <div className="p-8 text-center text-xs text-text/60">No watchlist items found.</div>
            ) : (
              watchlist.map((item) => (
                <div key={item.id} className="p-4 flex items-center justify-between hover:bg-bg/40">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-semibold text-text">{item.company}</h4>
                      {item.ats && (
                        <span className="text-[10px] font-bold px-2 py-0.5 bg-primary/10 text-primary rounded">
                          {item.ats.toUpperCase()}
                        </span>
                      )}
                      {item.active ? (
                        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="text-[10px] text-text/50">INACTIVE</span>
                      )}
                    </div>
                    {item.token && <p className="text-xs text-text/60 font-mono">Token: {item.token}</p>}
                  </div>

                  <button
                    onClick={() => handleDeleteWatchlist(item.id)}
                    className="p-1.5 text-text/50 hover:text-rejected transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 5: SETTINGS */}
      {activeTab === 'settings' && (
        <div className="space-y-4">
          <p className="text-xs text-text/60">
            System runtime thresholds (ghost_days, nudge_days, scam_threshold, scout_interval_hours).
          </p>

          <div className="bg-white rounded-lg border border-accent/30 divide-y divide-accent/20 overflow-hidden">
            {settings.length === 0 ? (
              <div className="p-8 text-center text-xs text-text/60">No settings rows found.</div>
            ) : (
              settings.map((s) => (
                <div key={s.key} className="p-4 flex items-center justify-between hover:bg-bg/40">
                  <div className="space-y-1">
                    <code className="text-xs font-semibold text-primary">{s.key}</code>
                    <div className="text-xs font-mono text-text bg-bg px-2.5 py-1 rounded inline-block">
                      {JSON.stringify(s.value)}
                    </div>
                  </div>

                  <button
                    onClick={() => handleUpdateSetting(s.key, s.value)}
                    className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs text-text bg-white border border-accent/40 rounded hover:bg-white/80 transition-colors"
                  >
                    <Edit2 className="w-3.5 h-3.5 text-primary" />
                    <span>Edit Value</span>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
