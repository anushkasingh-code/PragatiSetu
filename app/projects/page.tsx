import { Folder, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function Projects() {
  const projects = [
    { name: 'Project Alpha', code: '24P201', status: 'Operational', progress: 68.2 },
    { name: 'Project Beta', code: '24P305', status: 'Planning', progress: 12.5 },
    { name: 'Project Gamma', code: '23P890', status: 'Completed', progress: 100 },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <div className="mb-8">
        <h2 className="text-[24px] font-semibold text-on-surface mb-2">Projects Directory</h2>
        <p className="text-[16px] text-on-surface-variant">Manage and monitor all active and archived projects.</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(p => (
          <div key={p.code} className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <div className="w-10 h-10 rounded-lg bg-primary-fixed/30 text-primary flex items-center justify-center">
                <Folder size={20} />
              </div>
              <span className={`text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-sm ${p.status === 'Completed' ? 'bg-status-completed/10 text-status-completed border border-status-completed/20' : p.status === 'Operational' ? 'bg-primary/10 text-primary border border-primary/20' : 'bg-surface-container-high text-on-surface-variant border border-surface-border'}`}>
                {p.status}
              </span>
            </div>
            <h3 className="text-[18px] font-semibold text-on-surface mb-1">{p.name}</h3>
            <p className="font-mono text-[13px] text-on-surface-variant mb-6">{p.code}</p>
            
            <div className="space-y-2 mb-6">
              <div className="flex justify-between text-[12px] font-bold">
                <span className="text-on-surface-variant">Progress</span>
                <span className="text-on-surface">{p.progress}%</span>
              </div>
              <div className="w-full bg-surface-container rounded-full h-1.5">
                <div className="bg-primary h-1.5 rounded-full" style={{ width: `${p.progress}%` }}></div>
              </div>
            </div>

            <Link href="/" className="w-full py-2 bg-surface-container-low hover:bg-surface-container-high border border-surface-border rounded-lg text-[13px] font-bold text-on-surface flex items-center justify-center gap-2 transition-colors">
              Open Dashboard <ArrowRight size={16} />
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
