interface TabConfig {
  id: string;
  label: string;
  description: string;
  subTabs?: Array<{
    id: string;
    label: string;
  }>;
}

interface TabNavigationProps {
  tabs: TabConfig[];
  activeTab: string;
  onSetActiveTab: (tab: string, subtab?: string) => void;
}

export function TabNavigation({ tabs, activeTab, onSetActiveTab }: TabNavigationProps) {
  return (
    <div className="border-b border-border">
      <nav className="-mb-px flex space-x-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onSetActiveTab(tab.id)}
            className={`
              py-2 px-1 border-b-2 font-medium text-sm
              ${activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted'
              }
            `}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}