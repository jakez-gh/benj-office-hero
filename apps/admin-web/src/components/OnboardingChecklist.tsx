import { useCallback, useEffect, useState } from 'react';
import { listCustomers, listVehicles } from '@office-hero/api-client';
import { listJobsApi } from '../api';

const DISMISS_KEY = 'oh_onboarding_dismissed';

interface Progress {
  hasCustomer: boolean;
  hasVehicle: boolean;
  hasJob: boolean;
  hasDispatch: boolean;
}

async function fetchProgress(): Promise<Progress> {
  const [customers, vehicles, jobs] = await Promise.all([
    listCustomers({ search: undefined }).catch(() => ({ items: [] as { id: string }[] })),
    listVehicles().catch(() => [] as { id: string }[]),
    listJobsApi({}).catch(() => ({ items: [] as { status: string }[], total: 0 })),
  ]);
  const items = Array.isArray(jobs) ? jobs : jobs.items;
  return {
    hasCustomer: (Array.isArray(customers) ? customers : customers.items ?? []).length > 0,
    hasVehicle: vehicles.length > 0,
    hasJob: items.length > 0,
    hasDispatch: items.some(j => j.status !== 'pending'),
  };
}

export function OnboardingChecklist() {
  const [dismissed, setDismissed] = useState(() => !!localStorage.getItem(DISMISS_KEY));
  const [progress, setProgress] = useState<Progress | null>(null);

  const refresh = useCallback(async () => {
    try {
      const p = await fetchProgress();
      setProgress(p);
      if (p.hasDispatch) {
        localStorage.setItem(DISMISS_KEY, '1');
        setDismissed(true);
      }
    } catch {
      // silently ignore — this is a non-critical widget
    }
  }, []);

  useEffect(() => {
    if (dismissed) return;
    void refresh();
  }, [dismissed, refresh]);

  if (dismissed || progress === null) return null;
  // Only show when no customers have been added yet (true first-run state)
  if (progress.hasCustomer && progress.hasVehicle && progress.hasJob) return null;

  function dismiss() {
    localStorage.setItem(DISMISS_KEY, '1');
    setDismissed(true);
  }

  const steps: { label: string; done: boolean; href: string }[] = [
    { label: 'Add your first customer', done: progress.hasCustomer, href: '/customers' },
    { label: 'Add a vehicle', done: progress.hasVehicle, href: '/vehicles' },
    { label: 'Create a job', done: progress.hasJob, href: '/jobs' },
    { label: 'Schedule and dispatch the job', done: progress.hasDispatch, href: '/dispatch' },
  ];

  return (
    <div className="mx-4 mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <p className="mb-3 text-sm font-semibold text-blue-900">
            Getting started — complete these steps to dispatch your first job
          </p>
          <ol className="space-y-1.5">
            {steps.map((step, i) => (
              <li key={step.label} className="flex items-center gap-2 text-sm">
                {step.done ? (
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-500 text-xs text-white" aria-label="Complete">
                    ✓
                  </span>
                ) : (
                  <span className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-blue-400 text-xs text-blue-600" aria-label="Incomplete">
                    {i + 1}
                  </span>
                )}
                {step.done ? (
                  <span className="text-neutral-500 line-through">{step.label}</span>
                ) : (
                  <a href={step.href} className="font-medium text-blue-700 hover:underline">
                    {step.label}
                  </a>
                )}
              </li>
            ))}
          </ol>
        </div>
        <button
          onClick={dismiss}
          aria-label="Dismiss getting started guide"
          className="text-blue-400 hover:text-blue-600"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
