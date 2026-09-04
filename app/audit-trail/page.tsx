import { Search, Calendar, Filter, Download, History, ArrowRight, RotateCw, PersonStanding, BrainCircuit } from 'lucide-react';

export default function AuditTrail() {
  return (
    <div className="p-6 max-w-5xl mx-auto w-full">
      
      {/* Header & Filters */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h2 className="text-[32px] font-bold text-on-surface leading-tight">Audit & Compliance Trail</h2>
          <p className="text-[14px] text-on-surface-variant mt-1">Immutable ledger of schedule modifications and system actions.</p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 bg-surface-container-lowest p-2 rounded-xl border border-surface-border shadow-sm">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline" size={16} />
            <input 
              type="text" 
              placeholder="Activity ID..." 
              className="pl-9 pr-4 py-1.5 rounded-lg border-none bg-surface-container-low text-on-surface focus:ring-2 focus:ring-primary text-[14px] w-40"
            />
          </div>
          <div className="h-6 w-px bg-surface-border"></div>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-surface-container-low transition-colors font-mono text-[13px] text-on-surface-variant">
            <Calendar size={16} /> Last 7 Days
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-surface-container-low transition-colors font-mono text-[13px] text-on-surface-variant">
            <Filter size={16} /> All Decisions
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-border bg-surface-container-low hover:bg-surface-container-high transition-colors font-mono text-[13px] text-on-surface">
            <Download size={16} /> Export
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        
        {/* Audit Card 1: AUTO_LINK */}
        <div className="bg-surface-container-lowest rounded-xl border border-surface-border shadow-sm overflow-hidden flex flex-col md:flex-row">
          
          {/* Metadata */}
          <div className="w-full md:w-64 bg-surface-container-low p-5 border-b md:border-b-0 md:border-r border-surface-border flex flex-col justify-between shrink-0">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-semibold tracking-wider uppercase text-primary bg-primary-fixed/30 border border-primary/20 px-2 py-0.5 rounded-sm">AUTO_LINK</span>
                <span className="font-mono text-[13px] text-on-surface-variant">09:42 AM</span>
              </div>
              <p className="text-[14px] text-on-surface mt-2 leading-relaxed">System automatically matched voice transcript to schedule activity.</p>
            </div>
            <div className="mt-6 pt-4 border-t border-surface-border space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-[12px] font-bold text-on-surface-variant">Confidence</span>
                <span className="font-mono text-[13px] text-status-completed font-semibold">94%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[12px] font-bold text-on-surface-variant">User</span>
                <span className="font-mono text-[13px] text-on-surface">System (AI)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[12px] font-bold text-on-surface-variant">Hash</span>
                <span className="font-mono text-[13px] text-outline">a7f9b2c4</span>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded bg-surface-container-highest flex items-center justify-center">
                <History className="text-on-surface-variant" size={20} />
              </div>
              <div>
                <h3 className="text-[18px] font-semibold text-on-surface">24P201 - Pour Foundation Slab</h3>
                <p className="font-mono text-[13px] text-on-surface-variant">WBS: L6-CIV-04</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* BEFORE */}
              <div className="border border-surface-border rounded-lg bg-audit-previous p-4">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant mb-4 flex items-center gap-1.5">
                  <History size={14} /> PREVIOUS STATE
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-[14px] text-on-surface-variant">Status</span>
                    <span className="font-mono text-[13px] text-on-surface">NOT_STARTED</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[14px] text-on-surface-variant">% Complete</span>
                    <span className="font-mono text-[13px] text-on-surface">0%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[14px] text-on-surface-variant">Actual Start</span>
                    <span className="font-mono text-[13px] text-on-surface/50">--/--/----</span>
                  </div>
                </div>
              </div>

              {/* AFTER */}
              <div className="border border-status-completed/20 rounded-lg bg-audit-new p-4 relative">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-status-completed mb-4 flex items-center gap-1.5">
                  <RotateCw size={14} /> NEW STATE
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-[14px] text-on-surface-variant">Status</span>
                    <span className="font-mono text-[13px] text-status-completed font-bold">IN_PROGRESS</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[14px] text-on-surface-variant">% Complete</span>
                    <span className="font-mono text-[13px] text-status-completed font-bold">25%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[14px] text-on-surface-variant">Actual Start</span>
                    <span className="font-mono text-[13px] text-on-surface">10/24/2023</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-5 p-4 bg-surface-container-low rounded-lg border border-surface-border border-dashed">
              <p className="text-[12px] font-bold text-on-surface-variant mb-1.5">Source Transcript Snippet:</p>
              <p className="font-mono text-[13px] text-on-surface italic">"Yeah we started pouringquot;Yeah we started pouring the foundation on sector four today. About a quarter of the way done.way done."quot;</p>
            </div>
          </div>
        </div>

        {/* Audit Card 2: HUMAN_REVIEW */}
        <div className="bg-surface-container-lowest rounded-xl border border-surface-border shadow-sm overflow-hidden flex flex-col md:flex-row">
          
          {/* Metadata */}
          <div className="w-full md:w-64 bg-surface-container-low p-5 border-b md:border-b-0 md:border-r border-surface-border flex flex-col justify-between shrink-0">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-semibold tracking-wider uppercase text-secondary bg-secondary/10 border border-secondary/20 px-2 py-0.5 rounded-sm">HUMAN_REVIEW</span>
                <span className="font-mono text-[13px] text-on-surface-variant">Yesterday</span>
              </div>
              <p className="text-[14px] text-on-surface mt-2 leading-relaxed">Planner manually corrected AI suggestion before committing.</p>
            </div>
            <div className="mt-6 pt-4 border-t border-surface-border space-y-1.5">
              <div className="flex justify-between items-center">
                <span className="text-[12px] font-bold text-on-surface-variant">Original Conf.</span>
                <span className="font-mono text-[13px] text-status-review font-semibold">68%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[12px] font-bold text-on-surface-variant">User</span>
                <span className="font-mono text-[13px] text-on-surface">J. Doe (Planner)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[12px] font-bold text-on-surface-variant">Hash</span>
                <span className="font-mono text-[13px] text-outline">c92m1x8z</span>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded bg-surface-container-highest flex items-center justify-center">
                <RotateCw className="text-on-surface-variant" size={20} />
              </div>
              <div>
                <h3 className="text-[18px] font-semibold text-on-surface">18E105 - Install Main Switchgear</h3>
                <p className="font-mono text-[13px] text-on-surface-variant">WBS: L5-ELEC-01</p>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* PREVIOUS */}
              <div className="border border-surface-border rounded-lg bg-audit-previous p-4">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant mb-4 flex items-center gap-1.5">
                  <History size={14} /> PREVIOUS
                </div>
                <div className="flex justify-between">
                  <span className="text-[14px] text-on-surface-variant">% Complete</span>
                  <span className="font-mono text-[13px] text-on-surface">50%</span>
                </div>
              </div>

              {/* AI SUGGESTION */}
              <div className="border border-status-review/30 rounded-lg bg-surface-container-low p-4 opacity-70">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-status-review mb-4 flex items-center gap-1.5">
                  <BrainCircuit size={14} /> AI SUGGESTION
                </div>
                <div className="flex justify-between">
                  <span className="text-[14px] text-on-surface-variant">% Complete</span>
                  <span className="font-mono text-[13px] text-status-review line-through">100%</span>
                </div>
              </div>

              {/* HUMAN FINAL */}
              <div className="border border-surface-border rounded-lg bg-audit-new p-4 shadow-sm relative">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-status-completed mb-4 flex items-center gap-1.5">
                  <PersonStanding size={14} /> HUMAN FINAL
                </div>
                <div className="flex justify-between">
                  <span className="text-[14px] text-on-surface-variant">% Complete</span>
                  <span className="font-mono text-[13px] text-status-completed font-bold">85%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="text-center mt-4">
          <button className="text-[12px] font-bold text-primary border border-primary/20 hover:bg-primary/5 transition-colors py-2.5 px-8 rounded-lg">
            Load More History...
          </button>
        </div>

      </div>
    </div>
  );
}
