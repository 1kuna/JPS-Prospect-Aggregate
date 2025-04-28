import { DataPageLayout } from '@/components/layout';

export default function Dashboard() {
  // Placeholder data
  const isLoading = false;

  return (
    <DataPageLayout
      title="Dashboard"
      subtitle="Overview of your data collection system"
      data={null}
      loading={isLoading}
      renderContent={() => (
        <div className="space-y-6">
          <div>Dashboard content temporarily removed due to missing components.</div>
        </div>
      )}
    />
  );
} 