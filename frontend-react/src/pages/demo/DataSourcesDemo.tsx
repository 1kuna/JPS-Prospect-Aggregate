import { useEffect, useState } from 'react';
import { useDataSourcesSelectors, useUISelectors } from '@/hooks/useStoreSelectors';
import { DataSource } from '@/store/slices/dataSourcesSlice';

// This is a demo component to showcase how to use the store selectors
export default function DataSourcesDemo() {
  const { 
    dataSources, 
    loading, 
    errors, 
    fetchDataSources,
    createDataSource,
    updateDataSource,
    deleteDataSource,
    pullDataSource,
    pullingProgress
  } = useDataSourcesSelectors();
  
  const { addToast } = useUISelectors();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSource, setSelectedSource] = useState<DataSource | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    url: '',
    description: ''
  });
  
  // Fetch data sources on component mount
  useEffect(() => {
    fetchDataSources().catch(error => {
      console.error('Failed to fetch data sources:', error);
      addToast({
        title: 'Error',
        description: 'Failed to load data sources. Please try again.',
        variant: 'destructive'
      });
    });
  }, [fetchDataSources, addToast]);
  
  const handleCreateSource = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createDataSource(formData);
      setIsModalOpen(false);
      setFormData({ name: '', url: '', description: '' });
      addToast({
        title: 'Success',
        description: 'Data source created successfully',
        variant: 'success'
      });
    } catch (error: any) {
      addToast({
        title: 'Error',
        description: error.message || 'Failed to create data source',
        variant: 'destructive'
      });
    }
  };
  
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSource) return;
    
    try {
      await updateDataSource(selectedSource.id, formData);
      setIsModalOpen(false);
      setSelectedSource(null);
      setFormData({ name: '', url: '', description: '' });
      addToast({
        title: 'Success',
        description: 'Data source updated successfully',
        variant: 'success'
      });
    } catch (error: any) {
      addToast({
        title: 'Error',
        description: error.message || 'Failed to update data source',
        variant: 'destructive'
      });
    }
  };
  
  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this data source?')) return;
    
    try {
      await deleteDataSource(id);
      addToast({
        title: 'Success',
        description: 'Data source deleted successfully',
        variant: 'success'
      });
    } catch (error: any) {
      addToast({
        title: 'Error',
        description: error.message || 'Failed to delete data source',
        variant: 'destructive'
      });
    }
  };
  
  const handlePull = async (id: number) => {
    try {
      await pullDataSource(id);
      addToast({
        title: 'Success',
        description: 'Started pulling data from source',
        variant: 'success'
      });
    } catch (error: any) {
      addToast({
        title: 'Error',
        description: error.message || 'Failed to pull data from source',
        variant: 'destructive'
      });
    }
  };
  
  const openEditModal = (source: DataSource) => {
    setSelectedSource(source);
    setFormData({
      name: source.name,
      url: source.url,
      description: source.description || ''
    });
    setIsModalOpen(true);
  };
  
  const openCreateModal = () => {
    setSelectedSource(null);
    setFormData({ name: '', url: '', description: '' });
    setIsModalOpen(true);
  };
  
  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Data Sources</h1>
        <button 
          className="px-4 py-2 bg-blue-500 text-white rounded" 
          onClick={openCreateModal}
        >
          Add Source
        </button>
      </div>
      
      {errors && errors.dataSources && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {errors.dataSources.message}
        </div>
      )}
      
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200">
            <thead>
              <tr>
                <th className="px-4 py-2 border">Name</th>
                <th className="px-4 py-2 border">URL</th>
                <th className="px-4 py-2 border">Status</th>
                <th className="px-4 py-2 border">Last Scraped</th>
                <th className="px-4 py-2 border">Proposals</th>
                <th className="px-4 py-2 border">Actions</th>
              </tr>
            </thead>
            <tbody>
              {dataSources.map((source) => (
                <tr key={source.id}>
                  <td className="px-4 py-2 border">{source.name}</td>
                  <td className="px-4 py-2 border">
                    <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                      {source.url}
                    </a>
                  </td>
                  <td className="px-4 py-2 border">{source.status}</td>
                  <td className="px-4 py-2 border">{source.lastScraped || 'Never'}</td>
                  <td className="px-4 py-2 border">{source.proposalCount}</td>
                  <td className="px-4 py-2 border">
                    <div className="flex space-x-2">
                      <button 
                        className="px-2 py-1 bg-green-500 text-white text-sm rounded"
                        onClick={() => handlePull(source.id)}
                        disabled={pullingProgress[source.id]}
                      >
                        {pullingProgress[source.id] ? 'Pulling...' : 'Pull'}
                      </button>
                      <button 
                        className="px-2 py-1 bg-yellow-500 text-white text-sm rounded"
                        onClick={() => openEditModal(source)}
                      >
                        Edit
                      </button>
                      <button 
                        className="px-2 py-1 bg-red-500 text-white text-sm rounded"
                        onClick={() => handleDelete(source.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              
              {dataSources.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-4 text-center border">
                    No data sources found. Add a source to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      
      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">
              {selectedSource ? 'Edit Data Source' : 'Add Data Source'}
            </h2>
            
            <form onSubmit={selectedSource ? handleUpdate : handleCreateSource}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Name</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border rounded"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">URL</label>
                <input
                  type="url"
                  className="w-full px-3 py-2 border rounded"
                  value={formData.url}
                  onChange={(e) => setFormData({...formData, url: e.target.value})}
                  required
                />
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  className="w-full px-3 py-2 border rounded"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  rows={3}
                />
              </div>
              
              <div className="flex justify-end space-x-2">
                <button
                  type="button"
                  className="px-4 py-2 border rounded"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-500 text-white rounded"
                >
                  {selectedSource ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
} 