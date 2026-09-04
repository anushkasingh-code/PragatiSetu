'use client';

import { UploadCloud, Mic, Sparkles, FileText, CheckCircle2 } from 'lucide-react';
import { useRef, useState } from 'react';

export default function ReportsIngestionHub() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [voiceProcessed, setVoiceProcessed] = useState(false);

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleProcessVoice = () => {
    setIsProcessingVoice(true);
    setTimeout(() => {
      setIsProcessingVoice(false);
      setVoiceProcessed(true);
    }, 1500);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <div className="mb-8">
        <h2 className="text-[24px] font-semibold text-on-surface mb-2">Report Ingestion Hub</h2>
        <p className="text-[16px] text-on-surface-variant">Process field updates and operational reports via file or voice.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Column */}
        <div className="xl:col-span-2 flex flex-col gap-6">
          
          {/* Drag & Drop */}
          <div 
            onClick={handleFileClick}
            className={`bg-surface-container-lowest border rounded-xl p-10 flex flex-col items-center justify-center border-dashed transition-colors cursor-pointer group h-[300px] ${selectedFile ? 'border-primary bg-primary/5' : 'border-surface-border hover:bg-surface-container-low'}`}
          >
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              onChange={handleFileChange} 
              accept=".txt,.csv,.xlsx"
            />
            
            {selectedFile ? (
              <>
                <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mb-5 text-primary">
                  <CheckCircle2 size={32} />
                </div>
                <h3 className="text-[18px] font-semibold text-on-surface mb-2">File Selected</h3>
                <p className="font-mono text-[14px] text-primary mb-6 text-center">{selectedFile.name}</p>
                <button className="px-6 py-2.5 bg-primary text-on-primary text-[12px] font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-sm">
                  Upload & Process
                </button>
              </>
            ) : (
              <>
                <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center mb-5 group-hover:scale-105 transition-transform duration-300">
                  <UploadCloud size={32} className="text-primary" />
                </div>
                <h3 className="text-[18px] font-semibold text-on-surface mb-2">Drag & Drop Reports</h3>
                <p className="text-[14px] text-on-surface-variant mb-6 text-center">Support for TXT, CSV, and XLSX WBS exports.</p>
                <button className="px-6 py-2.5 bg-surface-container-lowest text-primary text-[12px] font-bold rounded-lg hover:bg-surface-container-low transition-colors border border-surface-border shadow-sm">
                  Browse Files
                </button>
              </>
            )}
          </div>

          {/* Voice Input */}
          <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-[18px] font-semibold text-on-surface flex items-center gap-2">
                <Mic className="text-primary" size={20} /> Local Voice Input
              </h3>
              <span className={`px-3 py-1 bg-surface-container-low rounded text-[11px] font-semibold tracking-wider uppercase flex items-center gap-2 border border-surface-border ${voiceProcessed ? 'text-status-completed' : 'text-on-surface-variant'}`}>
                {!voiceProcessed && <div className="w-2 h-2 rounded-full bg-status-conflict animate-pulse"></div>}
                {voiceProcessed ? 'Processed' : 'Recording'}
              </span>
            </div>
            
            {/* Waveform Mock */}
            <div className="h-20 bg-surface-container-low rounded-lg border border-surface-border mb-5 flex items-end justify-center gap-1.5 p-3 overflow-hidden">
              {[20, 70, 40, 90, 30, 80, 100, 60, 40, 85, 30, 70].map((h, i) => (
                <div 
                  key={i} 
                  className={`w-2 rounded-t-sm transition-all duration-500 ${voiceProcessed ? 'bg-status-completed' : 'bg-primary'}`} 
                  style={{ height: voiceProcessed ? '10%' : `${h}%`, opacity: 0.8 }}
                ></div>
              ))}
            </div>

            <div className={`border rounded-lg p-5 mb-5 transition-colors ${voiceProcessed ? 'bg-status-completed/10 border-status-completed/20' : 'bg-surface-bright border-surface-border'}`}>
              <p className="font-mono text-[13px] text-on-surface leading-relaxed">
                "Activity 24P201 foundation pour completed. Moving to curing phase. Next is steel erection on Monday..."
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <button 
                onClick={() => setVoiceProcessed(false)} 
                className="px-5 py-2.5 border border-surface-border text-on-surface text-[12px] font-bold rounded-lg hover:bg-surface-container-high transition-colors bg-surface-container-lowest"
              >
                Reset
              </button>
              <button 
                onClick={handleProcessVoice}
                disabled={isProcessingVoice || voiceProcessed}
                className={`px-5 py-2.5 text-[12px] font-bold rounded-lg transition-colors flex items-center gap-2 shadow-sm ${voiceProcessed ? 'bg-status-completed text-surface-container-lowest' : 'bg-primary text-on-primary hover:bg-primary/90'} disabled:opacity-70`}
              >
                {voiceProcessed ? <CheckCircle2 size={16} /> : <Sparkles size={16} />}
                {isProcessingVoice ? 'Processing...' : voiceProcessed ? 'Processed Successfully' : 'Process Spoken Update'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="xl:col-span-1 flex flex-col gap-6">
          
          {/* Active Pipeline */}
          <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 shadow-sm">
            <h3 className="text-[18px] font-semibold text-on-surface mb-6">Active Pipeline</h3>
            <div className="space-y-5">
              <div>
                <div className="flex justify-between text-[12px] font-bold mb-2">
                  <span className="text-on-surface">Uploading field_report_v2.csv</span>
                  <span className="text-status-completed">Done</span>
                </div>
                <div className="w-full bg-surface-container rounded-full h-1.5">
                  <div className="bg-status-completed h-1.5 rounded-full w-full"></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-[12px] font-bold mb-2">
                  <span className="text-on-surface">Validating structure</span>
                  <span className="text-status-completed">Done</span>
                </div>
                <div className="w-full bg-surface-container rounded-full h-1.5">
                  <div className="bg-status-completed h-1.5 rounded-full w-full"></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-[12px] font-bold mb-2">
                  <span className="text-on-surface">Extracting Events</span>
                  <span className="text-status-review">In Progress (45%)</span>
                </div>
                <div className="w-full bg-surface-container rounded-full h-1.5">
                  <div className="bg-status-review h-1.5 rounded-full w-[45%]"></div>
                </div>
              </div>
              <div className="opacity-50">
                <div className="flex justify-between text-[12px] font-bold mb-2">
                  <span className="text-on-surface">Matching to WBS</span>
                  <span className="text-on-surface-variant">Waiting</span>
                </div>
                <div className="w-full bg-surface-container rounded-full h-1.5">
                  <div className="bg-surface-border h-1.5 rounded-full w-0"></div>
                </div>
              </div>
            </div>
          </div>

          {/* History */}
          <div className="bg-surface-container-lowest border border-surface-border rounded-xl flex-1 flex flex-col shadow-sm overflow-hidden">
            <div className="p-5 border-b border-surface-border">
              <h3 className="text-[18px] font-semibold text-on-surface">Ingestion History</h3>
            </div>
            <div className="overflow-y-auto flex-1">
              <table className="w-full text-left">
                <thead className="bg-surface-container-low text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider border-b border-surface-border">
                  <tr>
                    <th className="px-5 py-3">Filename</th>
                    <th className="px-5 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  <tr className="hover:bg-audit-previous transition-colors">
                    <td className="px-5 py-3">
                      <div className="font-mono text-[13px] text-on-surface">Q3_Update.xlsx</div>
                      <div className="text-[12px] text-on-surface-variant mt-1">Today, 09:41 AM</div>
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center px-2 py-1 text-[11px] font-bold uppercase tracking-wide bg-audit-new text-status-completed border border-status-completed/20 rounded-sm">Processed</span>
                    </td>
                  </tr>
                  <tr className="hover:bg-audit-previous transition-colors">
                    <td className="px-5 py-3">
                      <div className="font-mono text-[13px] text-on-surface">voice_note_891.wav</div>
                      <div className="text-[12px] text-on-surface-variant mt-1">Yesterday, 14:20</div>
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center px-2 py-1 text-[11px] font-bold uppercase tracking-wide bg-audit-new text-status-completed border border-status-completed/20 rounded-sm">Processed</span>
                    </td>
                  </tr>
                  <tr className="hover:bg-audit-previous transition-colors">
                    <td className="px-5 py-3">
                      <div className="font-mono text-[13px] text-on-surface">corrupted_data.csv</div>
                      <div className="text-[12px] text-on-surface-variant mt-1">Oct 24, 11:05</div>
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center px-2 py-1 text-[11px] font-bold uppercase tracking-wide bg-error-container text-error border border-error/20 rounded-sm">Rejected</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
