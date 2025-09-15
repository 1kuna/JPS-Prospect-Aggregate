import { CheckIcon, ReloadIcon, Cross2Icon, ExclamationTriangleIcon } from '@radix-ui/react-icons';

interface ProgressStep {
  key: string;
  label: string;
  completed: boolean;
  skipped: boolean;
  active: boolean;
  skipReason?: string;
}

interface EnhancementProgressProps {
  status: {
    overallStatus?: 'idle' | 'queued' | 'processing' | 'completed' | 'failed';
    currentStep?: string;
    progress?: {
      titles?: { completed: boolean; skipped?: boolean; skipReason?: string };
      values?: { completed: boolean; skipped?: boolean; skipReason?: string };
      naics?: { completed: boolean; skipped?: boolean; skipReason?: string };
      set_asides?: { completed: boolean; skipped?: boolean; skipReason?: string };
    };
    enhancementTypes?: string[];
    plannedSteps?: Record<string, { will_process: boolean; reason?: string | null }>;
    error?: string | null;
  } | null;
  isVisible: boolean;
}

export function EnhancementProgress({ status, isVisible }: EnhancementProgressProps) {
  if (!isVisible || !status) {
    return null;
  }
  
  const overallStatus = status.overallStatus;
  const isFailed = overallStatus === 'failed';
  const failureMessage = status.error || 'The AI enhancement failed. Please try again.';

  const allSteps: ProgressStep[] = [
    {
      key: 'titles',
      label: 'Enhance Title',
      completed: status.progress?.titles?.completed || false,
      // Check plannedSteps first for pre-processing skip indication
      skipped: status.plannedSteps?.titles && !status.plannedSteps.titles.will_process 
        ? true 
        : (status.progress?.titles?.skipped || false),
      active: status.currentStep?.toLowerCase() === 'enhancing title...' || false,
      skipReason: status.plannedSteps?.titles?.reason 
        ? status.plannedSteps.titles.reason 
        : status.progress?.titles?.skipReason
    },
    {
      key: 'values',
      label: 'Parse Contract Values',
      completed: status.progress?.values?.completed || false,
      // Check plannedSteps first for pre-processing skip indication
      skipped: status.plannedSteps?.values && !status.plannedSteps.values.will_process 
        ? true 
        : (status.progress?.values?.skipped || false),
      active: status.currentStep?.toLowerCase() === 'parsing contract values...' || false,
      skipReason: status.plannedSteps?.values?.reason 
        ? status.plannedSteps.values.reason 
        : status.progress?.values?.skipReason
    },
    {
      key: 'naics',
      label: 'Classify NAICS Code',
      completed: status.progress?.naics?.completed || false,
      // Check plannedSteps first for pre-processing skip indication
      skipped: status.plannedSteps?.naics && !status.plannedSteps.naics.will_process 
        ? true 
        : (status.progress?.naics?.skipped || false),
      active: status.currentStep?.toLowerCase() === 'classifying naics code...' || false,
      skipReason: status.plannedSteps?.naics?.reason 
        ? status.plannedSteps.naics.reason 
        : status.progress?.naics?.skipReason
    },
    {
      key: 'set_asides',
      label: 'Process Set Asides',
      completed: status.progress?.set_asides?.completed || false,
      // Check plannedSteps first for pre-processing skip indication
      skipped: status.plannedSteps?.set_asides && !status.plannedSteps.set_asides.will_process 
        ? true 
        : (status.progress?.set_asides?.skipped || false),
      active: status.currentStep?.toLowerCase() === 'processing set asides...' || false,
      skipReason: status.plannedSteps?.set_asides?.reason 
        ? status.plannedSteps.set_asides.reason 
        : status.progress?.set_asides?.skipReason
    }
  ];
  
  // Filter steps based on enhancement types if provided
  const steps = status.enhancementTypes && status.enhancementTypes.length > 0
    ? allSteps.filter(step => status.enhancementTypes?.includes(step.key))
    : allSteps;
  
  return (
    <div className="bg-yellow-50 dark:bg-amber-400/10 border border-yellow-200 dark:border-amber-400/20 p-4 rounded-lg">
      <h4 className="text-sm font-medium text-yellow-800 dark:text-amber-300 mb-3">AI Enhancement Progress</h4>
      {isFailed && (
        <div className="mb-3 flex items-start rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <ExclamationTriangleIcon className="mr-2 mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{failureMessage}</span>
        </div>
      )}
      
      <div className="space-y-2">
        {steps.map((step) => (
          <div key={step.key} className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              {step.active ? (
                <ReloadIcon className="h-4 w-4 text-blue-600 animate-spin" />
              ) : step.completed && !step.skipped ? (
                <CheckIcon className="h-4 w-4 text-green-600" />
              ) : step.skipped && step.completed ? (
                // Already skipped (processed but skipped)
                <div className="h-4 w-4 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center" title={step.skipReason}>
                  <Cross2Icon className="h-3 w-3 text-gray-500 dark:text-gray-400" />
                </div>
              ) : step.skipped ? (
                // Will be skipped (pre-determined skip)
                <div className="h-4 w-4 bg-yellow-100 dark:bg-amber-400/20 dark:ring-1 dark:ring-amber-400/30 rounded-full flex items-center justify-center" title={step.skipReason}>
                  <Cross2Icon className="h-3 w-3 text-yellow-700 dark:text-amber-300" />
                </div>
              ) : (
                <div className="h-4 w-4 border border-gray-300 dark:border-gray-600 rounded-full"></div>
              )}
            </div>
            <span className={`text-sm ${
              step.active ? 'text-blue-700 font-medium' :
              step.completed && !step.skipped ? 'text-green-700' :
              step.skipped ? 'text-yellow-700' :
              'text-muted-foreground'
            }`}>
              {step.label}
              {step.skipped && !step.completed && (
                <span className="ml-1 text-xs text-yellow-600">
                  (will skip - {
                    step.skipReason === 'already_enhanced' ? 'already enhanced' :
                    step.skipReason === 'already_parsed' ? 'already parsed' :
                    step.skipReason === 'already_classified' ? 'already classified' :
                    step.skipReason === 'already_standardized' ? 'already standardized' :
                    'has existing data'
                  })
                </span>
              )}
              {step.skipped && step.completed && (
                <span className="ml-1 text-xs text-muted-foreground">
                  (skipped - {
                    step.skipReason === 'already_enhanced' ? 'already enhanced' :
                    step.skipReason === 'already_parsed' ? 'already parsed' :
                    step.skipReason === 'already_classified' ? 'already classified' :
                    step.skipReason === 'already_standardized' ? 'already standardized' :
                    'has existing data'
                  })
                </span>
              )}
              {step.active && status.currentStep && (
                <span className="ml-1 text-xs">- {status.currentStep}</span>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
