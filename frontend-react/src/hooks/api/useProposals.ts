import { useQuery, useInfiniteQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { Proposal, ProposalFilters, ProposalStatistics, ProposalStatus } from '@/types/proposals';

// Placeholder API base URL - commented out to remove unused variable warning
// const API_BASE_URL = '/api'; // Adjust as needed

// --- API Call Functions (Placeholders) ---

// Simulate a paginated API response structure
interface PaginatedProposalsResponse {
  data: Proposal[];
  nextCursor?: number | null;
  totalCount: number;
}

async function fetchProposalsAPI(
  { pageParam = 0, filters }: { pageParam?: number; filters?: ProposalFilters }
): Promise<PaginatedProposalsResponse> {
  console.log(`Fetching proposals... pageParam (0-indexed): ${pageParam}, filters:`, filters);
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
  console.log('[useProposals.ts] Raw responseJson from backend:', responseJson);

  const transformedData = {
    data: responseJson.prospects || [],
    nextCursor: responseJson.pagination?.has_next ? responseJson.pagination.page : undefined,
    totalCount: responseJson.pagination?.total_items || 0,
  };
  console.log('[useProposals.ts] Transformed data in fetchProposalsAPI:', transformedData);
  return transformedData;
}

async function fetchProposalStatisticsAPI(): Promise<ProposalStatistics> {
  console.log('Fetching proposal statistics...');
  // const response = await fetch(`/api/proposals/statistics`); // Commenting this out for now
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

// --- Mock API functions for Proposal mutations ---
async function createProposalAPI(newProposal: Omit<Proposal, 'id' | 'createdAt' | 'updatedAt'>): Promise<Proposal> {
  console.log("Simulating create proposal:", newProposal);
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate API response
  const createdProposal: Proposal = {
    id: `prop-${Math.floor(Math.random() * 1000) + 100}`, // Generate a random ID
    ...newProposal,
    createdAt: new Date().toISOString(),
    status: newProposal.status || ProposalStatus.SUBMITTED, // Default status if not provided
  };
  console.log("Simulated created proposal:", createdProposal);
  return createdProposal;
}

async function updateProposalAPI({ id, ...updatedData }: Partial<Proposal> & { id: Proposal['id'] }): Promise<Proposal> {
  console.log(`Simulating update proposal ${id}:`, updatedData);
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate API response, assuming the update is successful and returns the updated object
  // In a real API, you would fetch the proposal and merge updates or rely on the backend to do so.
  const mockUpdatedProposal: Proposal = {
    // These would ideally come from a fetched existing proposal
    title: "Updated Title", 
    dataSource: { id: 'ds-0', name: 'DataSource X'},
    url: 'http://example.com/updated',
    ...updatedData, // Apply incoming updates
    id,
    createdAt: new Date(Date.now() - 100000000).toISOString(), // Keep original or mock
    updatedAt: new Date().toISOString(),
    status: updatedData.status || ProposalStatus.SUBMITTED,
  };
  console.log("Simulated updated proposal:", mockUpdatedProposal);
  return mockUpdatedProposal;
}

async function deleteProposalAPI(proposalId: Proposal['id']): Promise<void> {
  console.log(`Simulating delete proposal ${proposalId}`);
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate successful deletion (API typically returns 204 No Content or similar)
  console.log(`Simulated deletion of proposal ${proposalId} successful.`);
}

// --- React Query Hooks ---

const proposalQueryKeys = {
  all: () => ['proposals'] as const,
  lists: () => [...proposalQueryKeys.all(), 'list'] as const,
  list: (filters?: ProposalFilters) => [...proposalQueryKeys.lists(), { filters }] as const, // Infinite query key usually includes filters
  statistics: () => [...proposalQueryKeys.all(), 'statistics'] as const,
  details: () => [...proposalQueryKeys.all(), 'detail'] as const, // For individual proposal details if needed
  detail: (id: Proposal['id']) => [...proposalQueryKeys.details(), id] as const, // For individual proposal details
};

export function useInfiniteProposals(filters?: ProposalFilters) {
  const result = useInfiniteQuery({
    queryKey: proposalQueryKeys.list(filters),
    queryFn: ({ pageParam = 0 }) => fetchProposalsAPI({ pageParam, filters }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, _allPages) => {
      // lastPage.nextCursor is the 'page' number from the backend's pagination response for the *last fetched page*.
      // If it exists (meaning has_next was true), it means there's potentially another page.
      // react-query will pass this returned value as `pageParam` to `fetchProposalsAPI` for the next fetch.
      // The value itself should be the page number that was *just fetched* if a next page exists.
      console.log('[useProposals.ts] getNextPageParam - lastPage:', lastPage);
      return lastPage.nextCursor ? lastPage.nextCursor : undefined;
    },
  });

  console.log('[useProposals.ts] result.data from useInfiniteQuery (before flattening):', result.data);
  const flattenedData = result.data?.pages.flatMap(page => page.data) ?? [];
  console.log('[useProposals.ts] flattenedData:', flattenedData);

  return {
    ...result,
    data: flattenedData, // Override data with the flattened array
    // fetchNextPage, hasNextPage, isFetchingNextPage are already part of result
  };
}

export function useProposalStatistics() {
  return useQuery({
    queryKey: proposalQueryKeys.statistics(),
    queryFn: fetchProposalStatisticsAPI,
    // Configure options like staleTime if needed
  });
}

// --- Mutation Hooks for Proposals ---

export function useCreateProposal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createProposalAPI,
    onSuccess: (newProposal) => {
      // Invalidate and refetch the list of proposals
      queryClient.invalidateQueries({ queryKey: proposalQueryKeys.lists() });
      // Optionally, you could add the new proposal to the infinite list cache
      // This can be complex with infinite lists; often invalidation is simpler.
      console.log('CreateProposal success, invalidated proposals list. New proposal:', newProposal);
    },
    onError: (error) => {
      console.error('CreateProposal error:', error);
    }
  });
}

