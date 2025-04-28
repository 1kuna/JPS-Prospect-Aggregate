import { createEntityHooks } from "./useApi";
import { Proposal, ProposalFilters, ProposalStatistics } from '@/types/proposals';

// @ts-ignore // Suppress TS2347
export const useProposals = (createEntityHooks as any)<Proposal, ProposalFilters>(
  'proposals',
  '/api/proposals',
);

// Hook for proposal statistics
export const useProposalStatistics = () => {
  const { useQuery } = useProposals;
  // @ts-ignore // Suppress TS2347
  return (useQuery as any)<ProposalStatistics>(
    ['statistics'],
    '/api/proposals/statistics'
  );
};

// The following hooks are automatically created by createEntityHooks:
// - useProposals().useList() - Get list of proposals with pagination
// - useProposals().useGet(id) - Get single proposal
// - useProposals().useCreate() - Create new proposal
// - useProposals().useUpdate(id) - Update proposal
// - useProposals().useDelete(id) - Delete proposal
// - useProposals().useInfiniteList() - Get infinite-loading list 