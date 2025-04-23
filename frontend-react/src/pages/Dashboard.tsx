import { DataPageLayout } from '@/components/layout';
import { useDashboard } from '@/hooks/api/useAnalytics';
import { useProposals, useRecentProposals } from '@/hooks/api/useProposals';
import { useDataSources } from '@/hooks/api/useDataSources';
// Commenting out missing dashboard components
// import { DashboardStats } from '@/components/dashboard/DashboardStats'; 
// import { RecentProposals } from '@/components/dashboard/RecentProposals';
// import { DataSourceHealth } from '@/components/dashboard/DataSourceHealth';

export default function Dashboard() {
  const {
    data: dashboardData,
    isLoading,
    isError,
    error
  } = useDashboard();

  const dashboard = dashboardData?.data;
  const statistics = null;

  // const { data: recentProposals } = useRecentProposals(5); // Commented out - endpoint /api/proposals/recent doesn't exist
  const { data: dataSources } = useDataSources.useList();

  return (
    <DataPageLayout
      title="Dashboard"
      subtitle="Overview of your data collection system"
      data={dashboard}
      loading={isLoading}
      error={error}
      renderContent={() => (
        <div className="space-y-6">
          {/* Statistics Overview - Commented out as DashboardStats is missing */}
          {/* <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"> */}
          {/*   <div className="card-container"> */}
          {/*     <DashboardStats */}
          {/*       title="Total Proposals" */}
          {/*       value={statistics?.totalProposals} */}
          {/*       description="Total proposals collected" */}
          {/*     /> */}
          {/*   </div> */}
          {/*   <div className="card-container"> */}
          {/*     <DashboardStats */}
          {/*       title="Active Sources" */}
          {/*       value={statistics?.activeDataSources} */}
          {/*       description="Currently active data sources" */}
          {/*     /> */}
          {/*   </div> */}
          {/*   <div className="card-container"> */}
          {/*     <DashboardStats */}
          {/*       title="Success Rate" */}
          {/*       value={`${statistics?.successRate}%`} */}
          {/*       description="Successful data collection rate" */}
          {/*     /> */}
          {/*   </div> */}
          {/* </div> */}

          {/* Recent Activity and Health - Commented out as components are missing */}
          {/* <div className="grid gap-4 md:grid-cols-2"> */}
          {/*   <div className="card-container"> */}
          {/*     <RecentProposals */}
          {/*       proposals={recentProposals?.data || []} */}
          {/*       isLoading={!recentProposals} */}
          {/*     /> */}
          {/*   </div> */}
          {/*   <div className="card-container"> */}
          {/*     <DataSourceHealth */}
          {/*       dataSources={dataSources?.data || []} */}
          {/*       isLoading={!dataSources} */}
          {/*     /> */}
          {/*   </div> */}
          {/* </div> */}
          <div>Dashboard content temporarily removed due to missing components.</div>
        </div>
      )}
    />
  );
} 