export function useUpdateProposal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateProposalAPI,
    onSuccess: (_, variables) => {
      // Invalidate the list of proposals to refetch
      queryClient.invalidateQueries({ queryKey: proposalQueryKeys.lists() });
      // Optionally, invalidate the specific proposal detail query if you have one
      // queryClient.invalidateQueries({ queryKey: proposalQueryKeys.detail(variables.id) });

      // More advanced: update the cache directly for a smoother UX
      // This requires careful handling of the paginated/infinite data structure.
      // Example for infinite list (can be complex):
      // queryClient.setQueryData<InfiniteData<PaginatedProposalsResponse>>(
      //   proposalQueryKeys.list(/* provide current filters if any */),
      //   (oldData) => {
      //     if (!oldData) return oldData;
      //     return {
      //       ...oldData,
      //       pages: oldData.pages.map(page => ({
      //         ...page,
      //         data: page.data.map(proposal =>
      //           proposal.id === variables.id ? updatedProposal : proposal
      //         ),
      //       })),
      //     };
      //   }
      // );
      console.log('UpdateProposal success, invalidated proposals list. Updated proposal ID:', variables.id);

    },
    onError: (error, variables) => {
      console.error('UpdateProposal error for ID:', variables.id, error);
    }
  });
}

export function useDeleteProposal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteProposalAPI,
    onSuccess: (_, proposalId) => {
      // Invalidate and refetch the list of proposals
      queryClient.invalidateQueries({ queryKey: proposalQueryKeys.lists() });
      // Optionally, optimistic update or direct cache manipulation
      // Similar to update, but removing the item.
      console.log('DeleteProposal success, invalidated proposals list. Deleted proposal ID:', proposalId);
    },
    onError: (error, proposalId) => {
      console.error('DeleteProposal error for ID:', proposalId, error);
    }
  });
}