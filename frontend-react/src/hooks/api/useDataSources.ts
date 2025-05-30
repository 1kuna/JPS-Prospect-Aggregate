import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DataSource } from '@/types';

// Placeholder API base URL - commented out to remove unused variable warning
// const API_BASE_URL = '/api'; // Adjust as needed

// --- API Call Functions (Placeholders) ---
// Typically, these would use fetch or axios to interact with your backend

async function fetchDataSourcesAPI(): Promise<DataSource[]> {
  const response = await fetch(`/api/data-sources`);
  if (!response.ok) {
    throw new Error('Network response was not ok while fetching data sources');
  }
  return response.json();
}

async function createDataSourceAPI(newDataSource: Omit<DataSource, 'id'>): Promise<DataSource> {
  const response = await fetch(`/api/data-sources`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newDataSource),
  });
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Failed to create data source: ${response.status} ${errorBody}`);
  }
  return response.json();
}

async function updateDataSourceAPI({ id, ...updatedData }: Partial<DataSource> & { id: DataSource['id'] }): Promise<DataSource> {
  const response = await fetch(`/api/data-sources/${id}`, {
    method: 'PUT', // or 'PATCH'
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updatedData),
  });
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Failed to update data source ${id}: ${response.status} ${errorBody}`);
  }
  return response.json();
}

async function deleteDataSourceAPI(dataSourceId: DataSource['id']): Promise<void> {
  const response = await fetch(`/api/data-sources/${dataSourceId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Failed to delete data source ${dataSourceId}: ${response.status} ${errorBody}`);
  }
  // No content typically, so no response.json()
}

// --- React Query Hooks ---

const dataSourceQueryKeys = {
  all: () => ['dataSources'] as const,
  lists: () => [...dataSourceQueryKeys.all(), 'list'] as const,
  list: (filters: string) => [...dataSourceQueryKeys.lists(), { filters }] as const,
  details: () => [...dataSourceQueryKeys.all(), 'detail'] as const,
  detail: (id: DataSource['id']) => [...dataSourceQueryKeys.details(), id] as const,
};


export function useListDataSources() {
  return useQuery({
    queryKey: dataSourceQueryKeys.lists(),
    queryFn: fetchDataSourcesAPI,
    staleTime: 5 * 60 * 1000, // 5 minutes
    // Add other React Query options as needed, e.g., onSuccess, onError, refetchOnWindowFocus: false
  });
}

export function useCreateDataSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createDataSourceAPI,
    onSuccess: () => {
      // Invalidate and refetch the list of data sources
      queryClient.invalidateQueries({ queryKey: dataSourceQueryKeys.lists() });
      // Optionally, update the cache directly if the API returns the created item
      // queryClient.setQueryData(dataSourceQueryKeys.list(), (oldData: DataSource[] | undefined) => [...(oldData || []), data]);
    },
    // Add other React Query options as needed, e.g., onError, onMutate
  });
}

export function useUpdateDataSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateDataSourceAPI,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: dataSourceQueryKeys.lists() });
      queryClient.invalidateQueries({ queryKey: dataSourceQueryKeys.detail(variables.id) });
      // Optionally, update the cache directly
      // queryClient.setQueryData(dataSourceQueryKeys.detail(variables.id), data);
      // queryClient.setQueryData(dataSourceQueryKeys.list(), (oldData: DataSource[] | undefined) =>
      //   oldData?.map(item => item.id === variables.id ? data : item) || []
      // );
    },
  });
}

export function useDeleteDataSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteDataSourceAPI,
    onSuccess: () => {
      // Invalidate and refetch the list of data sources
      queryClient.invalidateQueries({ queryKey: dataSourceQueryKeys.lists() });
      // Optimistic update: Remove the item from the cache immediately
      // queryClient.setQueryData(dataSourceQueryKeys.list(), (oldData: DataSource[] | undefined) =>
      //   oldData?.filter(ds => ds.id !== dataSourceId) || []
      // );
    },
  });
}

// If you need a hook for fetching a single data source by ID:
// export function useDataSource(id: DataSource['id']) {
//   return useQuery({
//     queryKey: dataSourceQueryKeys.detail(id),
//     queryFn: () => fetchDataSourcesAPI().then(sources => sources.find(s => s.id === id)), // Highly inefficient, fetch by ID directly
//     enabled: !!id, // Only run query if ID is provided
//   });
// }