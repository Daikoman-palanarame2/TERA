'use client';

import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import PromptInput from '../components/PromptInput';
import FeatureCard from '../components/FeatureCard';
import RouterDecisionCard from '../components/RouterDecisionCard';
import VerificationCard from '../components/VerificationCard';
import TelemetryCard from '../components/TelemetryCard';
import AnswerCard from '../components/AnswerCard';
import { Sparkles, Terminal, Activity, HelpCircle } from 'lucide-react';

export default function Home() {
  const [devMode, setDevMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [isMock, setIsMock] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check backend health on start to determine connection state
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiBase}/api/health`, { method: 'GET' });
        if (res.ok) {
          // If Fireworks key is in environment, backend will run in live mode
          // We check the telemetry model on actual runs, default connection is active
        }
      } catch (err) {
        console.warn('Backend server not reachable at default port 8000.');
      }
    };
    checkConnection();
  }, []);

  const handleAnalyze = async (payload: any) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiBase}/api/router-inspector`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status code ${res.status}`);
      }

      const data = await res.json();
      setResult(data);

      // Inferred connection mode from response metadata
      const provider = data?.metadata?.model_metadata?.provider || 'mock';
      setIsMock(provider === 'mock');
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'An unexpected communication error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#09090b]">
      <Header devMode={devMode} setDevMode={setDevMode} isMock={isMock} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col lg:flex-row gap-8">
        
        {/* Left Column - Input Panel */}
        <div className="w-full lg:w-5/12 space-y-6">
          <PromptInput onSubmit={handleAnalyze} loading={loading} devMode={devMode} />
          
          {error && (
            <div className="bg-rose-950/20 border border-rose-900/50 p-4 rounded-xl text-rose-400 text-xs flex gap-2">
              <span className="font-bold">Error:</span> {error}
            </div>
          )}
        </div>

        {/* Right Column - Results Display */}
        <div className="flex-1 space-y-6">
          {loading ? (
            /* Skeleton Loading States */
            <div className="space-y-6 animate-pulse">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-zinc-950/40 border border-zinc-900 h-64 rounded-xl" />
                <div className="bg-zinc-950/40 border border-zinc-900 h-64 rounded-xl" />
              </div>
              <div className="bg-zinc-950/40 border border-zinc-900 h-44 rounded-xl" />
              <div className="bg-zinc-950/40 border border-zinc-900 h-80 rounded-xl" />
            </div>
          ) : result ? (
            /* Results Presentation */
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FeatureCard features={result.features} devMode={devMode} />
                <RouterDecisionCard 
                  router={result.router} 
                  utilities={result.utilities} 
                  devMode={devMode} 
                />
              </div>

              <VerificationCard 
                verification={result.verification} 
                metadata={result.metadata}
                devMode={devMode} 
              />

              <TelemetryCard metadata={result.metadata} />
              
              <AnswerCard answer={result.answer} />
            </div>
          ) : (
            /* Initial Empty State Placeholder */
            <div className="bg-zinc-950/20 border border-zinc-900 rounded-xl p-12 text-center space-y-6 flex flex-col items-center justify-center min-h-[450px]">
              <div className="h-14 w-14 rounded-full bg-zinc-900/60 border border-zinc-800 flex items-center justify-center text-zinc-500">
                <Sparkles className="h-6 w-6" />
              </div>
              <div className="max-w-md space-y-2">
                <h3 className="text-sm font-semibold text-zinc-300">Ready for Routing Optimization</h3>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  Enter a prompt query in the input panel to watch the Token-Efficient Routing Agent evaluate lexical complexity, calculate expected utilities, and dynamically select optimal lanes.
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4 max-w-lg w-full pt-4 text-left">
                <div className="bg-zinc-950 border border-zinc-900 p-3.5 rounded-lg space-y-1.5">
                  <Terminal className="h-4 w-4 text-indigo-500" />
                  <div className="text-[10px] font-bold text-zinc-300 uppercase tracking-wider">1. Feature Extract</div>
                  <div className="text-[10px] text-zinc-500">Extracts 4D features (Length, Symbols, Regex, BM25 similarity).</div>
                </div>
                <div className="bg-zinc-950 border border-zinc-900 p-3.5 rounded-lg space-y-1.5">
                  <Activity className="h-4 w-4 text-indigo-500" />
                  <div className="text-[10px] font-bold text-zinc-300 uppercase tracking-wider">2. Utility Opt</div>
                  <div className="text-[10px] text-zinc-500">Computes expected Lagrangian utilities for cheap, dense, and cascade lanes.</div>
                </div>
                <div className="bg-zinc-950 border border-zinc-900 p-3.5 rounded-lg space-y-1.5">
                  <HelpCircle className="h-4 w-4 text-indigo-500" />
                  <div className="text-[10px] font-bold text-zinc-300 uppercase tracking-wider">3. ROVL Cascade</div>
                  <div className="text-[10px] text-zinc-500">Verifies output formats (JSON/regex, length, stop tokens, sequence entropy).</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
