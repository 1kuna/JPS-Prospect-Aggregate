import { CheckIcon, ReloadIcon } from '@radix-ui/react-icons';

interface ProgressStep {
  key: string;
  label: string;
  completed: boolean;
  skipped: boolean;
  active: boolean;
}

interface EnhancementProgressProps {
  status: {
    currentStep?: string;
    progress?: {
      titles?: { completed: boolean; skipped?: boolean };
      values?: { completed: boolean; skipped?: boolean };
      naics?: { completed: boolean; skipped?: boolean };
      set_asides?: { completed: boolean; skipped?: boolean };
    };
  } | null;
  isVisible: boolean;
}

export function EnhancementProgress({ status, isVisible }: EnhancementProgressProps) {
  if (!isVisible || !status) return null;
  
  const steps: ProgressStep[] = [
    {
      key: 'titles',
      label: 'Enhance Title',
      completed: status.progress?.titles?.completed || false,
      skipped: status.progress?.titles?.skipped || false,
      active: status.currentStep?.toLowerCase().includes('enhancing') ||
              status.currentStep?.toLowerCase().includes('title') || false
    },
    {
      key: 'values',
      label: 'Parse Contract Values',
      completed: status.progress?.values?.completed || false,
      skipped: status.progress?.values?.skipped || false,
      active: status.currentStep?.toLowerCase().includes('parsing') || 
              status.currentStep?.toLowerCase().includes('contract') ||
              status.currentStep?.toLowerCase().includes('values') || false
    },
    {
      key: 'naics',
      label: 'Classify NAICS Code',
      completed: status.progress?.naics?.completed || false,
      skipped: status.progress?.naics?.skipped || false,
      active: status.currentStep?.toLowerCase().includes('classifying') ||
              status.currentStep?.toLowerCase().includes('naics') || false
    },
    {
      key: 'set_asides',
      label: 'Process Set Asides',
      completed: status.progress?.set_asides?.completed || false,
      skipped: status.progress?.set_asides?.skipped || false,
      active: status.currentStep?.toLowerCase().includes('processing') ||
              status.currentStep?.toLowerCase().includes('set') ||
              status.currentStep?.toLowerCase().includes('aside') || false
    }
  ];
  
  return (
    <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
      <h4 className="text-sm font-medium text-yellow-800 mb-3">AI Enhancement Progress</h4>
      <div className="space-y-2">
        {steps.map((step) => (
          <div key={step.key} className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              {step.active ? (
                <ReloadIcon className="h-4 w-4 text-blue-600 animate-spin" />
              ) : step.completed ? (
                <CheckIcon className="h-4 w-4 text-green-600" />
              ) : step.skipped ? (
                <div className="h-4 w-4 bg-gray-200 rounded-full flex items-center justify-center">
                  <CheckIcon className="h-3 w-3 text-green-600" />
                </div>
              ) : (
                <div className="h-4 w-4 border border-gray-300 rounded-full"></div>
              )}
            </div>
            <span className={`text-sm ${
              step.active ? 'text-blue-700 font-medium' :
              step.completed ? 'text-green-700' :
              step.skipped ? 'text-gray-600' :
              'text-gray-600'
            }`}>
              {step.label}
              {step.skipped && <span className="ml-1 text-xs text-green-600">(already complete)</span>}
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