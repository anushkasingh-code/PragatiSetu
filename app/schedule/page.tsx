import { Filter, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Schedule() {
  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-surface-bright w-full overflow-hidden">
      
      {/* Toolbar */}
      <div className="px-6 py-3 border-b border-surface-border bg-surface-container-lowest flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-1.5 bg-surface-container-lowest hover:bg-surface-container-low rounded-lg border border-surface-border text-[13px] font-medium text-on-surface transition-colors">
            <Filter size={16} /> Filter
          </button>
          
          <div className="h-6 w-px bg-surface-border mx-1"></div>
          
          <div className="flex items-center bg-surface-container-low rounded-lg border border-surface-border p-0.5">
            <button className="px-4 py-1.5 rounded-sm bg-surface-container-lowest text-[13px] font-medium text-on-surface shadow-sm">Days</button>
            <button className="px-4 py-1.5 rounded-sm text-[13px] font-medium text-on-surface-variant hover:text-on-surface">Weeks</button>
            <button className="px-4 py-1.5 rounded-sm text-[13px] font-medium text-on-surface-variant hover:text-on-surface">Months</button>
          </div>
        </div>
        
        <div className="flex items-center gap-5 text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
          <div className="flex items-center gap-2"><div className="w-4 h-1 bg-surface-border rounded-full"></div> Baseline</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 bg-primary rounded-sm"></div> Actual</div>
        </div>
      </div>

      {/* Split View */}
      <div className="flex-1 flex overflow-hidden bg-surface">
        
        {/* Left: WBS Table */}
        <div className="w-[40%] flex flex-col border-r border-surface-border bg-surface-container-lowest shrink-0 z-10 shadow-[2px_0_8px_rgba(0,0,0,0.02)]">
          
          {/* Header */}
          <div className="flex border-b border-surface-border bg-surface-container-low text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider sticky top-0 z-20">
            <div className="px-4 py-3 w-32 shrink-0 border-r border-surface-border">WBS Code</div>
            <div className="px-4 py-3 flex-1 border-r border-surface-border">Activity Name</div>
            <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border">% Comp</div>
            <div className="px-4 py-3 w-32 shrink-0">Status</div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto">
            {/* L1 */}
            <div className="flex border-b border-surface-border hover:bg-surface-container transition-colors group cursor-pointer bg-surface">
              <div className="px-4 py-3 w-32 shrink-0 border-r border-surface-border font-mono text-[13px] font-bold text-on-surface flex items-center gap-1">
                <ChevronDown size={16} className="text-outline" /> A.1
              </div>
              <div className="px-4 py-3 flex-1 border-r border-surface-border text-[14px] text-on-surface font-semibold truncate">
                Site Preparation Phase
              </div>
              <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface">45%</div>
              <div className="px-4 py-3 w-32 shrink-0 flex items-center">
                <span className="px-2 py-0.5 rounded-sm text-[10px] font-bold bg-primary-fixed/50 text-primary border border-primary-fixed uppercase tracking-wide">In Progress</span>
              </div>
            </div>

            {/* L2 - Completed */}
            <div className="flex border-b border-surface-border hover:bg-surface-container transition-colors group cursor-pointer bg-surface-container-lowest">
              <div className="px-4 py-3 pl-8 w-32 shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface flex items-center gap-1">
                <ChevronDown size={16} className="text-outline" /> A.1.1
              </div>
              <div className="px-4 py-3 flex-1 border-r border-surface-border text-[14px] text-on-surface truncate">
                Survey & Mapping
              </div>
              <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface">100%</div>
              <div className="px-4 py-3 w-32 shrink-0 flex items-center">
                <span className="px-2 py-0.5 rounded-sm text-[10px] font-bold bg-status-completed/10 text-status-completed border border-status-completed/20 uppercase tracking-wide">Completed</span>
              </div>
            </div>

            {/* L3 - Completed */}
            <div className="flex border-b border-surface-border hover:bg-surface-container transition-colors group cursor-pointer bg-surface-container-lowest">
              <div className="px-4 py-3 pl-12 w-32 shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface-variant flex items-center gap-1">
                <span className="w-4"></span> 24P201
              </div>
              <div className="px-4 py-3 flex-1 border-r border-surface-border text-[14px] text-on-surface-variant truncate">
                Topographical Survey
              </div>
              <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface-variant">100%</div>
              <div className="px-4 py-3 w-32 shrink-0 flex items-center">
                <span className="px-2 py-0.5 rounded-sm text-[10px] font-bold bg-status-completed/10 text-status-completed border border-status-completed/20 uppercase tracking-wide">Completed</span>
              </div>
            </div>

            {/* L2 - In Progress */}
            <div className="flex border-b border-surface-border hover:bg-surface-container transition-colors group cursor-pointer bg-surface-container-lowest">
              <div className="px-4 py-3 pl-8 w-32 shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface flex items-center gap-1">
                <ChevronRight size={16} className="text-outline" /> A.1.2
              </div>
              <div className="px-4 py-3 flex-1 border-r border-surface-border text-[14px] text-on-surface truncate">
                Clearance & Grading
              </div>
              <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface">20%</div>
              <div className="px-4 py-3 w-32 shrink-0 flex items-center">
                <span className="px-2 py-0.5 rounded-sm text-[10px] font-bold bg-primary-fixed/50 text-primary border border-primary-fixed uppercase tracking-wide">In Progress</span>
              </div>
            </div>

            {/* L2 - Not Started */}
            <div className="flex border-b border-surface-border hover:bg-surface-container transition-colors group cursor-pointer bg-surface-container-lowest">
              <div className="px-4 py-3 pl-8 w-32 shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface flex items-center gap-1">
                <ChevronRight size={16} className="text-outline" /> A.1.3
              </div>
              <div className="px-4 py-3 flex-1 border-r border-surface-border text-[14px] text-on-surface truncate">
                Foundation Excavation
              </div>
              <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border font-mono text-[13px] text-on-surface-variant">0%</div>
              <div className="px-4 py-3 w-32 shrink-0 flex items-center">
                <span className="px-2 py-0.5 rounded-sm text-[10px] font-bold bg-surface-container-high text-on-surface-variant border border-surface-border uppercase tracking-wide">Not Started</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Gantt Chart */}
        <div className="flex-1 overflow-x-auto overflow-y-hidden bg-surface-bright relative">
          
          {/* Grid Background */}
          <div 
            className="absolute inset-0 pointer-events-none" 
            style={{ 
              backgroundSize: '40px 100%', 
              backgroundImage: 'linear-gradient(to right, var(--color-surface-border) 1px, transparent 1px)' 
            }}
          ></div>

          {/* Timeline Header */}
          <div className="flex border-b border-surface-border bg-surface-container-lowest text-[11px] font-semibold text-on-surface-variant sticky top-0 z-20 min-w-max h-[45px]">
            <div className="absolute inset-0 flex items-end pb-2 px-1">
              <div className="w-[200px] shrink-0 border-l border-surface-border pl-2">Oct 01 - Oct 05</div>
              <div className="w-[200px] shrink-0 border-l border-surface-border pl-2">Oct 06 - Oct 10</div>
              <div className="w-[200px] shrink-0 border-l border-surface-border pl-2">Oct 11 - Oct 15</div>
              <div className="w-[200px] shrink-0 border-l border-surface-border pl-2">Oct 16 - Oct 20</div>
            </div>
          </div>

          {/* Timeline Body Rows */}
          <div className="min-w-max relative" style={{ minHeight: 'calc(100% - 45px)' }}>
            
            {/* Row 1 */}
            <div className="h-[45px] border-b border-surface-border relative group hover:bg-surface-container-low/50">
              <div className="absolute top-[10px] h-[4px] bg-surface-border rounded-full" style={{ left: '40px', width: '600px' }}></div>
              <div className="absolute top-[20px] h-[12px] bg-secondary rounded-sm shadow-sm flex items-center px-1 overflow-hidden" style={{ left: '40px', width: '620px' }}>
                <div className="h-full bg-primary/20" style={{ width: '45%' }}></div>
              </div>
            </div>

            {/* Row 2 */}
            <div className="h-[45px] border-b border-surface-border relative group hover:bg-surface-container-low/50">
              <div className="absolute top-[10px] h-[4px] bg-surface-border rounded-full" style={{ left: '40px', width: '160px' }}></div>
              <div className="absolute top-[22px] h-[8px] bg-status-completed rounded-sm shadow-sm" style={{ left: '40px', width: '160px' }}></div>
            </div>

            {/* Row 3 */}
            <div className="h-[45px] border-b border-surface-border relative group hover:bg-surface-container-low/50">
              <div className="absolute top-[10px] h-[4px] bg-surface-border rounded-full" style={{ left: '40px', width: '160px' }}></div>
              <div className="absolute top-[24px] h-[4px] bg-status-completed rounded-full" style={{ left: '40px', width: '160px' }}></div>
            </div>

            {/* Row 4 */}
            <div className="h-[45px] border-b border-surface-border relative group hover:bg-surface-container-low/50">
              <div className="absolute top-[10px] h-[4px] bg-surface-border rounded-full" style={{ left: '200px', width: '240px' }}></div>
              <div className="absolute top-[22px] h-[8px] bg-primary rounded-sm shadow-sm flex overflow-hidden" style={{ left: '240px', width: '280px' }}>
                <div className="h-full bg-primary-fixed w-[20%]"></div>
              </div>
              {/* Conflict indicator */}
              <div className="absolute top-[18px] w-4 h-4 rounded-full bg-status-conflict border-2 border-surface-container-lowest flex items-center justify-center z-10" style={{ left: '512px' }}></div>
            </div>

            {/* Row 5 */}
            <div className="h-[45px] border-b border-surface-border relative group hover:bg-surface-container-low/50">
              <div className="absolute top-[10px] h-[4px] bg-surface-border rounded-full" style={{ left: '440px', width: '200px' }}></div>
              <div className="absolute top-[22px] h-[8px] border border-outline border-dashed rounded-sm" style={{ left: '520px', width: '200px' }}></div>
            </div>

            {/* Today Marker */}
            <div className="absolute top-0 bottom-0 w-[2px] bg-status-review/50 border-l border-dashed border-status-review z-10" style={{ left: '280px' }}>
              <div className="absolute -top-5 -left-6 bg-status-review text-on-error font-semibold text-[10px] px-2 py-0.5 rounded tracking-wider">TODAY</div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
