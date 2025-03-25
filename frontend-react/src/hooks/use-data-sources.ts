import { createEntityHooks } from './use-query';

export interface DataSource {
  id: number;
  name: string;
  url: string;
  status: 'active' | 'inactive';
  lastUpdated: string;
  totalProposals: number;
}

export interface CreateDataSourceDto {
  name: string;
  url: string;
}

export interface UpdateDataSourceDto {
  name?: string;
  url?: string;
  status?: 'active' | 'inactive';
}

export const {
  useGetAll: useGetAllDataSources,
  useGetById: useGetDataSourceById,
  useCreate: useCreateDataSource,
  useUpdate: useUpdateDataSource,
  useDelete: useDeleteDataSource,
} = createEntityHooks<DataSource, CreateDataSourceDto, UpdateDataSourceDto>(
  'dataSources',
  '/data-sources'
);

// Example usage:
/*
function DataSourcesList() {
  const { data, isLoading, error } = useGetAllDataSources();
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <ul>
      {data?.data.map(source => (
        <li key={source.id}>{source.name}</li>
      ))}
    </ul>
  );
}

function DataSourceForm() {
  const createMutation = useCreateDataSource({
    onSuccess: () => {
      // Handle success
    }
  });
  
  const handleSubmit = (data: CreateDataSourceDto) => {
    createMutation.mutate(data);
  };
  
  return <form onSubmit={handleSubmit}>...</form>;
}
*/ 