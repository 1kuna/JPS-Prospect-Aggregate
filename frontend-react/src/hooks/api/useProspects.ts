import { useQuery, useInfiniteQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { Prospect, ProspectFilters, ProspectStatistics, ProspectStatus } from '@/types/prospects';

// Placeholder API base URL - commented out to remove unused variable warning
// const API_BASE_URL = '/api'; // Adjust as needed

// --- API Call Functions (Placeholders) ---

// Simulate a paginated API response structure
interface PaginatedProspectsResponse {
  data: Prospect[];
  nextCursor?: number | null;
  totalCount: number;
}

async function fetchProspectsAPI(
  { pageParam = 0, filters }: { pageParam?: number; filters?: ProspectFilters }
): Promise<PaginatedProspectsResponse> {
  console.log(`Fetching prospects... pageParam (0-indexed): ${pageParam}, filters:`, filters);
  const queryParams = new URLSearchParams();
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => queryParams.append(key, String(value)));
  }
  const backendPageToFetch = pageParam + 1; // Backend is 1-indexed
  queryParams.append('page', String(backendPageToFetch));
  queryParams.append('limit', '10');
  console.log(`Requesting backend page: ${backendPageToFetch}`);

  const response = await fetch(`/api/prospects?${queryParams.toString()}`);
  if (!response.ok) {
    console.error('Network response was not ok', response);
    throw new Error('Network response was not ok');
  }
  const responseJson = await response.json();
  console.log('[useProspects.ts] Raw responseJson from backend:', responseJson);

  const transformedData = {
    data: responseJson.prospects || [],
    nextCursor: responseJson.pagination?.has_next ? responseJson.pagination.page : undefined,
    totalCount: responseJson.pagination?.total_items || 0,
  };
  console.log('[useProspects.ts] Transformed data in fetchProspectsAPI:', transformedData);
  return transformedData;
}

async function fetchProspectStatisticsAPI(): Promise<ProspectStatistics> {
  console.log('Fetching prospect statistics...');
  // const response = await fetch(`/api/prospects/statistics`); // Commenting this out for now
  // if (!response.ok) throw new Error('Network response was not ok');
  // return response.json();
  await new Promise(resolve => setTimeout(resolve, 300)); // Keep a small delay to avoid breaking the UI immediately
  // Return mock/empty statistics data for now to prevent errors
  return {
    data: { 
        total: 0,
        approved: 0,
        pending: 0,
        rejected: 0,
    }
  };
}

// --- Mock API functions for Prospect mutations ---
async function createProspectAPI(newProspect: Omit<Prospect, 'id' | 'createdAt' | 'updatedAt'>): Promise<Prospect> {
  console.log("Simulating create prospect:", newProspect);
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate API response
  const createdProspect: Prospect = {
    id: `prospect-${Math.floor(Math.random() * 1000) + 100}`, // Generate a random ID
    ...newProspect,
    createdAt: new Date().toISOString(),
    status: newProspect.status || ProspectStatus.SUBMITTED, // Default status if not provided
  };
  console.log("Simulated created prospect:", createdProspect);
  return createdProspect;
}

async function updateProspectAPI({ id, ...updatedData }: Partial<Prospect> & { id: Prospect['id'] }): Promise<Prospect> {
  console.log(`Simulating update prospect ${id}:`, updatedData);
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate API response, assuming the update is successful and returns the updated object
  // In a real API, you would fetch the prospect and merge updates or rely on the backend to do so.
  const mockUpdatedProspect: Prospect = {
    // These would ideally come from a fetched existing prospect
    title: "Updated Title", 
    dataSource: { id: 'ds-0', name: 'DataSource X'},
    url: 'http://example.com/updated',
    ...updatedData, // Apply incoming updates
    id,
    createdAt: new Date(Date.now() - 100000000).toISOString(), // Keep original or mock
    updatedAt: new Date().toISOString(),
    status: updatedData.status || ProspectStatus.SUBMITTED,
  };
  console.log("Simulated updated prospect:", mockUpdatedProspect);
  return mockUpdatedProspect;
}

async function deleteProspectAPI(prospectId: Prospect['id']): Promise<void> {
  console.log(`Simulating delete prospect ${prospectId}`);
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate successful deletion (API typically returns 204 No Content or similar)
  console.log(`Simulated deletion of prospect ${prospectId} successful.`);
}

// --- React Query Hooks ---

