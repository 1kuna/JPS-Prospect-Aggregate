import { createEntityHooks } from './use-query';

export interface Proposal {
  id: number;
  title: string;
  description: string;
  status: 'active' | 'inactive' | 'archived';
  dataSourceId: number;
  createdAt: string;
  updatedAt: string;
  metadata: Record<string, any>;
}

export interface CreateProposalDto {
  title: string;
  description: string;
  status: 'active' | 'inactive';
  dataSourceId: number;
  metadata?: Record<string, any>;
}

export interface UpdateProposalDto {
  title?: string;
  description?: string;
  status?: 'active' | 'inactive' | 'archived';
  metadata?: Record<string, any>;
}

export const {
  useGetAll: useGetAllProposals,
  useGetById: useGetProposalById,
  useCreate: useCreateProposal,
  useUpdate: useUpdateProposal,
  useDelete: useDeleteProposal,
} = createEntityHooks<Proposal, CreateProposalDto, UpdateProposalDto>(
  'proposals',
  '/proposals'
); 