import { useEffect } from 'react';
import { PageLayout } from '@/components/layout';
import { AIEnrichment } from '@/components/AIEnrichment';
import { useConfirmationDialog } from '@/components/ui/ConfirmationDialog';
import { useDataSourceManagement, useScraperOperations, useTabNavigation } from '@/hooks';
import { DataSourcesTab, DatabaseTab, TabNavigation } from '@/components/advanced';

export default function Advanced() {
  const { confirm, ConfirmationDialog } = useConfirmationDialog();
  
  // Use extracted hooks
  const { tabs, activeTab, activeSubTab, currentTab, setActiveTab } = useTabNavigation();
  const { sources, isLoading, error, runAllScrapersMutation, clearDataMutation, handleClearData } = useDataSourceManagement();
  const { runAllInProgress, handleRunScraper, handleRunAllScrapers, updateWorkingScrapers, getScraperButtonState } = useScraperOperations();

  // Update working scrapers when sources data changes
  useEffect(() => {
    if (sources?.data) {
      updateWorkingScrapers(sources.data);
    }
  }, [sources, updateWorkingScrapers]);

  // Handle run all scrapers with confirmation
  const handleRunAllScrapersWithConfirm = async () => {
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
      case 'data-sources':
      default:
        return (
          <DataSourcesTab
            sources={sources}
            isLoading={isLoading}
            error={error}
            runAllInProgress={runAllInProgress}
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