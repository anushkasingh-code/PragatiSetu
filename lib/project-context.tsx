'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiFetchSafe } from './api';
import { useAppDataRefresh, notifyAppDataRefresh } from './app-sync';

export interface Project {
  project_id: string;
  name: string;
  description: string;
  displayCode?: string;
}

interface ProjectInfo {
  project_id: string;
  name: string;
  displayCode?: string;
}

interface ProjectContextType {
  selectedProjectId: string | null;
  setSelectedProjectId: (id: string | null) => void;
  isLoading: boolean;
  projects: ProjectInfo[];
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [selectedProjectId, setSelectedProjectIdState] = useState<string | null>(null);
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize from localStorage safely
  useEffect(() => {
    try {
      const stored = localStorage.getItem('pragati_selected_project');
      if (stored) setSelectedProjectIdState(stored);
    } catch {}
  }, []);

  const setSelectedProjectId = useCallback((id: string | null) => {
    setSelectedProjectIdState(id);
    try {
      if (id) {
        localStorage.setItem('pragati_selected_project', id);
      } else {
        localStorage.removeItem('pragati_selected_project');
      }
    } catch {}
    notifyAppDataRefresh({ source: 'project_selection' });
  }, []);

  const fetchProjects = useCallback(async () => {
    setIsLoading(true);
    const res = await apiFetchSafe<ProjectInfo[]>('/projects');
    if (res.ok && Array.isArray(res.data)) {
      setProjects(res.data);
      
      // If no projects exist, clear selected
      if (res.data.length === 0) {
        setSelectedProjectId(null);
      } else {
        // If current selected project doesn't exist in backend, reset to null
        setSelectedProjectIdState((currentSelected) => {
          if (currentSelected && !res.data.find((p) => p.project_id === currentSelected)) {
            // clear it locally
            try { localStorage.removeItem('pragati_selected_project'); } catch {}
            return null;
          }
          return currentSelected;
        });
      }
    } else {
      setProjects([]);
      setSelectedProjectId(null);
    }
    setIsLoading(false);
  }, [setSelectedProjectId]);

  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);

  useAppDataRefresh(() => {
    void fetchProjects();
  });

  return (
    <ProjectContext.Provider
      value={{
        selectedProjectId,
        setSelectedProjectId,
        isLoading,
        projects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjectContext() {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProjectContext must be used within a ProjectProvider');
  }
  return context;
}
