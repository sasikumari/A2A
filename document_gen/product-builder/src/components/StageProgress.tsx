import {
  CheckCircle, MessageSquare, FileText, Smartphone,
  ClipboardList, Cpu, FlaskConical, Rocket, ShieldCheck,
  Zap, Briefcase, FileCheck
} from 'lucide-react';
import type { Stage } from '../types';

interface StageProgressProps {
  currentStage: Stage;
  onStageClick: (stage: Stage) => void;
  completedStages: Set<Stage>;
}

const STAGES: { id: Stage; label: string; icon: React.ReactNode }[] = [
  { id: 'clarify',        label: 'Clarify',    icon: <MessageSquare className="w-3.5 h-3.5" /> },
  { id: 'canvas',         label: 'Canvas',     icon: <FileText      className="w-3.5 h-3.5" /> },
  { id: 'product-kit',    label: 'Kit',        icon: <Briefcase     className="w-3.5 h-3.5" /> },
  { id: 'brd',            label: 'BRD',        icon: <FileCheck     className="w-3.5 h-3.5" /> },
  { id: 'technical-plan', label: 'Tech Plan',  icon: <ClipboardList className="w-3.5 h-3.5" /> },
  { id: 'a2a-sync',       label: 'A2A Sync',   icon: <Zap           className="w-3.5 h-3.5" /> },
  { id: 'execution',      label: 'Execute',    icon: <Cpu           className="w-3.5 h-3.5" /> },
  { id: 'verify',         label: 'Verify',     icon: <FlaskConical  className="w-3.5 h-3.5" /> },
  { id: 'certification',  label: 'Certify',    icon: <ShieldCheck   className="w-3.5 h-3.5" /> },
  { id: 'deploy',         label: 'Deploy',     icon: <Rocket        className="w-3.5 h-3.5" /> },
];

// Color tokens (solid, no opacity classes so they always render correctly)
const COLORS = {
  bar:           '#0f172a',   // slate-900 solid
  border:        '#1e293b',   // slate-800
  active:        '#4f46e5',   // indigo-600 fill for active stage
  activeText:    '#ffffff',
  activeBorder:  '#818cf8',   // indigo-400 accent bottom line
  done:          '#14532d',   // emerald-900 tint
  doneText:      '#6ee7b7',   // emerald-300 — readable on #1e293b
  accessible:    'transparent',
  accessibleText:'#cbd5e1',   // slate-300 — clearly readable on slate-800 bg
  locked:        'transparent',
  lockedText:    '#64748b',   // slate-500 — dimmed but visible
  divider:       '#334155',   // slate-700 — visible on slate-800
  dividerDone:   '#166534',
  dividerPast:   '#3730a3',
};

export default function StageProgress({ currentStage, onStageClick, completedStages }: StageProgressProps) {
  if (currentStage === 'input') return null;

  const currentIdx = STAGES.findIndex(s => s.id === currentStage);

  return (
    /* Solid stage bar — lighter than header so it's visually distinct */
    <div
      style={{ background: '#1e293b', borderBottom: '1px solid #334155', borderTop: '1px solid #0f172a', flexShrink: 0 }}
      className="shadow-inner"
    >

      <div className="flex items-stretch" style={{ height: 40 }}>
        {STAGES.map((stage, idx) => {
          const isActive     = stage.id === currentStage;
          const isCompleted  = completedStages.has(stage.id);
          // Always accessible: first stage, active stage, any completed stage, or any stage before current
          const isAccessible = idx === 0 || isActive || isCompleted || idx <= currentIdx;

          const bgColor    = isActive ? COLORS.active : isCompleted ? COLORS.done : COLORS.accessible;
          const textColor  = isActive ? COLORS.activeText : isCompleted ? COLORS.doneText : isAccessible ? COLORS.accessibleText : COLORS.lockedText;
          const bottomBdr  = isActive ? `2px solid ${COLORS.activeBorder}` : '2px solid transparent';

          return (
            <div key={stage.id} style={{ display: 'flex', alignItems: 'stretch', flex: '1 1 0', minWidth: 0 }}>
              <button
                onClick={() => isAccessible && onStageClick(stage.id)}
                disabled={!isAccessible}
                style={{
                  flex: 1,
                  background: bgColor,
                  color: textColor,
                  borderBottom: bottomBdr,
                  borderTop: 'none',
                  borderLeft: 'none',
                  borderRight: 'none',
                  cursor: isAccessible ? 'pointer' : 'not-allowed',
                  fontSize: 10,
                  fontWeight: 900,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 5,
                  padding: '0 4px',
                  transition: 'background 0.15s, color 0.15s',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                }}
                onMouseEnter={e => {
                  if (!isActive && isAccessible) {
                    (e.currentTarget as HTMLButtonElement).style.background = '#1e293b';
                    (e.currentTarget as HTMLButtonElement).style.color = '#e2e8f0';
                  }
                }}
                onMouseLeave={e => {
                  if (!isActive && isAccessible) {
                    (e.currentTarget as HTMLButtonElement).style.background = bgColor;
                    (e.currentTarget as HTMLButtonElement).style.color = textColor;
                  }
                }}
              >
                {/* Icon */}
                <span style={{ flexShrink: 0, display: 'flex', alignItems: 'center', opacity: isAccessible ? 1 : 0.5 }}>
                  {isCompleted && !isActive
                    ? <CheckCircle style={{ width: 13, height: 13, color: COLORS.doneText }} />
                    : stage.icon
                  }
                </span>

                {/* Label - always show on large screens */}
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }} className="hidden lg:block">
                  {stage.label}
                </span>
              </button>

              {/* Thin divider between stages */}
              {idx < STAGES.length - 1 && (
                <div style={{
                  width: 1,
                  flexShrink: 0,
                  background: isCompleted ? COLORS.dividerDone : currentIdx > idx ? COLORS.dividerPast : COLORS.divider,
                }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
