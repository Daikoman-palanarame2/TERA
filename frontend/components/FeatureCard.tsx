import React from 'react';
import { Eye, Code, BrainCircuit, Binary, Hash } from 'lucide-react';

interface FeatureCardProps {
  features: {
    length: number;
    symbol_ratio: number;
    regex_density: number;
    bm25_score: number;
    code_detected?: boolean;
    math_detected?: boolean;
    reasoning_count?: number;
    numeric_density?: number;
  };
  devMode: boolean;
}

export default function FeatureCard({ features, devMode }: FeatureCardProps) {
  // Compute standard visual progress ratios
  const lengthRatio = Math.min((features.length / 1000) * 100, 100);
  const symbolRatio = Math.min(features.symbol_ratio * 100, 100);
  const regexRatio = Math.min((features.regex_density / 10) * 100, 100);
  const bm25Ratio = Math.min((features.bm25_score / 15.0) * 100, 100);

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          Feature Extraction
        </h2>
        <span className="text-zinc-500 hover:text-zinc-300">
          <Eye className="h-4 w-4" />
        </span>
      </div>

      <div className="space-y-4">
        {/* Prompt Length */}
        <div>
          <div className="flex justify-between text-xs text-zinc-400 mb-1">
            <span>Prompt Character Length</span>
            <span className="font-mono text-zinc-200">{features.length} chars</span>
          </div>
          <div className="w-full bg-zinc-900 h-2.5 rounded-full overflow-hidden border border-zinc-850">
            <div 
              className="bg-indigo-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${lengthRatio}%` }}
            />
          </div>
        </div>

        {/* Symbol Ratio */}
        <div>
          <div className="flex justify-between text-xs text-zinc-400 mb-1">
            <span>Symbol Density Ratio</span>
            <span className="font-mono text-zinc-200">{(features.symbol_ratio * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-zinc-900 h-2.5 rounded-full overflow-hidden border border-zinc-850">
            <div 
              className="bg-indigo-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${symbolRatio}%` }}
            />
          </div>
        </div>

        {/* Regex Match count */}
        <div>
          <div className="flex justify-between text-xs text-zinc-400 mb-1">
            <span>Regex Keyword Matches</span>
            <span className="font-mono text-zinc-200">{features.regex_density} matched</span>
          </div>
          <div className="w-full bg-zinc-900 h-2.5 rounded-full overflow-hidden border border-zinc-850">
            <div 
              className="bg-indigo-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${regexRatio}%` }}
            />
          </div>
        </div>

        {/* BM25 Similarity score */}
        <div>
          <div className="flex justify-between text-xs text-zinc-400 mb-1">
            <span>BM25 Lexical Similarity</span>
            <span className="font-mono text-zinc-200">{features.bm25_score.toFixed(3)}</span>
          </div>
          <div className="w-full bg-zinc-900 h-2.5 rounded-full overflow-hidden border border-zinc-850">
            <div 
              className="bg-indigo-500 h-full rounded-full transition-all duration-500" 
              style={{ width: `${bm25Ratio}%` }}
            />
          </div>
        </div>
      </div>

      {/* Advanced Diagnostics (visible only in Dev Mode) */}
      {devMode && (
        <div className="border-t border-zinc-900 pt-4 mt-2 space-y-3 animate-fade-in">
          <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
            Advanced Feature Analytics
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            {/* Code matching */}
            <div className="bg-zinc-900/50 p-2 rounded-lg border border-zinc-900 flex items-center justify-between">
              <span className="text-zinc-400 flex items-center gap-1.5">
                <Code className="h-3.5 w-3.5" />
                Code Domain
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                features.code_detected ? 'bg-indigo-950/50 text-indigo-400 border border-indigo-900' : 'bg-zinc-950 text-zinc-600 border border-zinc-900'
              }`}>
                {features.code_detected ? 'Matched' : 'No Match'}
              </span>
            </div>

            {/* Math matching */}
            <div className="bg-zinc-900/50 p-2 rounded-lg border border-zinc-900 flex items-center justify-between">
              <span className="text-zinc-400 flex items-center gap-1.5">
                <Binary className="h-3.5 w-3.5" />
                Math Domain
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                features.math_detected ? 'bg-purple-950/50 text-purple-400 border border-purple-900' : 'bg-zinc-950 text-zinc-600 border border-zinc-900'
              }`}>
                {features.math_detected ? 'Matched' : 'No Match'}
              </span>
            </div>

            {/* Reasoning markers */}
            <div className="bg-zinc-900/50 p-2 rounded-lg border border-zinc-900 flex items-center justify-between col-span-2">
              <span className="text-zinc-400 flex items-center gap-1.5">
                <BrainCircuit className="h-3.5 w-3.5" />
                Reasoning Markers
              </span>
              <span className="font-mono text-zinc-200 font-bold bg-zinc-950 border border-zinc-900 px-2 py-0.5 rounded text-[10px]">
                {features.reasoning_count} instances
              </span>
            </div>

            {/* Numeric ratio */}
            <div className="bg-zinc-900/50 p-2 rounded-lg border border-zinc-900 flex items-center justify-between col-span-2">
              <span className="text-zinc-400 flex items-center gap-1.5">
                <Hash className="h-3.5 w-3.5" />
                Digit Density
              </span>
              <span className="font-mono text-zinc-200 font-bold bg-zinc-950 border border-zinc-900 px-2 py-0.5 rounded text-[10px]">
                {(features.numeric_density ? features.numeric_density * 100 : 0.0).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
