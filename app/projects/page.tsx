'use client';

import { apiFetch, apiFetchSafe } from '@/lib/api';
import { Folder, ArrowRight, Plus, X, Loader2, CheckCircle2, Building2, Trash2, AlertTriangle } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState, useCallback } from 'react';
import { useAppDataRefresh, notifyAppDataRefresh } from '@/lib/app-sync';
import { getDeletedProjectCodes, recordDeletedProjectCode, unrecordDeletedProjectCode, FALLBACK_PROJECTS } from '@/lib/projects';
import { clearFallbackData } from '@/lib/report-fallback';

export default function Projects() {
  const [projects, setProjects] = useState(FALLBACK_PROJECTS);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProjName, setNewProjName] = useState('');
  const [newProjDesc, setNewProjDesc] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const [projectToDelete, setProjectToDelete] = useState<{ code: string; name: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const fetchProjects = useCallback(() => {
    const deleted = getDeletedProjectCodes();
    apiFetch<{ project_id: string; name: string; description?: string; created_at?: string; status?: string; progress_percentage?: number }[]>('/projects')
      .then((data) => {
        if (Array.isArray(data)) {
          const apiProjects = data
            .filter((p) => !deleted.has(p.project_id))
            .map((p) => {
              const isAlpha = p.project_id === 'PROJ-ALPHA' || p.name.includes('Project Alpha');
              const displayStatus = p.status && p.status !== 'N/A' ? p.status : isAlpha ? 'Operational' : 'Planning';
              return {
                name: isAlpha ? 'Project Alpha' : p.name,
                code: p.project_id,
                displayCode: isAlpha ? '24P201' : p.project_id,
                status: displayStatus,
                progress: p.progress_percentage != null ? p.progress_percentage : isAlpha ? 31.3 : 0,
              };
            });

          if (apiProjects.length > 0) {
            setProjects(apiProjects);
          } else if (data.length > 0) {
            setProjects([]);
          } else {
            const activeFallbacks = FALLBACK_PROJECTS.filter((p) => !deleted.has(p.code));
            setProjects(activeFallbacks);
          }
        }
      })
      .catch(() => {
        const activeFallbacks = FALLBACK_PROJECTS.filter((p) => !deleted.has(p.code));
        setProjects(activeFallbacks);
      });
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  useAppDataRefresh(fetchProjects);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setFeedback(null);

    const generatedId = `PROJ-${newProjName.trim().toUpperCase().replace(/[^A-Z0-9]/g, '-').slice(0, 12)}-${Date.now().toString().slice(-4)}`;

    try {
      const res = await apiFetchSafe('/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: generatedId,
          name: newProjName.trim(),
          description: newProjDesc.trim() || 'PragatiSetu Infrastructure Construction Package',
          status: 'Planning',
        }),
      });

      if (res.ok) {
        unrecordDeletedProjectCode(generatedId);
        setFeedback({ type: 'success', message: `Project "${newProjName.trim()}" created successfully!` });
        notifyAppDataRefresh({ source: 'projects' });
        fetchProjects();
        setTimeout(() => {
          setIsModalOpen(false);
          setNewProjName('');
          setNewProjDesc('');
          setFeedback(null);
        }, 1200);
      } else {
        setFeedback({ type: 'error', message: res.error || 'Failed to create project.' });
      }
    } catch {
      setFeedback({ type: 'error', message: 'Network error creating project.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete || isDeleting) return;
    setIsDeleting(true);
    setDeleteError(null);

    try {
      const res = await apiFetchSafe(`/projects/${encodeURIComponent(projectToDelete.code)}`, {
        method: 'DELETE',
      });

      if (res.ok || res.status === 404 || res.error?.includes('not found')) {
        recordDeletedProjectCode(projectToDelete.code);
        clearFallbackData(projectToDelete.code);
        setProjects((prev) => {
          const next = prev.filter((p) => p.code !== projectToDelete.code);
          if (next.length === 0) {
            clearFallbackData();
          }
          return next;
        });
        notifyAppDataRefresh({ source: 'projects' });
        setProjectToDelete(null);
      } else {
        setDeleteError(res.error || 'Failed to delete project.');
      }
    } catch {
      recordDeletedProjectCode(projectToDelete.code);
      clearFallbackData(projectToDelete.code);
      setProjects((prev) => {
        const next = prev.filter((p) => p.code !== projectToDelete.code);
        if (next.length === 0) {
          clearFallbackData();
        }
        return next;
      });
      notifyAppDataRefresh({ source: 'projects' });
      setProjectToDelete(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto w-full space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded border border-primary/20">
              PragatiSetu Directory
            </span>
          </div>
          <h2 className="text-[24px] font-semibold text-on-surface mb-1">Projects Directory</h2>
          <p className="text-[14px] text-on-surface-variant">Manage and monitor all active and archived infrastructure projects.</p>
        </div>

        <button
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2.5 bg-primary text-on-primary text-[13px] font-bold rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-xs cursor-pointer shrink-0"
        >
          <Plus size={16} />
          <span>New Project</span>
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((p) => (
          <div key={p.code} className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <div className="w-10 h-10 rounded-lg bg-primary-fixed/30 text-primary flex items-center justify-center">
                <Folder size={20} />
              </div>
              <span className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-sm border ${
                p.status === 'Completed'
                  ? 'bg-status-completed/10 text-status-completed border-status-completed/30'
                  : p.status === 'Operational'
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                  : p.status === 'Planning'
                  ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30'
                  : 'bg-surface-container-high text-on-surface-variant border-surface-border'
              }`}>
                {p.status}
              </span>
            </div>
            <h3 className="text-[18px] font-semibold text-on-surface mb-1">{p.name}</h3>
            <p className="font-mono text-[13px] text-on-surface-variant mb-6">{p.displayCode ?? p.code}</p>
            
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-[12px] font-bold">
                <span className="text-on-surface-variant">Progress</span>
                <span className="text-on-surface">{p.progress}%</span>
              </div>
              <div className="w-full bg-surface-container rounded-full h-1.5">
                <div className="bg-primary h-1.5 rounded-full" style={{ width: `${p.progress}%` }}></div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Link href={`/?project_id=${encodeURIComponent(p.code)}`} className="flex-1 py-2 bg-surface-container-low hover:bg-surface-container-high border border-surface-border rounded-lg text-[13px] font-bold text-on-surface flex items-center justify-center gap-2 transition-colors">
                Open Dashboard <ArrowRight size={16} />
              </Link>
              <button
                type="button"
                onClick={() => {
                  setDeleteError(null);
                  setProjectToDelete({ code: p.code, name: p.name });
                }}
                title={`Delete ${p.name}`}
                aria-label={`Delete ${p.name}`}
                className="p-2 border border-surface-border hover:border-status-conflict/40 hover:bg-status-conflict/10 text-on-surface-variant hover:text-status-conflict rounded-lg transition-colors cursor-pointer shrink-0"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Modal */}
      {projectToDelete && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-surface-container-lowest border border-surface-border rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div className="flex items-center gap-2 font-bold text-[16px] text-status-conflict">
                <AlertTriangle size={18} />
                <span>Delete Project</span>
              </div>
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => {
                  setProjectToDelete(null);
                  setDeleteError(null);
                }}
                className="p-1 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-2 text-[13px] text-on-surface">
              <p>
                Are you sure you want to delete <span className="font-semibold text-on-surface">{projectToDelete.name}</span> (<code className="text-primary font-mono">{projectToDelete.code}</code>)?
              </p>
              <p className="text-on-surface-variant text-[12px]">
                This will permanently remove the project and its associated schedule activities, daily reports, review queue items, and audit records. This action cannot be undone.
              </p>
            </div>

            {deleteError && (
              <div className="p-2.5 rounded-lg text-[12px] flex items-center gap-2 bg-status-conflict/10 text-status-conflict border border-status-conflict/20">
                <X size={15} />
                <span>{deleteError}</span>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-3 border-t border-surface-border">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => {
                  setProjectToDelete(null);
                  setDeleteError(null);
                }}
                className="px-4 py-2 bg-surface-container hover:bg-surface-container-high text-on-surface font-semibold rounded-lg transition-colors cursor-pointer text-[13px]"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={handleDeleteProject}
                className="px-4 py-2 bg-status-conflict hover:bg-status-conflict/90 text-white font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer text-[13px] shadow-xs disabled:opacity-50"
              >
                {isDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                <span>{isDeleting ? 'Deleting...' : 'Delete Project'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Project Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-surface-container-lowest border border-surface-border rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div className="flex items-center gap-2 font-bold text-[16px] text-on-surface">
                <Building2 size={18} className="text-primary" />
                <span>Create New Project</span>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4 text-[13px]">
              <div>
                <label className="block font-semibold text-on-surface mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  value={newProjName}
                  onChange={(e) => setNewProjName(e.target.value)}
                  placeholder="e.g. Sector 7 Water Treatment Facility"
                  className="w-full px-3 py-2 rounded-lg bg-surface border border-surface-border text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div>
                <label className="block font-semibold text-on-surface mb-1">Description (Optional)</label>
                <textarea
                  rows={3}
                  value={newProjDesc}
                  onChange={(e) => setNewProjDesc(e.target.value)}
                  placeholder="Brief summary of construction scope and Primavera baseline linkage..."
                  className="w-full px-3 py-2 rounded-lg bg-surface border border-surface-border text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40 resize-none"
                />
              </div>

              {feedback && (
                <div
                  className={`p-2.5 rounded-lg text-[12px] flex items-center gap-2 ${
                    feedback.type === 'success'
                      ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
                      : 'bg-status-conflict/10 text-status-conflict border border-status-conflict/20'
                  }`}
                >
                  {feedback.type === 'success' ? <CheckCircle2 size={15} /> : <X size={15} />}
                  <span>{feedback.message}</span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-surface-border">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-surface-container hover:bg-surface-container-high text-on-surface font-semibold rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !newProjName.trim()}
                  className="px-4 py-2 bg-primary text-on-primary font-bold rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : null}
                  <span>Create Project</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
