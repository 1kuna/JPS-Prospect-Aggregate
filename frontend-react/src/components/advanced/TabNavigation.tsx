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
    <div className="border-b border-gray-200">
      <nav className="-mb-px flex space-x-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onSetActiveTab(tab.id)}
            className={`
              py-2 px-1 border-b-2 font-medium text-sm
              ${activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
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