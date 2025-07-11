import { useEffect } from 'react';
import { PageLayout } from '@/components/layout';
import { AIEnrichment } from '@/components/AIEnrichment';
import { useConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { useDataSourceManagement, useScraperOperations, useTabNavigation } from '@/hooks';
import { DataSourcesTab, DatabaseTab, TabNavigation, ToolsTab } from '@/components/advanced';
import { useIsAdmin } from '@/hooks/api';

export default function Advanced() {
  const isAdmin = useIsAdmin();
  const { confirm, ConfirmationDialog } = useConfirmationDialog();
  
  // Use extracted hooks
  const { tabs, activeTab, activeSubTab, currentTab, setActiveTab } = useTabNavigation();
  const { sources, isLoading, error, runAllScrapersMutation, clearDataMutation, handleClearData } = useDataSourceManagement();
  const { runAllInProgress, handleRunScraper, handleRunAllScrapers, updateWorkingScrapers, getScraperButtonState } = useScraperOperations();

  // Redirect if not admin
  if (!isAdmin) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600">You need admin privileges to access this page.</p>
        </div>
      </div>
    );
  }

  // Update working scrapers when sources data changes
  useEffect(() => {
    if (sources?.data) {
      updateWorkingScrapers(sources.data);
    }
  }, [sources, updateWorkingScrapers]);

  // Handle run all scrapers with confirmation
  const handleRunAllScrapersWithConfirm = async () => {
    // Prevent multiple simultaneous requests
    if (runAllInProgress || runAllScrapersMutation.isPending) {
      return;
    }
    
    const confirmed = await confirm({
      title: 'Run All Scrapers',
      description: 'This will run all scrapers synchronously. This may take several minutes.',
      confirmLabel: 'Run All Scrapers',
      variant: 'default'
    });
    
    if (confirmed) {
      handleRunAllScrapers(runAllScrapersMutation);
    }
  };

  // Handle clear data with confirmation
  const handleClearDataWithConfirm = async (id: number, sourceName: string) => {
    const confirmed = await confirm({
      title: 'Clear Data Source',
      description: `Clear all scraped data from ${sourceName}?`,
      details: [
        'This will delete all prospects from this source',
        'The data source configuration will remain',
        'This action cannot be undone'
      ],
      confirmLabel: 'Clear Data',
      variant: 'destructive'
    });
    
    if (confirmed) {
      await handleClearData(id, sourceName);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'database': {
        const currentTabConfig = tabs.find(tab => tab.id === 'database');
        const subTabs = currentTabConfig?.subTabs || [];
        return (
          <DatabaseTab
            activeSubTab={activeSubTab}
            onSetActiveTab={setActiveTab}
            subTabs={subTabs}
          />
        );
      }
      case 'ai-enrichment':
        return <AIEnrichment />;
      case 'tools':
        return <ToolsTab />;
      case 'data-sources':
      default:
        return (
          <DataSourcesTab
            sources={sources}
            isLoading={isLoading}
            error={error}
            runAllInProgress={runAllInProgress || runAllScrapersMutation.isPending}
            onRunAllScrapers={handleRunAllScrapersWithConfirm}
            onRunScraper={handleRunScraper}
            onClearData={handleClearDataWithConfirm}
            getScraperButtonState={getScraperButtonState}
            clearDataMutation={clearDataMutation}
          />
        );
    }
  };

  return (
    <PageLayout title="Advanced" subtitle={currentTab.description}>
      <div className="space-y-6">
        {/* Tab Navigation */}
        <TabNavigation
          tabs={tabs}
          activeTab={activeTab}
          onSetActiveTab={setActiveTab}
        />

        {/* Tab Content */}
        {renderTabContent()}
      </div>
      
      {ConfirmationDialog}
    </PageLayout>
  );
}