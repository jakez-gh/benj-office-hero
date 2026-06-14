import React from 'react';
import type { ContractStatus, JobStatus, RouteStatus } from '../api';

/**
 * Shared status-badge components — one per status enum. Each renders the same
 * pill markup; only the colour/label maps differ. Extracted from the
 * near-identical local StatusBadge definitions that lived in JobsPage,
 * ContractsPage and RoutesPage.
 */

const PILL =
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium';
const FALLBACK = 'bg-neutral-100 text-neutral-600';

function Badge({ label, color }: { label: string; color: string }) {
  return <span className={`${PILL} ${color}`}>{label}</span>;
}

const JOB_COLORS: Record<JobStatus, string> = {
  pending:     'bg-amber-100 text-amber-800',
  scheduled:   'bg-blue-100 text-blue-800',
  in_progress: 'bg-indigo-100 text-indigo-800',
  completed:   'bg-green-100 text-green-800',
  cancelled:   'bg-neutral-100 text-neutral-500',
};
const JOB_LABELS: Record<JobStatus, string> = {
  pending:     'Pending',
  scheduled:   'Scheduled',
  in_progress: 'In Progress',
  completed:   'Completed',
  cancelled:   'Cancelled',
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return <Badge label={JOB_LABELS[status] ?? status} color={JOB_COLORS[status] ?? FALLBACK} />;
}

const CONTRACT_COLORS: Record<ContractStatus, string> = {
  active: 'bg-green-100 text-green-800',
  paused: 'bg-amber-100 text-amber-800',
  ended:  'bg-neutral-100 text-neutral-500',
};
const CONTRACT_LABELS: Record<ContractStatus, string> = {
  active: 'Active',
  paused: 'Paused',
  ended:  'Ended',
};

export function ContractStatusBadge({ status }: { status: ContractStatus }) {
  return (
    <Badge label={CONTRACT_LABELS[status] ?? status} color={CONTRACT_COLORS[status] ?? FALLBACK} />
  );
}

const ROUTE_COLORS: Record<RouteStatus, string> = {
  draft:       'bg-neutral-100 text-neutral-600',
  committed:   'bg-blue-100 text-blue-800',
  in_progress: 'bg-indigo-100 text-indigo-800',
  complete:    'bg-green-100 text-green-800',
  cancelled:   'bg-neutral-100 text-neutral-500',
};
const ROUTE_LABELS: Record<RouteStatus, string> = {
  draft:       'Draft',
  committed:   'Committed',
  in_progress: 'In Progress',
  complete:    'Complete',
  cancelled:   'Cancelled',
};

export function RouteStatusBadge({ status }: { status: RouteStatus }) {
  return <Badge label={ROUTE_LABELS[status] ?? status} color={ROUTE_COLORS[status] ?? FALLBACK} />;
}
