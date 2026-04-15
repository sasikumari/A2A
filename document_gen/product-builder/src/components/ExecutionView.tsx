import { useState } from 'react';
import {
  Code2, Play, CheckCircle, Clock, GitBranch, FilePlus,
  FileEdit, Trash2, Terminal, Zap, AlertCircle, ChevronDown, ChevronUp
} from 'lucide-react';
import type { ExecutionItem } from '../types';

interface ExecutionViewProps {
  items: ExecutionItem[];
  featureName: string;
  onUpdate: (items: ExecutionItem[]) => void;
}

const TYPE_CONFIG = {
  add: { label: 'Add', color: 'bg-emerald-100 text-emerald-700', icon: FilePlus },
  modify: { label: 'Modify', color: 'bg-blue-100 text-blue-700', icon: FileEdit },
  delete: { label: 'Delete', color: 'bg-red-100 text-red-700', icon: Trash2 },
};

const STATUS_CONFIG = {
  pending: { label: 'Pending', color: 'text-gray-500', bg: 'bg-gray-100', icon: Clock },
  'in-progress': { label: 'In Progress', color: 'text-amber-600', bg: 'bg-amber-100', icon: Zap },
  done: { label: 'Done', color: 'text-emerald-600', bg: 'bg-emerald-100', icon: CheckCircle },
};

const IMPLEMENTATION_PHASES = [
  {
    phase: 'Phase 1',
    title: 'Core API Layer',
    duration: '2 weeks',
    files: ['src/api/upi/transaction.ts', 'src/api/upi/execute.ts', 'src/db/schemas/transaction.ts'],
    color: 'border-l-indigo-500',
  },
  {
    phase: 'Phase 2',
    title: 'Security & Middleware',
    duration: '1 week',
    files: ['src/middleware/auth.ts', 'src/services/fraudDetection.ts'],
    color: 'border-l-blue-500',
  },
  {
    phase: 'Phase 3',
    title: 'Frontend Components',
    duration: '2 weeks',
    files: ['src/components/ActiveReserves.tsx', 'src/components/PaymentCreate.tsx'],
    color: 'border-l-indigo-500',
  },
  {
    phase: 'Phase 4',
    title: 'Notifications & Jobs',
    duration: '1 week',
    files: ['src/services/notifications.ts', 'src/jobs/blockExpiry.ts', 'src/jobs/reconciliation.ts'],
    color: 'border-l-cyan-500',
  },
  {
    phase: 'Phase 5',
    title: 'Testing & QA',
    duration: '2 weeks',
    files: ['tests/unit/transaction.test.ts', 'tests/integration/e2e.test.ts'],
    color: 'border-l-emerald-500',
  },
];

function TerminalOutput({ lines }: { lines: string[] }) {
  return (
    <div className="bg-gray-950 rounded-xl p-4 font-mono text-xs space-y-1">
      {lines.map((line, i) => (
        <div key={i} className={`${
          line.startsWith('✓') ? 'text-emerald-400' :
          line.startsWith('►') ? 'text-amber-400' :
          line.startsWith('✗') ? 'text-red-400' :
          line.startsWith('$') ? 'text-gray-300' :
          'text-gray-500'
        }`}>
          {line}
        </div>
      ))}
      <div className="flex items-center gap-2 text-gray-400 pt-1">
        <span>$</span>
        <span className="animate-pulse">_</span>
      </div>
    </div>
  );
}

