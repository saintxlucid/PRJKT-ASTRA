/**
 * ConsentCard Component
 * Visual consent workflow for destructive operations
 * - Diff preview (create/write/delete/move)
 * - Scope badges
 * - Approve/Reject actions
 * - Animated with Framer Motion
 */

import { motion } from 'framer-motion';
import Button from './ui/Button';

export interface FileDiff {
  path: string;
  change: 'create' | 'write' | 'delete' | 'move';
  oldPath?: string; // For move operations
}

export interface ConsentPlan {
  summary: string;
  diffs: FileDiff[];
  scopes: string[];
}

interface ConsentCardProps {
  plan: ConsentPlan;
  onApprove: () => void;
  onReject: () => void;
  loading?: boolean;
}

const changeColors = {
  create: 'text-status-success',
  write: 'text-accent-amber',
  delete: 'text-status-danger',
  move: 'text-accent-teal',
};

const changeIcons = {
  create: '+',
  write: '~',
  delete: '-',
  move: '→',
};

export function ConsentCard({ plan, onApprove, onReject, loading }: ConsentCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ type: 'spring', mass: 0.9, stiffness: 220, damping: 28 }}
      className="rounded-2xl border border-accent-gold/30 bg-astra-elevated p-6 shadow-soft"
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-accent-gold/20 flex items-center justify-center">
          <span className="text-xl">🔐</span>
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-1">Review & Seal</h3>
          <p className="text-sm text-white/70">{plan.summary}</p>
        </div>
      </div>

      {/* File Diffs */}
      {plan.diffs.length > 0 && (
        <div className="mb-4">
          <div className="text-xs font-medium text-white/60 mb-2 uppercase tracking-wide">
            File Changes ({plan.diffs.length})
          </div>
          <div className="rounded-xl bg-astra-bg/50 border border-white/5 p-3 max-h-48 overflow-y-auto">
            <div className="space-y-1.5 font-mono text-sm">
              {plan.diffs.map((diff, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center gap-3 py-1"
                >
                  <span className={`flex-shrink-0 w-5 font-bold ${changeColors[diff.change]}`}>
                    {changeIcons[diff.change]}
                  </span>
                  <span className={`flex-shrink-0 text-xs uppercase font-semibold ${changeColors[diff.change]}`}>
                    {diff.change}
                  </span>
                  <span className="text-white/80 truncate">
                    {diff.change === 'move' && diff.oldPath ? (
                      <>
                        {diff.oldPath} → {diff.path}
                      </>
                    ) : (
                      diff.path
                    )}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Scopes */}
      {plan.scopes.length > 0 && (
        <div className="mb-5">
          <div className="text-xs font-medium text-white/60 mb-2 uppercase tracking-wide">
            Required Scopes
          </div>
          <div className="flex flex-wrap gap-2">
            {plan.scopes.map((scope, i) => (
              <motion.span
                key={i}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-accent-gold/10 border border-accent-gold/30 text-xs font-medium text-accent-gold"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-accent-gold" />
                {scope}
              </motion.span>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          variant="primary"
          className="flex-1"
          onClick={onApprove}
          loading={loading}
          disabled={loading}
        >
          <span className="mr-1.5">🔒</span>
          Seal & Execute
        </Button>
        <Button
          variant="ghost"
          onClick={onReject}
          disabled={loading}
        >
          Reject
        </Button>
      </div>

      {/* Footer hint */}
      <div className="mt-4 pt-4 border-t border-white/5">
        <p className="text-xs text-white/40 text-center">
          This action will be recorded in the immutable journal
        </p>
      </div>
    </motion.div>
  );
}

export default ConsentCard;
