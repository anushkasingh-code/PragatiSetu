import { 
  Filter, 
  Mic, 
  BrainCircuit, 
  CheckCircle2, 
  AlertTriangle, 
  Check, 
  ArrowRightLeft, 
  X,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

export default function ReviewQueue() {
  return (
    <div className="p-6 h-[calc(100vh-4rem)] flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      
      {/* Header */}
      <div className="flex justify-between items-end shrink-0">
        <div>
          <h2 className="text-[24px] font-semibold text-on-surface">Review Queue</h2>
          <p className="text-[14px] text-on-surface-variant mt-1">Resolve AI-extracted field events against the WBS.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded bg-surface-container-high text-on-surface text-[11px] font-semibold border border-surface-border uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-status-review"></span>
            12 PENDING
          </span>
          <button className="px-4 py-1.5 border border-surface-border rounded-lg text-[12px] font-bold hover:bg-surface-container transition-colors flex items-center gap-2 bg-surface-container-lowest">
            <Filter size={16} /> Filter
          </button>
        </div>
      </div>

      {/* Split View */}
      <div className="flex-1 grid grid-cols-1 xl:grid-cols-12 gap-6 min-h-0">
        
        {/* Left Pane: Field Transcript */}
        <div className="xl:col-span-5 flex flex-col gap-4 min-h-0">
          <div className="bg-surface-container-lowest border border-surface-border rounded-xl shadow-sm p-5 flex flex-col h-full overflow-y-auto">
            
            <div className="flex justify-between items-center mb-5 border-b border-surface-border pb-4">
              <h3 className="text-[18px] font-semibold text-on-surface flex items-center gap-2">
                <Mic className="text-primary" size={20} />
                Field Transcript
              </h3>
              <span className="text-[13px] font-mono text-on-surface-variant bg-surface-container px-2 py-1 rounded">ID: EXT-8924</span>
            </div>

            <div className="bg-surface-container p-5 rounded-lg mb-6 border-l-4 border-primary">
              <p className="text-[16px] text-on-surface italic leading-relaxed">
                "Supervisor text input: Foundation pour at Sector 4 is complete, waiting on inspector approval for rebar."
              </p>
            </div>

            <h4 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-4">Extracted Data</h4>
            
            <div className="grid grid-cols-2 gap-y-5 gap-x-6">
              <div>
                <span className="block text-[12px] font-bold text-outline mb-1.5">IDENTIFIER</span>
                <span className="font-mono text-[13px] text-on-surface font-medium">--</span>
              </div>
              <div>
                <span className="block text-[12px] font-bold text-outline mb-1.5">ACTION</span>
                <span className="text-[14px] text-on-surface">Completed</span>
              </div>
              <div>
                <span className="block text-[12px] font-bold text-outline mb-1.5">OBJECT</span>
                <span className="text-[14px] text-on-surface">Foundation Pour, Rebar</span>
              </div>
              <div>
                <span className="block text-[12px] font-bold text-outline mb-1.5">LOCATION</span>
                <span className="text-[14px] text-on-surface">Sector 4</span>
              </div>
              <div className="col-span-2">
                <span className="block text-[12px] font-bold text-outline mb-1.5">IMPLIED STATUS</span>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-status-completed/10 text-status-completed text-[12px] font-bold border border-status-completed/20 uppercase">
                  <CheckCircle2 size={14} /> COMPLETE
                </span>
              </div>
            </div>

            <div className="mt-auto pt-6">
              <button className="w-full py-2.5 bg-surface-container-low hover:bg-surface-container-high border border-surface-border rounded-lg text-on-surface text-[14px] font-bold transition-colors flex items-center justify-center gap-2">
                <AlertTriangle size={18} /> Mark as Unplanned Event
              </button>
            </div>

          </div>
        </div>

        {/* Right Pane: AI Match Candidates */}
        <div className="xl:col-span-7 flex flex-col min-h-0 bg-surface-container-lowest border border-surface-border rounded-xl shadow-sm">
          
          <div className="p-5 border-b border-surface-border flex justify-between items-center bg-surface-bright rounded-t-xl shrink-0">
            <h3 className="text-[18px] font-semibold text-on-surface flex items-center gap-2">
              <BrainCircuit className="text-secondary" size={20} />
              AI Match Candidates
            </h3>
            <span className="text-[12px] font-bold text-on-surface-variant">3 Candidates Found</span>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            
            {/* Top Match */}
            <div className="border border-primary bg-primary-fixed/10 rounded-lg p-5 relative overflow-hidden transition-all shadow-sm">
              <div className="absolute top-0 right-0 bg-primary text-on-primary text-[11px] font-bold px-3 py-1 rounded-bl-lg tracking-wider">TOP MATCH</div>
              
              <div className="flex justify-between items-start mb-4 pr-24">
                <div>
                  <span className="font-mono text-[13px] font-semibold text-primary block mb-1">WBS: 24P201.04</span>
                  <h4 className="text-[16px] font-medium text-on-surface">Concrete Pour - Sector 4 Foundation</h4>
                </div>
                <div className="text-right">
                  <div className="text-[24px] font-bold text-status-completed leading-none mb-1">94%</div>
                  <div className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">CONFIDENCE</div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 mb-5 bg-surface-container-lowest p-2.5 rounded border border-surface-border">
                {['LOCATION MATCH', 'OBJECT MATCH', 'SCHEDULE ALIGNMENT'].map((label, idx) => (
                  <div key={idx} className={`text-center p-1 ${idx === 1 ? 'border-x border-surface-border' : ''}`}>
                    <div className="text-[10px] text-outline font-semibold uppercase tracking-wider mb-2">{label}</div>
                    <div className="w-full bg-surface-variant h-1.5 rounded-full overflow-hidden">
                      <div className="bg-status-completed h-full" style={{ width: ['100%', '90%', '85%'][idx] }}></div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-surface-container-lowest p-4 rounded border border-surface-border mb-5 text-[14px] text-on-surface-variant leading-relaxed">
                <strong className="text-on-surface text-[12px] font-bold block mb-1.5">AI Reasoning:</strong>
                Exact match on location ("Sector 4") and strong semantic match for action/object ("Foundation pour" ≈ "Concrete Pour - Foundation"). Activity is scheduled for this week.
              </div>

              <div className="flex gap-3">
                <button className="flex-1 bg-primary hover:bg-primary-container text-on-primary py-2.5 rounded-lg text-[14px] font-bold transition-colors flex justify-center items-center gap-2">
                  <Check size={18} /> ACCEPT MATCH
                </button>
                <button className="px-6 py-2.5 bg-surface-container-low hover:bg-surface-container-high border border-surface-border text-on-surface rounded-lg text-[14px] font-bold transition-colors">
                  MODIFY
                </button>
              </div>
            </div>

            {/* Match 2 */}
            <div className="border border-surface-border bg-surface-container-lowest rounded-lg p-5 transition-all hover:border-outline-variant">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <span className="font-mono text-[13px] font-semibold text-secondary block mb-1">WBS: 24P201.05</span>
                  <h4 className="text-[14px] font-medium text-on-surface">Rebar Installation - Sector 4</h4>
                </div>
                <div className="text-right">
                  <div className="text-[20px] font-bold text-status-review leading-none">68%</div>
                </div>
              </div>
              
              <div className="text-[14px] text-on-surface-variant mb-5">
                Matched location ("Sector 4") and object ("rebar"), but transcript indicates waiting *for* approval, not completion of installation.
              </div>
              
              <button className="w-full py-2 bg-surface-container-low hover:bg-surface-container-high border border-surface-border text-on-surface rounded-lg text-[14px] font-bold transition-colors flex justify-center items-center gap-2">
                <ArrowRightLeft size={16} /> SWITCH TO THIS
              </button>
            </div>

          </div>

          {/* Footer Navigation */}
          <div className="p-4 border-t border-surface-border bg-surface-bright rounded-b-xl flex justify-between items-center shrink-0">
            <button className="text-error hover:bg-error/10 px-4 py-2 rounded-lg text-[14px] font-bold transition-colors flex items-center gap-2 border border-error/20 bg-error-container/50">
              <X size={18} /> REJECT ALL
            </button>
            <div className="flex items-center gap-3">
              <button className="p-2 border border-surface-border rounded hover:bg-surface-container transition-colors text-on-surface-variant">
                <ChevronLeft size={18} />
              </button>
              <span className="text-[13px] font-mono font-medium">1 of 12</span>
              <button className="p-2 border border-surface-border rounded hover:bg-surface-container transition-colors text-on-surface-variant">
                <ChevronRight size={18} />
              </button>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
