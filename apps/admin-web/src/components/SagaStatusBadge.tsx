/**
 * SagaStatusBadge — displays saga status as a colored badge.
 *
 * Status colors:
 *   - running: blue
 *   - done: green
 *   - compensating: orange
 *   - failed: red
 *   - pending: gray
 */

import React from 'react';

type SagaStatusValue = 'running' | 'done' | 'compensating' | 'failed' | string;

interface SagaStatusBadgeProps {
  status: SagaStatusValue;
}

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  running: { backgroundColor: '#3b82f6', color: '#fff' },
  done: { backgroundColor: '#22c55e', color: '#fff' },
  compensating: { backgroundColor: '#f97316', color: '#fff' },
  failed: { backgroundColor: '#ef4444', color: '#fff' },
  pending: { backgroundColor: '#6b7280', color: '#fff' },
};

export function SagaStatusBadge({ status }: SagaStatusBadgeProps) {
  const style: React.CSSProperties = {
    display: 'inline-block',
    padding: '2px 10px',
    borderRadius: '12px',
    fontSize: '0.8rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    ...(STATUS_STYLES[status] || STATUS_STYLES.pending),
  };

  return <span style={style} data-testid="saga-status-badge">{status}</span>;
}
