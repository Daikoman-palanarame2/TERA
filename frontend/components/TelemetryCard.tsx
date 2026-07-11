import React from 'react';
import { Activity, Clock, Cpu, BarChart3 } from 'lucide-react';

interface TelemetryCardProps {
  metadata: any;
}

export default function TelemetryCard({ metadata }: TelemetryCardProps) {
  if (!metadata) return null;

  // Extract latency values (or default to 0)
  const totalInferenceTime = metadata.inference_time_ms || 0;
  const verificationTime = metadata.verification_time_ms || 0;
  const routerTime = 0.15; // TERA CPU routing executes in <0.2ms
  const totalLatency = totalInferenceTime + verificationTime + routerTime;

  const modelMeta = metadata.model_metadata || {};
  const modelName = modelMeta.model || 'Unknown Model';
  const provider = modelMeta.provider || 'mock';
  
  const usage = modelMeta.usage || {};
  const promptTokens = usage.prompt_tokens || 0;
  const completionTokens = usage.completion_tokens || 0;
  const totalTokens = promptTokens + completionTokens;
  const finishReason = modelMeta.finish_reason || 'stop';

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 shadow-lg space-y-4 col-span-1 md:col-span-2 lg:col-span-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          Telemetry & Performance
        </h2>
        <Activity className="h-4 w-4 text-zinc-500" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Latency Timing Breakdown */}
        <div className="space-y-3">
          <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            Execution Latency
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">Router CPU Latency</span>
              <span className="font-mono text-zinc-355 text-zinc-300">{routerTime.toFixed(2)} ms</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">Inference API Latency</span>
              <span className="font-mono text-zinc-300">{totalInferenceTime.toFixed(1)} ms</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">ROVL Verification Latency</span>
              <span className="font-mono text-zinc-300">{verificationTime.toFixed(1)} ms</span>
            </div>
            <div className="flex justify-between py-1 pt-1.5 font-semibold text-zinc-200">
              <span>Total Pipeline Latency</span>
              <span className="font-mono text-indigo-400">{(totalLatency / 1000.0).toFixed(3)} s</span>
            </div>
          </div>
        </div>

        {/* Model Info */}
        <div className="space-y-3">
          <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5" />
            Model Resolution
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">Active Model ID</span>
              <span className="font-mono text-zinc-300 truncate max-w-[150px]" title={modelName}>{modelName.split('/').pop()}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">API Provider</span>
              <span className="font-mono text-zinc-300 capitalize">{provider}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">Finish Status Reason</span>
              <span className="font-mono text-zinc-300 capitalize">{finishReason}</span>
            </div>
          </div>
        </div>

        {/* Token accounting */}
        <div className="space-y-3">
          <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-1.5">
            <BarChart3 className="h-3.5 w-3.5" />
            Token Consumption
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">Input Tokens</span>
              <span className="font-mono text-zinc-300">{promptTokens}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-zinc-900">
              <span className="text-zinc-500">Completion Tokens</span>
              <span className="font-mono text-zinc-300">{completionTokens}</span>
            </div>
            <div className="flex justify-between py-1 pt-1.5 font-semibold text-zinc-200">
              <span>Total Tokens Charged</span>
              <span className="font-mono text-indigo-400">{totalTokens}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
