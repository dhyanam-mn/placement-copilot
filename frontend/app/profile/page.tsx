'use client';

import React, { useEffect, useState } from 'react';
import { Profile, ProfileProject } from '@/types';
import {
  getProfile,
  updateProfile,
  getProfileProjects,
  createProfileProject,
  updateProfileProject,
  deleteProfileProject,
  importProfile,
} from '@/lib/api';
import {
  User,
  FolderGit2,
  Plus,
  Trash2,
  Edit2,
  Upload,
  Save,
  CheckCircle,
  AlertCircle,
  Code,
} from 'lucide-react';

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [projects, setProjects] = useState<ProfileProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Profile Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [contactInfo, setContactInfo] = useState('');

  // Project Modal/Form State
  const [editingProject, setEditingProject] = useState<ProfileProject | null>(null);
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [bulletText, setBulletText] = useState('');
  const [skillTagsStr, setSkillTagsStr] = useState('');

  // JSON Import Modal State
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [jsonText, setJsonText] = useState('');
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [profData, projData] = await Promise.all([
        getProfile().catch(() => null),
        getProfileProjects().catch(() => []),
      ]);
      if (profData) {
        setProfile(profData);
        setName(profData.name || '');
        setEmail(profData.email || '');
        setContactInfo(profData.contact_info || '');
      }
      setProjects(projData || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await updateProfile({
        name,
        email: email || undefined,
        contact_info: contactInfo || undefined,
      });
      setProfile(updated);
      setSuccessMsg('Profile updated successfully!');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleOpenAddProject = () => {
    setEditingProject(null);
    setProjectName('');
    setBulletText('');
    setSkillTagsStr('');
    setIsProjectModalOpen(true);
  };

  const handleOpenEditProject = (proj: ProfileProject) => {
    setEditingProject(proj);
    setProjectName(proj.project_name);
    setBulletText(proj.bullet_text);
    setSkillTagsStr(proj.skill_tags ? proj.skill_tags.join(', ') : '');
    setIsProjectModalOpen(true);
  };

  const handleSaveProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectName.trim() || !bulletText.trim()) return;

    const skill_tags = skillTagsStr
      ? skillTagsStr.split(',').map((s) => s.trim()).filter(Boolean)
      : [];

    setError(null);
    try {
      if (editingProject) {
        await updateProfileProject(editingProject.id, {
          project_name: projectName,
          bullet_text: bulletText,
          skill_tags,
        });
        setSuccessMsg('Project updated!');
      } else {
        await createProfileProject({
          project_name: projectName,
          bullet_text: bulletText,
          skill_tags,
        });
        setSuccessMsg('Project added!');
      }
      setIsProjectModalOpen(false);
      loadData();
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to save project');
    }
  };

  const handleDeleteProject = async (id: number) => {
    if (!confirm('Are you sure you want to delete this project bullet?')) return;
    try {
      await deleteProfileProject(id);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete project');
    }
  };

  const handleImportJson = async (e: React.FormEvent) => {
    e.preventDefault();
    setImporting(true);
    setError(null);
    try {
      let parsed: any;
      try {
        parsed = JSON.parse(jsonText);
      } catch (parseErr) {
        throw new Error('Invalid JSON format. Please check your syntax.');
      }

      if (!parsed.name) {
        throw new Error('JSON profile must contain a "name" field.');
      }

      await importProfile(parsed);
      setIsImportModalOpen(false);
      setJsonText('');
      setSuccessMsg('Profile imported successfully!');
      loadData();
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-sm text-text/60">Loading profile data...</div>;
  }

  return (
    <div className="max-w-5xl space-y-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text">Candidate Profile</h1>
          <p className="text-sm text-text/60 mt-1">
            Manage your personal baseline info, project resume bullets, and skill tags.
          </p>
        </div>

        <button
          onClick={() => setIsImportModalOpen(true)}
          className="inline-flex items-center space-x-2 px-3.5 py-2 text-xs font-medium text-text bg-white/80 border border-accent/40 rounded hover:bg-white transition-colors shrink-0"
        >
          <Upload className="w-3.5 h-3.5 text-primary" />
          <span>Import Profile JSON</span>
        </button>
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

      {/* Main Grid: Profile Info + Projects */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Basic Info Form */}
        <div className="lg:col-span-1 space-y-6">
          <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-5">
            <div className="flex items-center space-x-2 border-b border-accent/20 pb-3">
              <User className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold text-text">Basic Information</h2>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text/70">Full Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Rivera"
                  className="w-full p-2.5 text-xs text-text bg-bg/50 border border-accent/40 rounded focus:outline-none focus:border-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text/70">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex@example.com"
                  className="w-full p-2.5 text-xs text-text bg-bg/50 border border-accent/40 rounded focus:outline-none focus:border-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text/70">Contact Info / Links</label>
                <input
                  type="text"
                  value={contactInfo}
                  onChange={(e) => setContactInfo(e.target.value)}
                  placeholder="github.com/alex | linkedin.com/in/alex"
                  className="w-full p-2.5 text-xs text-text bg-bg/50 border border-accent/40 rounded focus:outline-none focus:border-primary"
                />
              </div>

              <button
                type="submit"
                disabled={savingProfile}
                className="w-full inline-flex items-center justify-center space-x-2 px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{savingProfile ? 'Saving...' : 'Save Profile Info'}</span>
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Project Resume Bullets List */}
        <div className="lg:col-span-2 space-y-6">
          <div className="p-6 rounded-lg bg-white border border-accent/30 space-y-6">
            <div className="flex items-center justify-between border-b border-accent/20 pb-3">
              <div className="flex items-center space-x-2">
                <FolderGit2 className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-semibold text-text">
                  Project Resume Bullets ({projects.length})
                </h2>
              </div>

              <button
                onClick={handleOpenAddProject}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-primary bg-primary/10 rounded hover:bg-primary/20 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Bullet</span>
              </button>
            </div>

            {projects.length === 0 ? (
              <div className="p-8 text-center space-y-2">
                <Code className="w-8 h-8 text-text/30 mx-auto" />
                <h3 className="text-sm font-semibold text-text">No Project Bullets Yet</h3>
                <p className="text-xs text-text/60">
                  Add project accomplishments with skill tags for automated LaTeX resume tailoring.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {projects.map((proj) => (
                  <div
                    key={proj.id}
                    className="p-4 rounded-lg bg-bg/40 border border-accent/30 space-y-3 hover:border-accent/60 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <h3 className="text-sm font-semibold text-text">{proj.project_name}</h3>
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleOpenEditProject(proj)}
                          className="p-1 text-text/60 hover:text-primary transition-colors"
                          title="Edit"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDeleteProject(proj.id)}
                          className="p-1 text-text/60 hover:text-rejected transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <p className="text-xs text-text/80 leading-relaxed font-mono bg-white p-2.5 rounded border border-accent/20">
                      {proj.bullet_text}
                    </p>

                    {proj.skill_tags && proj.skill_tags.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {proj.skill_tags.map((tag, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Project Modal */}
      {isProjectModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full space-y-5 shadow-xl">
            <h3 className="text-base font-semibold text-text">
              {editingProject ? 'Edit Project Bullet' : 'Add Project Bullet'}
            </h3>

            <form onSubmit={handleSaveProject} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text/70">Project Name *</label>
                <input
                  type="text"
                  required
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. DronaMaps Drone Tiling Pipeline"
                  className="w-full p-2.5 text-xs text-text border border-accent/40 rounded focus:outline-none focus:border-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text/70">Bullet Text *</label>
                <textarea
                  rows={4}
                  required
                  value={bulletText}
                  onChange={(e) => setBulletText(e.target.value)}
                  placeholder="e.g. Engineered sliding window tiling system reducing latency by 40%..."
                  className="w-full p-2.5 text-xs text-text border border-accent/40 rounded focus:outline-none focus:border-primary font-mono resize-none leading-relaxed"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-text/70">
                  Skill Tags (comma separated)
                </label>
                <input
                  type="text"
                  value={skillTagsStr}
                  onChange={(e) => setSkillTagsStr(e.target.value)}
                  placeholder="Python, PyTorch, Computer Vision, Docker"
                  className="w-full p-2.5 text-xs text-text border border-accent/40 rounded focus:outline-none focus:border-primary"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsProjectModalOpen(false)}
                  className="px-4 py-2 text-xs text-text/70 hover:text-text"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90"
                >
                  {editingProject ? 'Save Changes' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* JSON Import Modal */}
      {isImportModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 max-w-xl w-full space-y-5 shadow-xl">
            <div>
              <h3 className="text-base font-semibold text-text">Import Candidate Profile JSON</h3>
              <p className="text-xs text-text/60 mt-1">
                Paste raw profile JSON containing name, email, contact_info, and project bullets.
              </p>
            </div>

            <form onSubmit={handleImportJson} className="space-y-4">
              <textarea
                rows={10}
                required
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                placeholder={`{\n  "name": "Alex Rivera",\n  "email": "alex@example.com",\n  "contact_info": "github.com/alex",\n  "projects": [\n    {\n      "project_name": "DronaMaps",\n      "bullet_text": "Built computer vision pipeline...",\n      "skill_tags": ["Python", "PyTorch"]\n    }\n  ]\n}`}
                className="w-full p-3 text-xs text-text font-mono bg-bg/50 border border-accent/40 rounded focus:outline-none focus:border-primary resize-none"
              />

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsImportModalOpen(false)}
                  className="px-4 py-2 text-xs text-text/70 hover:text-text"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importing}
                  className="px-4 py-2 text-xs font-medium text-white bg-primary rounded hover:bg-primary/90 disabled:opacity-50"
                >
                  {importing ? 'Importing...' : 'Execute Import'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
