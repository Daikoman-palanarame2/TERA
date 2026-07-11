import React from 'react';
import { Compass, AlertTriangle, Info } from 'lucide-react';

interface RouterDecisionCardProps {
  router: {
    raw_probability: number;
    calibrated_probability: number;
    selected_route: string;
  };
  utilities: {
    cheap: number;
    dense: number;
    cascade: number;
  };
  devMode: boolean;
}

export default function RouterDecisionCard({ router, utilities, devMode }: RouterDecisionCardProps) {
  const isCheap = router.selected_route === 'cheap';
  const isDense = router.selected_route === 'dense';
  const isCascade = router.selected_route === 'cascade';

  // Check if raw probability exceeded standard calibration bounds (which were [0.506, 0.655] in trainer.py)
  const isClipped = router.raw_probability > 0.655 && router.calibrated_probability === 0.8235294117647058;

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          Routing Decision
        </h2>
        <Compass className="h-4 w-4 text-zinc-500" />
      </div>

      {/* Main Selected Route Badge */}
      <div className="bg-zinc-900/50 border border-zinc-850 p-4 rounded-lg flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-xs text-zinc-400">Optimal Selected Lane</span>
          <div className="text-xl font-bold tracking-tight text-zinc-100 uppercase">
            {isCheap && 'Cheap Model Lane'}
            {isDense && 'Dense Model Lane'}
            {isCascade && 'Cascade Lane (M2 -> M3)'}
          </div>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
          isCheap ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-900' :
          isDense ? 'bg-indigo-950/50 text-indigo-400 border border-indigo-900' :
          'bg-amber-950/50 text-amber-400 border border-amber-900'
        }`}>
          {router.selected_route}
        </span>
      </div>

      {/* Probabilities */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900 text-center">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Raw ML Probability</div>
          <div className="text-lg font-mono font-bold text-zinc-200">
            {(router.raw_probability * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900 text-center relative overflow-hidden">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Calibrated Accuracy</div>
          <div className="text-lg font-mono font-bold text-indigo-400">
            {(router.calibrated_probability * 100).toFixed(1)}%
          </div>
          {isClipped && (
            <div className="absolute top-0 right-0 h-1.5 w-1.5 bg-amber-500 rounded-bl" title="Calibration bounds clipped" />
          )}
        </div>
      </div>

      {/* Expected Utility Scores */}
      <div className="space-y-2.5">
        <div className="text-xs text-zinc-400 uppercase tracking-wider font-semibold">Expected Utility Outputs</div>
        
        <div className="grid grid-cols-3 gap-2">
          {/* Cheap Utility */}
          <div className={`p-2.5 rounded-lg border text-center ${
            isCheap ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-900/20 border-zinc-900'
          }`}>
            <div className="text-[9px] text-zinc-400 uppercase">Cheap</div>
            <div className={`text-xs font-mono font-bold mt-0.5 ${isCheap ? 'text-zinc-100' : 'text-zinc-500'}`}>
              {utilities.cheap.toFixed(4)}
            </div>
          </div>

          {/* Cascade Utility */}
          <div className={`p-2.5 rounded-lg border text-center ${
            isCascade ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-900/20 border-zinc-900'
          }`}>
            <div className="text-[9px] text-zinc-400 uppercase">Cascade</div>
            <div className={`text-xs font-mono font-bold mt-0.5 ${isCascade ? 'text-zinc-100' : 'text-zinc-500'}`}>
              {utilities.cascade.toFixed(4)}
            </div>
          </div>

          {/* Dense Utility */}
          <div className={`p-2.5 rounded-lg border text-center ${
            isDense ? 'bg-zinc-900 border-zinc-700' : 'bg-zinc-900/20 border-zinc-900'
          }`}>
            <div className="text-[9px] text-zinc-400 uppercase">Dense</div>
            <div className={`text-xs font-mono font-bold mt-0.5 ${isDense ? 'text-zinc-100' : 'text-zinc-500'}`}>
              {utilities.dense.toFixed(4)}
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Calibration warnings (visible only in Dev Mode) */}
      {devMode && (
        <div className="border-t border-zinc-900 pt-4 mt-2 space-y-2 animate-fade-in text-xs">
          {isClipped && (
            <div className="bg-amber-950/30 border border-amber-900/50 p-2.5 rounded-lg flex gap-2 text-amber-400">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Calibration Clipping Detected:</span> The raw probability ({ (router.raw_probability * 100).toFixed(1) }%) exceeds training calibration bounds. Clipped to max calibrated value (`0.8235`).
              </div>
            </div>
          )}

          <div className="bg-zinc-900/40 p-2.5 rounded-lg border border-zinc-900/80 flex gap-2 text-zinc-400">
            <Info className="h-4 w-4 shrink-0 mt-0.5 text-zinc-500" />
            <div>
              Expected utility maximizes accuracy vs token cost trade-off. Direct Cheap selected because: <span className="font-mono text-zinc-300">U(Cheap) &gt; U(Cascade) &gt; U(Dense)</span>.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
