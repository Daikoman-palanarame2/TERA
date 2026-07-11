import React from 'react';
import { Terminal, Database, HelpCircle } from 'lucide-react';

interface HeaderProps {
  devMode: boolean;
  setDevMode: (val: boolean) => void;
  isMock: boolean;
}

export default function Header({ devMode, setDevMode, isMock }: HeaderProps) {
  return (
    <header className="border-b border-zinc-800 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-zinc-100">TERA Router Inspector</h1>
            <p className="text-xs text-zinc-400">Interactive Routing Visualization & Diagnostics</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Connection Status Badge */}
          <div className="flex items-center gap-2">
            <div className={`h-2.5 w-2.5 rounded-full ${isMock ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500 animate-pulse'}`} />
            <span className="text-xs font-medium text-zinc-300">
              {isMock ? 'Offline Mock Mode' : 'Live Fireworks Connected'}
            </span>
          </div>

          <div className="h-4 w-px bg-zinc-800" />

          {/* Dev Mode Toggle */}
          <button
            onClick={() => setDevMode(!devMode)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
              devMode 
                ? 'bg-indigo-950/40 border-indigo-700 text-indigo-400' 
                : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Database className="h-3.5 w-3.5" />
            Developer Mode
          </button>
        </div>
      </div>
    </header>
  );
}
