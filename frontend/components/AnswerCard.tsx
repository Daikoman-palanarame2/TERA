import React, { useState } from 'react';
import { Copy, Check, Maximize2, Minimize2, Terminal } from 'lucide-react';

interface AnswerCardProps {
  answer: string;
}

export default function AnswerCard({ answer }: AnswerCardProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text', err);
    }
  };

  // Simple custom markdown block parser to render lists and code blocks beautifully
  const renderFormattedAnswer = (text: string) => {
    if (!text) return null;

    const parts = text.split(/(```[a-z]*\n[\s\S]*?\n```)/g);

    return parts.map((part, index) => {
      // Check if this part is a code block
      if (part.startsWith('```')) {
        const lines = part.split('\n');
        const firstLine = lines[0];
        const lang = firstLine.replace('```', '') || 'text';
        const codeText = lines.slice(1, -1).join('\n');

        return (
          <div key={index} className="my-4 border border-zinc-800 rounded-lg overflow-hidden bg-zinc-950 font-mono shadow-inner">
            <div className="flex items-center justify-between px-4 py-2 bg-zinc-900/60 border-b border-zinc-800 text-[10px] text-zinc-400 font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5" />
                {lang}
              </span>
              <span>Code Block</span>
            </div>
            <pre className="p-4 overflow-x-auto text-xs text-indigo-300 whitespace-pre">
              <code>{codeText}</code>
            </pre>
          </div>
        );
      }

      // Standard text with inline markdown styles (e.g. bold, bullet lists)
      const lines = part.split('\n');
      return (
        <div key={index} className="space-y-2 text-sm text-zinc-300 leading-relaxed font-sans">
          {lines.map((line, lIndex) => {
            if (line.trim().startsWith('-') || line.trim().startsWith('*')) {
              // Bullet lists
              return (
                <ul key={lIndex} className="list-disc pl-5 my-1.5 space-y-1">
                  <li>{line.replace(/^[-*]\s*/, '')}</li>
                </ul>
              );
            }
            if (line.trim().match(/^\d+\.\s/)) {
              // Numbered lists
              return (
                <ol key={lIndex} className="list-decimal pl-5 my-1.5 space-y-1">
                  <li>{line.replace(/^\d+\.\s*/, '')}</li>
                </ol>
              );
            }
            // Standard paragraph line
            return line.trim() === '' ? (
              <div key={lIndex} className="h-2" />
            ) : (
              <p key={lIndex}>{line}</p>
            );
          })}
        </div>
      );
    });
  };

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 shadow-lg space-y-4 col-span-1 md:col-span-2 lg:col-span-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          Final Response Output
        </h2>
        
        <div className="flex items-center gap-2">
          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="p-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
            title="Copy response"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          </button>

          {/* Expand/Collapse Toggle */}
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
            title={expanded ? "Collapse panel" : "Expand panel"}
          >
            {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Answer Body Panel */}
      <div className={`w-full bg-zinc-900/40 border border-zinc-900 rounded-lg p-4 transition-all duration-300 overflow-y-auto ${
        expanded ? 'max-h-[800px]' : 'max-h-[350px]'
      }`}>
        {renderFormattedAnswer(answer)}
      </div>
    </div>
  );
}
