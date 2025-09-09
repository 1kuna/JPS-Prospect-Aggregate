import { DatabaseManagement } from '@/components/DatabaseManagement';
import { DuplicateReview } from '@/components/DuplicateReview';

interface DatabaseTabProps {
  activeSubTab: string;
  onSetActiveTab: (tab: string, subtab?: string) => void;
  subTabs: Array<{
    id: string;
    label: string;
  }>;
}

export function DatabaseTab({ activeSubTab, onSetActiveTab, subTabs }: DatabaseTabProps) {
  return (
    <div className="space-y-6">
      {/* SubTab Navigation */}
      {subTabs.length > 0 && (
        <div className="border-b border-border">
          <nav className="-mb-px flex space-x-8">
            {subTabs.map((subTab) => (
              <button
                key={subTab.id}
                onClick={() => onSetActiveTab('database', subTab.id)}
                className={`
                  py-2 px-1 border-b-2 font-medium text-sm
                  ${activeSubTab === subTab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted'
                  }
                `}
              >
                {subTab.label}
              </button>
            ))}
          </nav>
        </div>
      )}

      {/* SubTab Content */}
      {activeSubTab === 'duplicates' ? <DuplicateReview /> : <DatabaseManagement />}
    </div>
  );
}