interface EnhancementStatusBadgeProps {
  hasAnyActivity: boolean;
}

export function EnhancementStatusBadge({ hasAnyActivity }: EnhancementStatusBadgeProps) {
  return (
    <div className="flex items-center space-x-2">
      <div className={`w-2 h-2 rounded-full ${hasAnyActivity ? 'bg-success dark:bg-success dark:ring-1 dark:ring-success/30' : 'bg-neutral dark:bg-neutral'} ${hasAnyActivity ? 'animate-pulse' : ''}`}></div>
      <span className="text-xs text-muted-foreground">
        {hasAnyActivity ? 'Live updates' : 'Idle'}
      </span>
    </div>
  );
}