export default function ExecutionView({ items, featureName, onUpdate }: ExecutionViewProps) {
  const [executing, setExecuting] = useState(false);
  const [showTimeline, setShowTimeline] = useState(true);
  const [showTerminal, setShowTerminal] = useState(false);
  const [terminalLines, setTerminalLines] = useState<string[]>([
    '$ npci-agent --feature "' + featureName + '" --mode execute',
    'NPCI A2A Execution Agent v2.0',
    '► Awaiting start command...',
  ]);

  const doneCount = items.filter(i => i.status === 'done').length;
  const inProgressCount = items.filter(i => i.status === 'in-progress').length;

  const startExecution = () => {
    setExecuting(true);
    setShowTerminal(true);

    const newLines = [
      ...terminalLines,
      '$ Starting execution pipeline...',
      '► Initializing git branch: feature/' + featureName.toLowerCase().replace(/\s+/g, '-'),
      '► Loading execution plan: 12 files...',
    ];
    setTerminalLines(newLines);

    items.forEach((item, idx) => {
      setTimeout(() => {
        setTerminalLines(prev => [
          ...prev,
          `► [${idx + 1}/${items.length}] Processing: ${item.file}`,
        ]);
        onUpdate(items.map(i => i.id === item.id ? { ...i, status: 'in-progress' } : i));

        setTimeout(() => {
          setTerminalLines(prev => [
            ...prev,
            `✓ [${idx + 1}/${items.length}] Completed: ${item.file}`,
          ]);
          onUpdate(items.map(i => i.id === item.id ? { ...i, status: 'done' } : i));

          if (idx === items.length - 1) {
            setTimeout(() => {
              setTerminalLines(prev => [
                ...prev,
                '',
                '✓ All files processed successfully',
                '► Running test suite...',
                '✓ 50/50 tests passing',
                '► Creating pull request...',
                '✓ PR created: feature/' + featureName.toLowerCase().replace(/\s+/g, '-'),
                '✓ Execution pipeline complete!',
              ]);
              setExecuting(false);
            }, 500);
          }
        }, 600);
      }, idx * 800);
    });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 animate-fadeIn">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-2xl p-6 mb-6 text-white shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="text-gray-400 text-xs font-medium uppercase tracking-widest mb-2 flex items-center gap-2">
              <Code2 className="w-4 h-4" />
              Execution Engine
            </div>
            <h2 className="text-xl font-bold">{featureName}</h2>
            <p className="text-gray-400 text-sm mt-1">{items.length} files · 5 implementation phases · ~8 weeks</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-400">{doneCount}</div>
              <div className="text-xs text-gray-400">Done</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-amber-400">{inProgressCount}</div>
              <div className="text-xs text-gray-400">In Progress</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-400">{items.length - doneCount - inProgressCount}</div>
              <div className="text-xs text-gray-400">Pending</div>
            </div>
            <button
              onClick={startExecution}
              disabled={executing}
              className={`flex items-center gap-2 px-5 py-3 rounded-xl font-semibold text-sm transition-all ${
                executing
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg hover:shadow-emerald-500/25'
              }`}
            >
              {executing ? (
                <>
                  <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                  Executing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Start Execution
                </>
              )}
            </button>
          </div>
        </div>
        {(doneCount > 0 || inProgressCount > 0) && (
          <div className="mt-4">
            <div className="bg-gray-700 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-emerald-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                style={{ width: `${(doneCount / items.length) * 100}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Implementation Timeline */}
      <div className="bg-slate-900 rounded-2xl border border-gray-200 mb-4 overflow-hidden">
        <button
          onClick={() => setShowTimeline(t => !t)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <GitBranch className="w-5 h-5 text-indigo-600" />
            <span className="font-semibold text-gray-900">Implementation Timeline</span>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">5 phases · ~8 weeks</span>
          </div>
          {showTimeline ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </button>
        {showTimeline && (
          <div className="px-5 pb-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {IMPLEMENTATION_PHASES.map(phase => (
              <div key={phase.phase} className={`border-l-4 ${phase.color} bg-gray-50 rounded-lg p-3`}>
                <div className="text-xs font-bold text-gray-500 mb-1">{phase.phase}</div>
                <div className="text-sm font-semibold text-gray-900 mb-1">{phase.title}</div>
                <div className="text-xs text-gray-400 mb-2">⏱ {phase.duration}</div>
                <div className="space-y-1">
                  {phase.files.map(f => (
                    <div key={f} className="text-xs text-gray-500 font-mono truncate">{f.split('/').pop()}</div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* File Changes */}
      <div className="bg-slate-900 rounded-2xl border border-gray-200 mb-4 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Code2 className="w-5 h-5 text-gray-600" />
            <span className="font-semibold text-gray-900">File Changes</span>
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{items.length} files</span>
          </div>
          <div className="flex gap-3 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="text-emerald-500">+</span>{items.filter(i => i.type === 'add').length} add</span>
            <span className="flex items-center gap-1"><span className="text-blue-500">~</span>{items.filter(i => i.type === 'modify').length} modify</span>
          </div>
        </div>
        <div className="divide-y divide-gray-50">
          {items.map(item => {
            const typeConf = TYPE_CONFIG[item.type];
            const statusConf = STATUS_CONFIG[item.status];
            const TypeIcon = typeConf.icon;
            const StatusIcon = statusConf.icon;

            return (
              <div key={item.id} className={`flex items-center gap-4 px-5 py-3 hover:bg-gray-50 transition-colors ${item.status === 'in-progress' ? 'bg-amber-50' : item.status === 'done' ? 'bg-emerald-50/30' : ''}`}>
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${typeConf.color}`}>
                  <TypeIcon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-mono text-gray-900 truncate">{item.file}</div>
                  <div className="text-xs text-gray-500 truncate">{item.change}</div>
                </div>
                <div className={`flex items-center gap-1 text-xs font-medium ${statusConf.color} ${statusConf.bg} px-2 py-0.5 rounded-full flex-shrink-0`}>
                  <StatusIcon className="w-3 h-3" />
                  {statusConf.label}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Terminal */}
      <div className="bg-slate-900 rounded-2xl border border-gray-200 overflow-hidden">
        <button
          onClick={() => setShowTerminal(t => !t)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Terminal className="w-5 h-5 text-gray-600" />
            <span className="font-semibold text-gray-900">Execution Terminal</span>
            {executing && (
              <span className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                Running
              </span>
            )}
          </div>
          {showTerminal ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </button>
        {showTerminal && (
          <div className="px-5 pb-5">
            <TerminalOutput lines={terminalLines} />
          </div>
        )}
      </div>

      {/* Footer notes */}
      <div className="mt-4 flex items-start gap-2 text-xs text-gray-400 bg-blue-50 rounded-xl p-3">
        <AlertCircle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <span>
          Execution will create a new git branch, implement all file changes, run the test suite, and open a pull request for review.
          All changes follow NPCI code standards and RBI security requirements.
        </span>
      </div>
    </div>
  );
}
