import { useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDate } from '@/lib/utils';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';

// Create stable selectors outside the component
const selectDashboardData = (state: any) => state.dashboardData;
const selectDashboardLoading = (state: any) => state.loading.dashboard;
const selectDashboardErrors = (state: any) => state.errors.dashboard;
const selectFetchDashboardData = (state: any) => state.fetchDashboardData;
const selectLastUpdated = (state: any) => state.lastUpdated;

export default function Dashboard() {
  // Use individual selectors to prevent unnecessary re-renders
  const dashboardData = useStore(selectDashboardData);
  const loading = useStore(selectDashboardLoading);
  const errors = useStore(selectDashboardErrors);
  const fetchDashboardData = useStore(selectFetchDashboardData);
  const lastUpdated = useStore(selectLastUpdated);

  useEffect(() => {
    // Fetch data on component mount
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleRefresh = () => {
    fetchDashboardData();
  };

  const handlePageChange = (page: number) => {
    fetchDashboardData({ page, perPage: dashboardData?.pagination?.per_page || 50 });
  };

  return (
    <div className="container mx-auto py-6">
      {/* Page header with title and last updated info */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-sm text-muted-foreground">
              Last updated: {formatDate(lastUpdated)}
            </span>
          )}
          <Button onClick={handleRefresh} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Error state */}
      {errors && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{errors.message && errors.message}</AlertDescription>
        </Alert>
      )}

      {/* Loading state */}
      {loading && !dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-8 w-3/4 mb-2" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-24 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* No data state */}
      {!loading && !dashboardData && (
        <Alert className="mb-6">
          <AlertTitle>No data available</AlertTitle>
          <AlertDescription>
            Click the refresh button to load data.
          </AlertDescription>
        </Alert>
      )}

      {/* Dashboard content */}
      {dashboardData && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {/* Summary Card */}
            <Card>
              <CardHeader>
                <CardTitle>Summary</CardTitle>
                <CardDescription>Overview of all data sources</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>Total Sources:</span>
                    <span className="font-medium">{dashboardData.active_sources || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total Proposals:</span>
                    <span className="font-medium">{dashboardData.total_proposals || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Last Run:</span>
                    <span className="font-medium">
                      {dashboardData.last_scrape ? formatDate(dashboardData.last_scrape) : 'Never'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Status Card */}
            <Card>
              <CardHeader>
                <CardTitle>Status</CardTitle>
                <CardDescription>Current system status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>System Status:</span>
                    <span className={`font-medium ${dashboardData.systemStatus === 'Running' ? 'text-green-500' : 'text-red-500'}`}>
                      {dashboardData.systemStatus || 'Unknown'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Active Jobs:</span>
                    <span className="font-medium">{dashboardData.activeJobs || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Pending Jobs:</span>
                    <span className="font-medium">{dashboardData.pendingJobs || 0}</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Activity Card */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Latest system activities</CardDescription>
              </CardHeader>
              <CardContent>
                {dashboardData.recentActivity && dashboardData.recentActivity.length > 0 ? (
                  <ul className="space-y-2">
                    {dashboardData.recentActivity.slice(0, 5).map((activity: any, index: number) => (
                      <li key={index} className="text-sm">
                        <div className="font-medium">{activity.action}</div>
                        <div className="text-muted-foreground">{formatDate(activity.timestamp)}</div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">No recent activity</p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Proposals Table */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Proposals</CardTitle>
              <CardDescription>
                Recent proposals from all sources
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboardData.proposals && dashboardData.proposals.length > 0 ? (
                <>
                  <div className="rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Title</TableHead>
                          <TableHead>Agency</TableHead>
                          <TableHead>Source</TableHead>
                          <TableHead>Release Date</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {dashboardData.proposals.map((proposal: any) => (
                          <TableRow key={proposal.id}>
                            <TableCell className="font-medium">{proposal.title}</TableCell>
                            <TableCell>{proposal.agency}</TableCell>
                            <TableCell>{proposal.source_name}</TableCell>
                            <TableCell>{proposal.release_date ? formatDate(proposal.release_date) : 'N/A'}</TableCell>
                            <TableCell>{proposal.status}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Pagination */}
                  {dashboardData.pagination && dashboardData.pagination.total_pages > 1 && (
                    <div className="flex justify-center mt-4">
                      <Pagination>
                        <PaginationContent>
                          <PaginationItem>
                            <PaginationPrevious 
                              onClick={() => handlePageChange(Math.max(1, (dashboardData.pagination?.page || 1) - 1))}
                              className={dashboardData.pagination.page <= 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                            />
                          </PaginationItem>
                          
                          {Array.from({ length: Math.min(5, dashboardData.pagination.total_pages) }, (_, i) => {
                            const pageNumber = i + 1;
                            return (
                              <PaginationItem key={pageNumber}>
                                <PaginationLink 
                                  onClick={() => handlePageChange(pageNumber)}
                                  isActive={pageNumber === dashboardData.pagination.page}
                                >
                                  {pageNumber}
                                </PaginationLink>
                              </PaginationItem>
                            );
                          })}
                          
                          <PaginationItem>
                            <PaginationNext 
                              onClick={() => handlePageChange(Math.min(dashboardData.pagination.total_pages, (dashboardData.pagination?.page || 1) + 1))}
                              className={dashboardData.pagination.page >= dashboardData.pagination.total_pages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                            />
                          </PaginationItem>
                        </PaginationContent>
                      </Pagination>
                    </div>
                  )}
                </>
              ) : (
                <Alert>
                  <AlertTitle>No proposals found</AlertTitle>
                  <AlertDescription>
                    There are currently no proposals in the system.
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
} 