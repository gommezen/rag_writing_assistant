import { useState, useEffect } from 'react';
import './Skeleton.css';

interface SkeletonProps {
  variant?: 'text' | 'rectangular' | 'circular';
  width?: string | number;
  height?: string | number;
  className?: string;
}

export function Skeleton({
  variant = 'text',
  width,
  height,
  className = '',
}: SkeletonProps) {
  const style: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div
      className={`skeleton skeleton--${variant} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

export function DocumentListSkeleton() {
  return (
    <div className="document-list-skeleton">
      {[1, 2, 3].map((i) => (
        <div key={i} className="document-card-skeleton">
          <Skeleton variant="circular" width={16} height={16} />
          <div className="document-card-skeleton__content">
            <Skeleton variant="text" width="80%" height={16} />
            <Skeleton variant="text" width="50%" height={12} />
            <Skeleton variant="rectangular" width={60} height={20} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ContentSkeleton() {
  return (
    <div className="content-skeleton">
      <Skeleton variant="text" width="100%" height={20} />
      <Skeleton variant="text" width="95%" height={16} />
      <Skeleton variant="text" width="90%" height={16} />
      <Skeleton variant="text" width="97%" height={16} />
      <Skeleton variant="text" width="85%" height={16} />
      <div className="content-skeleton__gap" />
      <Skeleton variant="text" width="100%" height={16} />
      <Skeleton variant="text" width="92%" height={16} />
      <Skeleton variant="text" width="88%" height={16} />
    </div>
  );
}

const GENERATION_STAGES = [
  'Analyzing your prompt...',
  'Retrieving relevant content...',
  'Generating draft...',
  'Finalizing sections...',
];

const STAGE_INTERVAL_MS = 3000;

export function GenerationProgress() {
  const [elapsed, setElapsed] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, GENERATION_STAGES.length - 1));
    }, STAGE_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="generation-progress">
      <div className="generation-progress__spinner" />
      <p className="generation-progress__stage">{GENERATION_STAGES[stageIndex]}</p>
      <p className="generation-progress__elapsed">{elapsed}s elapsed</p>
    </div>
  );
}
