import { useQuery, useInfiniteQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { Proposal, ProposalFilters, ProposalStatistics, ProposalStatus } from '@/types/proposals';

// Placeholder API base URL
const API_BASE_URL = '/api'; // Adjust as needed

// --- API Call Functions (Placeholders) ---

// Simulate a paginated API response structure
interface PaginatedProposalsResponse {
  data: Proposal[];
  nextCursor?: number | null; // Or string, depending on your API
  totalCount: number;
}

async function fetchProposalsAPI(
  { pageParam = 0, filters }: { pageParam?: number; filters?: ProposalFilters }
): Promise<PaginatedProposalsResponse> {
  console.log(`Fetching proposals... page: ${pageParam}, filters:`, filters);
  // Simulate API call with pagination
  // const queryParams = new URLSearchParams();
  // if (filters) {
  //   Object.entries(filters).forEach(([key, value]) => queryParams.append(key, String(value)));
  // }
  // queryParams.append('page', String(pageParam));
  // queryParams.append('limit', '10'); // Example page size
  // const response = await fetch(`${API_BASE_URL}/proposals?${queryParams.toString()}`);
  // if (!response.ok) {
  //   throw new Error('Network response was not ok');
  // }
  // return response.json();

  await new Promise(resolve => setTimeout(resolve, 750)); // Simulate network delay

  // Mock data for demonstration
  const pageSize = 10;
  const allMockProposals: Proposal[] = Array.from({ length: 35 }, (_, i) => ({
    id: `prop-${i + 1}`,
    title: `Proposal ${i + 1} for Project ${String.fromCharCode(65 + (i % 5))}`,
    status: i % 3 === 0 ? ProposalStatus.APPROVED : i % 3 === 1 ? ProposalStatus.PENDING : ProposalStatus.REJECTED,
    dataSource: { id: `ds-${i % 2}`, name: `DataSource ${i % 2 === 0 ? 'X' : 'Y'}` },
    createdAt: new Date(Date.now() - i * 1000 * 60 * 60 * 24).toISOString(),
    url: `http://example.com/proposal/${i + 1}`,
    // Add other Proposal fields as necessary
  }));

  const start = pageParam * pageSize;
  const end = start + pageSize;
  const pageData = allMockProposals.slice(start, end);

  return {
    data: pageData,
    nextCursor: end < allMockProposals.length ? pageParam + 1 : null,
    totalCount: allMockProposals.length,
  };
}

async function fetchProposalStatisticsAPI(): Promise<ProposalStatistics> {
  console.log('Fetching proposal statistics...');
  // const response = await fetch(`${API_BASE_URL}/proposals/statistics`);
  // if (!response.ok) throw new Error('Network response was not ok');
  // return response.json();
  await new Promise(resolve => setTimeout(resolve, 300));
  return {
    data: { // Assuming ProposalStatistics has a nested data object based on Proposals.tsx usage
        total: 35,
        approved: 12,
        pending: 12,
        rejected: 11,
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
    status: newProposal.status || ProposalStatus.PENDING, // Default status if not provided
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
    status: updatedData.status || ProposalStatus.PENDING,
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
  all: ['proposals'] as const,
  lists: () => [...proposalQueryKeys.all, 'list'] as const,
  list: (filters?: ProposalFilters) => [...proposalQueryKeys.lists(), { filters }] as const, // Infinite query key usually includes filters
  statistics: () => [...proposalQueryKeys.all, 'statistics'] as const,
  details: () => [...proposalQueryKeys.all, 'detail'] as const, // For individual proposal details if needed
  detail: (id: Proposal['id']) => [...proposalQueryKeys.details(), id] as const, // For individual proposal details
};

export function useInfiniteProposals(filters?: ProposalFilters) {
  const result = useInfiniteQuery<PaginatedProposalsResponse, Error>(
    proposalQueryKeys.list(filters),
    ({ pageParam }) => fetchProposalsAPI({ pageParam, filters }),
    {
      getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
      // staleTime, cacheTime, etc. can be configured here
    }
  );

  // Flatten pages for easier consumption in components
  const flattenedData = result.data?.pages.flatMap(page => page.data) ?? [];

  return {
    ...result,
    data: flattenedData, // Override data with the flattened array
    // fetchNextPage, hasNextPage, isFetchingNextPage are already part of result
  };
}

export function useProposalStatistics() {
  return useQuery<ProposalStatistics, Error>(
    proposalQueryKeys.statistics(),
    fetchProposalStatisticsAPI
    // Configure options like staleTime if needed
  );
}

// --- Mutation Hooks for Proposals ---

export function useCreateProposal() {
  const queryClient = useQueryClient();
  return useMutation<Proposal, Error, Omit<Proposal, 'id' | 'createdAt' | 'updatedAt'>>(
    createProposalAPI,
    {
      onSuccess: (newProposal) => {
        // Invalidate and refetch the list of proposals
        queryClient.invalidateQueries(proposalQueryKeys.lists());
        // Optionally, you could add the new proposal to the infinite list cache
        // This can be complex with infinite lists; often invalidation is simpler.
        console.log('CreateProposal success, invalidated proposals list. New proposal:', newProposal);
      },
      onError: (error) => {
        console.error('CreateProposal error:', error);
      }
    }
  );
}

export function useUpdateProposal() {
  const queryClient = useQueryClient();
  return useMutation<Proposal, Error, Partial<Proposal> & { id: Proposal['id'] }>(
    updateProposalAPI,
    {
      onSuccess: (updatedProposal, variables) => {
        // Invalidate the list of proposals to refetch
        queryClient.invalidateQueries(proposalQueryKeys.lists());
        // Optionally, invalidate the specific proposal detail query if you have one
        // queryClient.invalidateQueries(proposalQueryKeys.detail(variables.id));

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
    }
  );
}

export function useDeleteProposal() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, Proposal['id']>(
    deleteProposalAPI,
    {
      onSuccess: (_, proposalId) => {
        // Invalidate and refetch the list of proposals
        queryClient.invalidateQueries(proposalQueryKeys.lists());
        // Optionally, optimistic update or direct cache manipulation
        // Similar to update, but removing the item.
        console.log('DeleteProposal success, invalidated proposals list. Deleted proposal ID:', proposalId);
      },
      onError: (error, proposalId) => {
        console.error('DeleteProposal error for ID:', proposalId, error);
      }
    }
  );
}