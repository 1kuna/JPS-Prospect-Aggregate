import { useEnhancementQueueStatus } from '../hooks/api/useEnhancementQueue';
import { Loader2, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface EnhancementQueueStatusProps {
  compact?: boolean;
  className?: string;
}

export function EnhancementQueueStatus({ compact = false, className = '' }: EnhancementQueueStatusProps) {
  const { data: queueStatus, isLoading } = useEnhancementQueueStatus(2000);

  if (isLoading || !queueStatus) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
        <span className="text-sm text-gray-500">Loading queue status...</span>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'cancelled':
        return <AlertCircle className="w-4 h-4 text-gray-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Waiting';
      case 'processing':
        return 'Processing';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  };

  const getPriorityBadge = (priority: number) => {
    if (priority <= 1) {
      return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">High</span>;
    } else if (priority <= 5) {
      return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">Medium</span>;
    } else {
      return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">Low</span>;
    }
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        {queueStatus.worker_running ? (
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-sm text-gray-600">Queue Active</span>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
            <span className="text-sm text-gray-500">Queue Stopped</span>
          </div>
        )}
        
        {queueStatus.queue_size > 0 && (
          <span className="text-sm text-gray-600">
            {queueStatus.queue_size} pending
          </span>
        )}
        
        {queueStatus.current_item && (
          <div className="flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin text-blue-500" />
            <span className="text-sm text-blue-600">Processing</span>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Enhancement Queue</h3>
        <div className="flex items-center gap-2">
          {queueStatus.worker_running ? (
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-sm font-medium text-green-600">Active</span>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <span className="text-sm font-medium text-red-600">Stopped</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">{queueStatus.queue_size}</div>
          <div className="text-sm text-gray-500">Pending</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{queueStatus.current_item ? 1 : 0}</div>
          <div className="text-sm text-gray-500">Processing</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{queueStatus.recent_completed.length}</div>
          <div className="text-sm text-gray-500">Recent</div>
        </div>
      </div>

      {queueStatus.pending_items.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900">Pending Items</h4>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {queueStatus.pending_items.map((item, index) => (
              <div key={item.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-600">#{index + 1}</span>
                  {getStatusIcon(item.status)}
                  <span className="text-sm text-gray-900">
                    {item.type === 'individual' ? `Prospect ${item.prospect_id}` : `Bulk (${item.prospect_count} prospects)`}
                  </span>
                  {getPriorityBadge(item.priority)}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">{item.enhancement_type}</span>
                  <span className="text-xs text-gray-400">
                    {new Date(item.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {queueStatus.recent_completed.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="font-medium text-gray-900">Recent Completed</h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {queueStatus.recent_completed.map((item) => (
              <div key={item.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center gap-2">
                  {getStatusIcon(item.status)}
                  <span className="text-sm text-gray-900">
                    {item.type === 'individual' ? `Prospect ${item.prospect_id}` : 'Bulk Enhancement'}
                  </span>
                  <span className="text-xs text-gray-500">{getStatusText(item.status)}</span>
                </div>
                {item.completed_at && (
                  <span className="text-xs text-gray-400">
                    {new Date(item.completed_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {queueStatus.queue_size === 0 && queueStatus.recent_completed.length === 0 && (
        <div className="text-center py-8">
          <Clock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No enhancement requests in queue</p>
        </div>
      )}
    </div>
  );
}