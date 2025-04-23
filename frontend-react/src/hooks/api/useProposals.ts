import { createEntityHooks } from "./useApi";
import { Proposal, ProposalFilters, ProposalStatistics } from '@/types/proposals';

// Create base CRUD hooks
export const useProposals = createEntityHooks<Proposal, ProposalFilters>(
  'proposals',
  '/api/proposals',
);

// Add custom proposal-specific hooks
export const useProposalStatistics = () => {
  const { useQuery } = useProposals;
  return useQuery<ProposalStatistics>(
    ['statistics'],
    '/api/proposals/statistics'
  );
};

export const useRecentProposals = (limit: number = 5) => {
  const { useQuery } = useProposals;
  return useQuery<Proposal[]>(
    ['recent', { limit }],
    '/api/proposals/recent',
    { params: { limit } }
  );
};

// The following hooks are automatically created by createEntityHooks:
// - useProposals().useList() - Get list of proposals with pagination
// - useProposals().useGet(id) - Get single proposal
// - useProposals().useCreate() - Create new proposal
// - useProposals().useUpdate(id) - Update proposal
// - useProposals().useDelete(id) - Delete proposal
// - useProposals().useInfiniteList() - Get infinite-loading list 