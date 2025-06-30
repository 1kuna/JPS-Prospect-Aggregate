import { Button } from '@/components/ui/button';
import { ReloadIcon, Cross1Icon } from '@radix-ui/react-icons';
import { useProspectEnhancement } from '@/contexts/ProspectEnhancementContext';
import { useEnhancementErrorHandler } from './EnhancementErrorBoundary';

interface EnhancementButtonProps {
  prospect: {
    id: string;
  };
  userId?: number;
  forceRedo?: boolean;
  onEnhancementStart?: () => void;
}

export function EnhancementButton({ 
  prospect, 
  userId = 1, 
  forceRedo = false,
  onEnhancementStart 
}: EnhancementButtonProps) {
  const { addToQueue, getProspectStatus, cancelEnhancement } = useProspectEnhancement();
  const { handleError } = useEnhancementErrorHandler();
  
  const status = getProspectStatus(prospect.id);
  
  const handleEnhanceClick = async () => {
    try {
      onEnhancementStart?.();
      await addToQueue({
        prospect_id: prospect.id,
        user_id: userId,
        force_redo: forceRedo
      });
    } catch (error) {
      handleError(error as Error, 'Enhancement Queue');
    }
  };
  
  const handleCancelClick = async () => {
    try {
      const success = await cancelEnhancement(prospect.id);
      if (!success) {
        throw new Error('Failed to cancel enhancement');
      }
    } catch (error) {
      handleError(error as Error, 'Enhancement Cancellation');
    }
  };
  
  const isQueued = status?.status === 'queued';
  const isProcessing = status?.status === 'processing';
  const isDisabled = isQueued || isProcessing;
  
  const getButtonContent = () => {
    if (isProcessing) {
      return (
        <>
          <ReloadIcon className="mr-2 h-4 w-4 animate-spin" />
          {status?.currentStep || 'Enhancing...'}
        </>
      );
    }
    
    if (isQueued) {
      return (
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center">
            <ReloadIcon className="mr-2 h-4 w-4 animate-spin" />
            <span>
              Queued (#{status?.queuePosition})
              {status?.estimatedTimeRemaining && (
                <span className="text-xs ml-1">
                  ~{Math.ceil(status.estimatedTimeRemaining / 60)}m
                </span>
              )}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 ml-2 hover:bg-red-100"
            onClick={(e) => {
              e.stopPropagation();
              handleCancelClick();
            }}
          >
            <Cross1Icon className="h-3 w-3 text-red-600" />
          </Button>
        </div>
      );
    }
    
    return 'Enhance with AI';
  };
  
  return (
    <Button
      onClick={handleEnhanceClick}
      disabled={isDisabled && !isQueued} // Allow clicks on queued items for cancel
      className={`
        ${isQueued ? 'bg-orange-600 hover:bg-orange-700' : 'bg-blue-600 hover:bg-blue-700'} 
        text-white disabled:bg-gray-400 min-w-[140px]
      `}
    >
      {getButtonContent()}
    </Button>
  );
}