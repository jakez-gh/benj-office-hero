import React, { useEffect, useId, useRef } from 'react';
import { cn } from '../../lib/cn';

/**
 * Accessible modal shell shared by every dialog in the app.
 *
 * - Escape closes (unless `busy` — don't abandon an in-flight submit)
 * - Backdrop click closes (same guard)
 * - role="dialog" + aria-modal + aria-labelledby wired to the title
 * - Focuses the panel on mount so keyboard/screen-reader users land inside
 */
export function Modal({
  title,
  subtitle,
  onClose,
  busy = false,
  maxWidth = 'max-w-lg',
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  /** While true, Escape/backdrop/✕ are disabled (a submit is in flight). */
  busy?: boolean;
  maxWidth?: string;
  children: React.ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [busy, onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          'max-h-[90vh] w-full overflow-y-auto rounded-lg bg-white p-6 shadow-xl outline-none',
          maxWidth,
        )}
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 id={titleId} className="text-lg font-semibold text-neutral-900">
              {title}
            </h2>
            {subtitle && <p className="mt-0.5 text-sm text-neutral-500">{subtitle}</p>}
          </div>
          <button
            type="button"
            aria-label="Close dialog"
            className="rounded p-1 text-neutral-400 hover:text-neutral-600 disabled:opacity-40"
            onClick={onClose}
            disabled={busy}
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
