import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';

type Phase = 'hidden' | 'loading' | 'complete' | 'fading';

const PHASE_CLASS: Record<Exclude<Phase, 'hidden'>, string> = {
  loading: 'nav-progress-loading',
  complete: 'nav-progress-complete',
  fading: 'nav-progress-fading',
};

export const PageProgressBar: React.FC = () => {
  const location = useLocation();
  const [phase, setPhase] = useState<Phase>('hidden');
  const firstRender = useRef(true);
  const t1 = useRef<ReturnType<typeof setTimeout>>();
  const t2 = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    clearTimeout(t1.current);
    clearTimeout(t2.current);

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPhase('loading');
    t1.current = setTimeout(() => setPhase('complete'), 550);
    t2.current = setTimeout(() => setPhase('fading'), 700);
    return () => {
      clearTimeout(t1.current);
      clearTimeout(t2.current);
    };
  }, [location.pathname]);

  // Keep fading phase mounted long enough for the opacity transition to finish,
  // then hide completely so it doesn't intercept pointer events.
  useEffect(() => {
    if (phase !== 'fading') return;
    const id = setTimeout(() => setPhase('hidden'), 300);
    return () => clearTimeout(id);
  }, [phase]);

  if (phase === 'hidden') return null;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed left-0 top-0 z-50 h-[3px] w-full"
    >
      <div className={`h-full w-full bg-primary-500 ${PHASE_CLASS[phase]}`} />
    </div>
  );
};
