import { useQuery, useInfiniteQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { Prospect, ProspectFilters, ProspectStatistics, ProspectStatus } from '@/types/prospects';
import { ApiResponse } from '@/types/api';
import { get, buildQueryString } from '@/utils/apiUtils';

// --- API Call Functions ---

// Simulate a paginated API response structure
interface PaginatedProspectsResponse {
  data: Prospect[];
  nextCursor?: number | null;
  totalCount: number;
}

async function fetchProspectsAPI(
  { pageParam = 0, filters }: { pageParam?: number; filters?: ProspectFilters }
): Promise<PaginatedProspectsResponse> {
  // Fetching prospects with pagination
  
  const params: Record<string, string | number | boolean | Array<string | number>> = {
    page: pageParam + 1, // Backend is 1-indexed
    limit: 10,
    ...filters
  };
  
  // Backend uses 1-indexed pagination
  
  const url = `/api/prospects${buildQueryString(params)}`;
  const responseJson = await get<{
    prospects: Prospect[];
    pagination?: {
      has_next: boolean;
      page: number;
      total_items: number;
    };
  }>(url);
  
  // Transform backend response

  const transformedData = {
    data: responseJson.prospects || [],
    nextCursor: responseJson.pagination?.has_next ? responseJson.pagination.page : undefined,
    totalCount: responseJson.pagination?.total_items || 0,
  };
  // Return transformed data
  return transformedData;
}

async function fetchProspectStatisticsAPI(): Promise<ProspectStatistics> {
  // Fetching prospect statistics
  await new Promise(resolve => setTimeout(resolve, 300));
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
  // Creating new prospect
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate API response
  const createdProspect: Prospect = {
    id: `prospect-${Math.floor(Math.random() * 1000) + 100}`, // Generate a random ID
    ...newProspect,
    createdAt: new Date().toISOString(),
    status: newProspect.status || ProspectStatus.SUBMITTED, // Default status if not provided
  };
  // Return created prospect
  return createdProspect;
}

async function updateProspectAPI({ id, ...updatedData }: Partial<Prospect> & { id: Prospect['id'] }): Promise<Prospect> {
  // Updating prospect
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
  // Return updated prospect
  return mockUpdatedProspect;
}

async function deleteProspectAPI(_: Prospect['id']): Promise<void> {
  // Deleting prospect
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate successful deletion (API typically returns 204 No Content or similar)
  // Deletion successful
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
      // Calculate next page parameter
      return lastPage.nextCursor ? lastPage.nextCursor : undefined;
    },
  });

  // Flatten paginated data
  const flattenedData = result.data?.pages.flatMap(page => page.data) ?? [];
  // Return flattened data

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

// Hook to get a single prospect by ID
export function useProspect(prospectId: string | number | null) {
  return useQuery({
    queryKey: ['prospects', prospectId],
    queryFn: async () => {
      const response = await fetch(`/api/prospects/${prospectId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch prospect');
      }
      return response.json() as Promise<ApiResponse<Prospect>>;
    },
    enabled: !!prospectId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// --- Mutation Hooks for Prospects ---

export function useCreateProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createProspectAPI,
    onSuccess: () => {
      // Invalidate and refetch the list of prospects
      queryClient.invalidateQueries({ queryKey: prospectQueryKeys.lists() });
      // Optionally, you could add the new prospect to the infinite list cache
      // This can be complex with infinite lists; often invalidation is simpler.
      // Invalidated prospects list after creation
    },
    onError: () => {
      // Handle creation error
    }
  });
}

export function useUpdateProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateProspectAPI,
    onSuccess: () => {
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
      // Invalidated prospects list after update

    },
    onError: () => {
      // Handle update error
    }
  });
}

export function useDeleteProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteProspectAPI,
    onSuccess: () => {
      // Invalidate and refetch the list of prospects
      queryClient.invalidateQueries({ queryKey: prospectQueryKeys.lists() });
      // Optionally, optimistic update or direct cache manipulation
      // Similar to update, but removing the item.
      // Invalidated prospects list after deletion
    },
    onError: () => {
      // Handle deletion error
    }
  });
}