const prospectQueryKeys = {
  all: () => ['prospects'] as const,
  lists: () => [...prospectQueryKeys.all(), 'list'] as const,
  list: (filters?: ProspectFilters) => [...prospectQueryKeys.lists(), { filters }] as const, // Infinite query key usually includes filters
  statistics: () => [...prospectQueryKeys.all(), 'statistics'] as const,
  details: () => [...prospectQueryKeys.all(), 'detail'] as const, // For individual prospect details if needed
  detail: (id: Prospect['id']) => [...prospectQueryKeys.details(), id] as const, // For individual prospect details
};

export function useInfiniteProspects(filters?: ProspectFilters) {
  const result = useInfiniteQuery({
    queryKey: prospectQueryKeys.list(filters),
    queryFn: ({ pageParam = 0 }) => fetchProspectsAPI({ pageParam, filters }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      // lastPage.nextCursor is the 'page' number from the backend's pagination response for the *last fetched page*.
      // If it exists (meaning has_next was true), it means there's potentially another page.
      // react-query will pass this returned value as `pageParam` to `fetchProspectsAPI` for the next fetch.
      // The value itself should be the page number that was *just fetched* if a next page exists.
      console.log('[useProspects.ts] getNextPageParam - lastPage:', lastPage);
      return lastPage.nextCursor ? lastPage.nextCursor : undefined;
    },
  });

  console.log('[useProspects.ts] result.data from useInfiniteQuery (before flattening):', result.data);
  const flattenedData = result.data?.pages.flatMap(page => page.data) ?? [];
  console.log('[useProspects.ts] flattenedData:', flattenedData);

  return {
    ...result,
    data: flattenedData, // Override data with the flattened array
    // fetchNextPage, hasNextPage, isFetchingNextPage are already part of result
  };
}

export function useProspectStatistics() {
  return useQuery({
    queryKey: prospectQueryKeys.statistics(),
    queryFn: fetchProspectStatisticsAPI,
    // Configure options like staleTime if needed
  });
}

// --- Mutation Hooks for Prospects ---

export function useCreateProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createProspectAPI,
    onSuccess: (newProspect) => {
      // Invalidate and refetch the list of prospects
      queryClient.invalidateQueries({ queryKey: prospectQueryKeys.lists() });
      // Optionally, you could add the new prospect to the infinite list cache
      // This can be complex with infinite lists; often invalidation is simpler.
      console.log('CreateProspect success, invalidated prospects list. New prospect:', newProspect);
    },
    onError: (error) => {
      console.error('CreateProspect error:', error);
    }
  });
}

export function useUpdateProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateProspectAPI,
    onSuccess: (_, variables) => {
      // Invalidate the list of prospects to refetch
      queryClient.invalidateQueries({ queryKey: prospectQueryKeys.lists() });
      // Optionally, invalidate the specific prospect detail query if you have one
      // queryClient.invalidateQueries({ queryKey: prospectQueryKeys.detail(variables.id) });

      // More advanced: update the cache directly for a smoother UX
      // This requires careful handling of the paginated/infinite data structure.
      // Example for infinite list (can be complex):
      // queryClient.setQueryData<InfiniteData<PaginatedProspectsResponse>>(
      //   prospectQueryKeys.list(/* provide current filters if any */),
      //   (oldData) => {
      //     if (!oldData) return oldData;
      //     return {
      //       ...oldData,
      //       pages: oldData.pages.map(page => ({
      //         ...page,
      //         data: page.data.map(prospect =>
      //           prospect.id === variables.id ? updatedProspect : prospect
      //         ),
      //       })),
      //     };
      //   }
      // );
      console.log('UpdateProspect success, invalidated prospects list. Updated prospect ID:', variables.id);

    },
    onError: (error, variables) => {
      console.error('UpdateProspect error for ID:', variables.id, error);
    }
  });
}

export function useDeleteProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteProspectAPI,
    onSuccess: (_, prospectId) => {
      // Invalidate and refetch the list of prospects
      queryClient.invalidateQueries({ queryKey: prospectQueryKeys.lists() });
      // Optionally, optimistic update or direct cache manipulation
      // Similar to update, but removing the item.
      console.log('DeleteProspect success, invalidated prospects list. Deleted prospect ID:', prospectId);
    },
    onError: (error, prospectId) => {
      console.error('DeleteProspect error for ID:', prospectId, error);
    }
  });
}