import React from 'react';
import { PiggyBank, ArrowDownRight, TrendingUp, Cpu } from 'lucide-react';

interface SavingsCardProps {
  savings: {
    dense_baseline_cost: number;
    actual_cost: number;
    cost_savings_usd: number;
    cost_savings_percentage: number;
    token_savings: number;
  };
}

export default function SavingsCard({ savings }: SavingsCardProps) {
  const percentSaved = savings.cost_savings_percentage;
  const netSavedUsd = savings.cost_savings_usd;
  const tokensSaved = savings.token_savings;

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          Cost & Resource Savings
        </h2>
        <PiggyBank className="h-4 w-4 text-emerald-500" />
      </div>

      {/* Hero Savings Percentage Indicator */}
      <div className="bg-emerald-950/20 border border-emerald-900/50 p-4 rounded-lg flex items-center justify-between">
        <div className="space-y-0.5">
          <span className="text-[10px] uppercase font-semibold text-emerald-400/80 tracking-wider">Cost Efficiency Gain</span>
          <div className="text-2xl font-bold tracking-tight text-emerald-400">
            {percentSaved.toFixed(1)}% Saved
          </div>
        </div>
        <div className="h-10 w-10 rounded-full bg-emerald-900/30 border border-emerald-800/50 flex items-center justify-center text-emerald-400">
          <TrendingUp className="h-5 w-5" />
        </div>
      </div>

      {/* Detail statistics grid */}
      <div className="grid grid-cols-2 gap-4 text-xs">
        {/* Actual cost */}
        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900">
          <div className="text-zinc-500 mb-0.5">Actual TERA Cost</div>
          <div className="text-sm font-mono font-bold text-zinc-200">
            ${savings.actual_cost.toFixed(6)}
          </div>
        </div>

        {/* Dense baseline cost */}
        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900">
          <div className="text-zinc-500 mb-0.5">Dense Baseline Cost</div>
          <div className="text-sm font-mono font-bold text-zinc-400">
            ${savings.dense_baseline_cost.toFixed(6)}
          </div>
        </div>

        {/* Net Cost Saved */}
        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900 col-span-2 flex items-center justify-between">
          <span className="text-zinc-500">Net Dollar Savings</span>
          <span className="text-sm font-mono font-bold text-emerald-400 flex items-center gap-1">
            <ArrowDownRight className="h-3.5 w-3.5" />
            ${netSavedUsd.toFixed(6)}
          </span>
        </div>

        {/* Tokens Routed to Cheap */}
        <div className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-900 col-span-2 flex items-center justify-between">
          <span className="text-zinc-500 flex items-center gap-1">
            <Cpu className="h-3.5 w-3.5 text-zinc-500" />
            Tokens Routed to Cheap
          </span>
          <span className="text-sm font-mono font-bold text-indigo-400">
            {tokensSaved.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}
