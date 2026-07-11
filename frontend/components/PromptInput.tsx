import React, { useState } from 'react';
import { Send, Settings2, Sparkles } from 'lucide-react';

interface PromptInputProps {
  onSubmit: (data: any) => void;
  loading: boolean;
  devMode: boolean;
}

export default function PromptInput({ onSubmit, loading, devMode }: PromptInputProps) {
  const [prompt, setPrompt] = useState('');
  const [c2, setC2] = useState(10.0);
  const [c3, setC3] = useState(100.0);
  const [lambdaCoeff, setLambdaCoeff] = useState(0.5);
  const [alphaDense, setAlphaDense] = useState(0.9);
  const [schemaType, setSchemaType] = useState('none');
  const [regexPattern, setRegexPattern] = useState('');
  const [minChars, setMinChars] = useState('');
  const [maxChars, setMaxChars] = useState('');

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!prompt.trim() || loading) return;

    onSubmit({
      prompt,
      c2,
      c3,
      lambda_coeff: lambdaCoeff,
      alpha_dense: alphaDense,
      schema_type: schemaType,
      regex_pattern: regexPattern || null,
      min_chars: minChars ? parseInt(minChars) : null,
      max_chars: maxChars ? parseInt(maxChars) : null,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-5 shadow-2xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
            Input Query Prompt
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your prompt here... (Press Enter to analyze, Shift+Enter for newline)"
            rows={4}
            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 resize-none font-sans"
            disabled={loading}
          />
        </div>

        {/* Advanced Parameter Knobs (visible only in Dev Mode) */}
        {devMode && (
          <div className="border-t border-zinc-800 pt-4 mt-2 space-y-4 animate-fade-in">
            <div className="flex items-center gap-2 text-zinc-300 text-xs font-semibold uppercase tracking-wider">
              <Settings2 className="h-3.5 w-3.5" />
              Advanced Routing & Calibration Settings
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Cheap Cost (c2) */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1">
                  Cheap Cost (c2): <span className="text-zinc-200 font-mono">{c2.toFixed(1)}</span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="50"
                  step="0.5"
                  value={c2}
                  onChange={(e) => setC2(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600"
                />
              </div>

              {/* Dense Cost (c3) */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1">
                  Dense Cost (c3): <span className="text-zinc-200 font-mono">{c3.toFixed(1)}</span>
                </label>
                <input
                  type="range"
                  min="50"
                  max="500"
                  step="5"
                  value={c3}
                  onChange={(e) => setC3(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600"
                />
              </div>

              {/* Frugality Lambda */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1">
                  Frugality Coefficient (λ): <span className="text-zinc-200 font-mono">{lambdaCoeff.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={lambdaCoeff}
                  onChange={(e) => setLambdaCoeff(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600"
                />
              </div>

              {/* Dense Baseline Accuracy */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1">
                  Dense Accuracy (α_dense): <span className="text-zinc-200 font-mono">{alphaDense.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.05"
                  value={alphaDense}
                  onChange={(e) => setAlphaDense(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 border-t border-zinc-900 pt-3">
              {/* Schema Selection */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1.5">ROVL Schema Type</label>
                <select
                  value={schemaType}
                  onChange={(e) => setSchemaType(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="none">None</option>
                  <option value="json">JSON Only</option>
                  <option value="regex">Regex Pattern</option>
                </select>
              </div>

              {/* Regex Input */}
              {schemaType === 'regex' && (
                <div>
                  <label className="block text-xs text-zinc-400 mb-1.5">Regex Match Pattern</label>
                  <input
                    type="text"
                    value={regexPattern}
                    onChange={(e) => setRegexPattern(e.target.value)}
                    placeholder="e.g. ^[0-9]+$"
                    className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 placeholder-zinc-600"
                  />
                </div>
              )}

              {/* Min Chars */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1.5">Min Characters</label>
                <input
                  type="number"
                  value={minChars}
                  onChange={(e) => setMinChars(e.target.value)}
                  placeholder="None"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 placeholder-zinc-600"
                />
              </div>

              {/* Max Chars */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1.5">Max Characters</label>
                <input
                  type="number"
                  value={maxChars}
                  onChange={(e) => setMaxChars(e.target.value)}
                  placeholder="None"
                  className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 placeholder-zinc-600"
                />
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={!prompt.trim() || loading}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold tracking-wide text-white transition-all shadow-md cursor-pointer ${
              !prompt.trim() || loading
                ? 'bg-zinc-800 text-zinc-500 border border-zinc-850 cursor-not-allowed shadow-none'
                : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-500/10 active:scale-[0.98]'
            }`}
          >
            {loading ? (
              <>
                <div className="h-4 w-4 border-2 border-zinc-400 border-t-white rounded-full animate-spin" />
                Analyzing Prompt...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Analyze Prompt
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
