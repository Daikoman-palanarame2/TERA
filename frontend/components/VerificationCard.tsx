import React from 'react';
import { ShieldCheck, ShieldAlert, Check, X, ShieldAlert as AlertIcon } from 'lucide-react';

interface VerificationCardProps {
  verification: {
    accepted: boolean;
    confidence: number;
    entropy: number | null;
    escalated: boolean;
    reason: string | null;
  };
  metadata: any;
  devMode: boolean;
}

export default function VerificationCard({ verification, metadata, devMode }: VerificationCardProps) {
  const isEscalated = verification.escalated;
  const hasEntropy = verification.entropy !== null;
  
  // Extract individual validator statuses from metadata (if available)
  const validationDetails = metadata?.validation_details || {
    schema_passed: !verification.reason?.includes('schema'),
    length_passed: !verification.reason?.includes('length'),
    stop_token_passed: !verification.reason?.includes('stop_token'),
    entropy_passed: !verification.reason?.includes('entropy') && (verification.entropy === null || verification.entropy <= 3.0)
  };

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          ROVL Verification
        </h2>
        {isEscalated ? (
          <ShieldAlert className="h-4 w-4 text-rose-500 animate-pulse" />
        ) : (
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
        )}
      </div>

      {/* ROVL Status Alert */}
      <div className={`p-4 rounded-lg border flex items-center justify-between ${
        isEscalated 
          ? 'bg-rose-950/20 border-rose-900/50 text-rose-400' 
          : 'bg-emerald-950/20 border-emerald-900/50 text-emerald-400'
      }`}>
        <div className="space-y-0.5">
          <span className="text-[10px] uppercase font-semibold tracking-wider opacity-85">ROVL Status</span>
          <div className="text-lg font-bold uppercase tracking-tight">
            {isEscalated ? 'Escalated to Dense' : 'Accepted Cheap output'}
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
          isEscalated ? 'bg-rose-950/50 text-rose-400 border border-rose-900' : 'bg-emerald-950/50 text-emerald-400 border border-emerald-900'
        }`}>
          {isEscalated ? 'Escalated' : 'Passed'}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        {/* Sequence Entropy */}
        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900 text-center">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Sequence Entropy</div>
          <div className={`text-lg font-mono font-bold ${
            hasEntropy && verification.entropy! > 3.0 ? 'text-rose-400' : 'text-zinc-200'
          }`}>
            {hasEntropy ? verification.entropy!.toFixed(3) : 'N/A'}
          </div>
        </div>

        {/* Escalation Reason */}
        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900 text-center">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Trigger Reason</div>
          <div className="text-xs font-semibold text-zinc-300 truncate pt-1 capitalize">
            {isEscalated ? (verification.reason || 'Validation Fail') : 'None'}
          </div>
        </div>
      </div>

      {/* Advanced Validator breakdown (visible only in Dev Mode) */}
      {devMode && (
        <div className="border-t border-zinc-900 pt-4 mt-2 space-y-3 animate-fade-in text-xs">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
            ROVL Validator Checklist
          </div>

          <div className="space-y-2">
            {/* Schema validator */}
            <div className="flex items-center justify-between py-0.5">
              <span className="text-zinc-400">Schema Validation Check</span>
              <span className={`flex items-center gap-1 font-semibold ${validationDetails.schema_passed ? 'text-emerald-500' : 'text-rose-500'}`}>
                {validationDetails.schema_passed ? (
                  <>
                    <Check className="h-3.5 w-3.5" /> Passed
                  </>
                ) : (
                  <>
                    <X className="h-3.5 w-3.5" /> Failed
                  </>
                )}
              </span>
            </div>

            {/* Length validator */}
            <div className="flex items-center justify-between py-0.5">
              <span className="text-zinc-400">Character Range Bounds Check</span>
              <span className={`flex items-center gap-1 font-semibold ${validationDetails.length_passed ? 'text-emerald-500' : 'text-rose-500'}`}>
                {validationDetails.length_passed ? (
                  <>
                    <Check className="h-3.5 w-3.5" /> Passed
                  </>
                ) : (
                  <>
                    <X className="h-3.5 w-3.5" /> Failed
                  </>
                )}
              </span>
            </div>

            {/* Stop token validator */}
            <div className="flex items-center justify-between py-0.5">
              <span className="text-zinc-400">Stop Sequence Termination Check</span>
              <span className={`flex items-center gap-1 font-semibold ${validationDetails.stop_token_passed ? 'text-emerald-500' : 'text-rose-500'}`}>
                {validationDetails.stop_token_passed ? (
                  <>
                    <Check className="h-3.5 w-3.5" /> Passed
                  </>
                ) : (
                  <>
                    <X className="h-3.5 w-3.5" /> Failed
                  </>
                )}
              </span>
            </div>

            {/* Entropy validator */}
            <div className="flex items-center justify-between py-0.5">
              <span className="text-zinc-400">Entropy Threshold Limit Check (H &le; 3.0)</span>
              <span className={`flex items-center gap-1 font-semibold ${validationDetails.entropy_passed ? 'text-emerald-500' : 'text-rose-500'}`}>
                {validationDetails.entropy_passed ? (
                  <>
                    <Check className="h-3.5 w-3.5" /> Passed
                  </>
                ) : (
                  <>
                    <X className="h-3.5 w-3.5" /> Failed
                  </>
                )}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
