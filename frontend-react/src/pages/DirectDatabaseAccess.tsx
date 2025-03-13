import { useState, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { PageLayout } from '@/components';
import { Button, Alert, AlertTitle, AlertDescription } from '@/components/ui';
import { Textarea } from '@/components/ui/textarea';
import { FormWrapper } from '@/components/forms/FormWrapper';
import * as z from 'zod';

// Create stable selectors
const selectExecuteQuery = (state: any) => state.executeQuery;
const selectQueryLoading = (state: any) => state.loading.query;
const selectQueryErrors = (state: any) => state.errors.query;

// Define the form schema
const formSchema = z.object({
  query: z.string().min(1, { message: 'Query is required' }),
});

export default function DirectDatabaseAccess() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  
  // Use individual selectors to prevent unnecessary re-renders
  const executeQuery = useStore(selectExecuteQuery);
  const loading = useStore(selectQueryLoading);
  const errors = useStore(selectQueryErrors);

  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuery(e.target.value);
  }, []);

  const handleExecuteQuery = useCallback(async () => {
    if (!query.trim()) return;
    
    try {
      const result = await executeQuery(query);
      setResults(result);
    } catch (error) {
      console.error('Error executing query:', error);
    }
  }, [query, executeQuery]);

  const handleClearResults = useCallback(() => {
    setResults(null);
  }, []);

  const handleSubmit = useCallback((data: { query: string }) => {
    executeQuery(data.query).then(setResults);
  }, [executeQuery]);

  return (
    <PageLayout title="Direct Database Access" isLoading={loading}>
      <div className="space-y-6">
        <Alert variant="warning">
          <AlertTitle>Warning: Advanced Feature</AlertTitle>
          <AlertDescription>
            This page allows direct SQL queries to the database. Use with caution as improper queries may damage your data.
            SELECT queries are recommended. Avoid INSERT, UPDATE, or DELETE operations unless you know what you're doing.
          </AlertDescription>
        </Alert>

        <FormWrapper
          schema={formSchema}
          defaultValues={{ query: '' }}
          onSubmit={handleSubmit}
          submitLabel="Execute Query"
        >
          <div className="space-y-4">
            <div>
              <label htmlFor="query" className="block text-sm font-medium mb-1">
                SQL Query
              </label>
              <Textarea
                id="query"
                value={query}
                onChange={handleQueryChange}
                placeholder="SELECT * FROM proposals LIMIT 10;"
                className="h-32 font-mono"
              />
            </div>
            
            <div className="flex gap-2">
              <Button onClick={handleExecuteQuery} disabled={!query.trim() || loading}>
                {loading ? 'Executing...' : 'Execute Query'}
              </Button>
              <Button variant="outline" onClick={handleClearResults} disabled={!results}>
                Clear Results
              </Button>
            </div>
          </div>
        </FormWrapper>

        {errors && (
          <Alert variant="destructive">
            <AlertTitle>Query Error</AlertTitle>
            <AlertDescription>{errors.message}</AlertDescription>
          </Alert>
        )}

        {results && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-4">Query Results</h3>
            
            {results.rowCount !== undefined && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                {results.rowCount} {results.rowCount === 1 ? 'row' : 'rows'} returned
              </p>
            )}
            
            {results.rows && results.rows.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      {Object.keys(results.rows[0]).map((key) => (
                        <th
                          key={key}
                          className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider"
                        >
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {results.rows.map((row: any, rowIndex: number) => (
                      <tr key={rowIndex}>
                        {Object.values(row).map((value: any, colIndex: number) => (
                          <td
                            key={colIndex}
                            className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400"
                          >
                            {value === null ? (
                              <span className="text-gray-400 dark:text-gray-600 italic">NULL</span>
                            ) : typeof value === 'object' ? (
                              JSON.stringify(value)
                            ) : (
                              String(value)
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                {results.command === 'SELECT' ? 'No rows returned' : `Query executed successfully: ${results.command}`}
              </p>
            )}
          </div>
        )}
      </div>
    </PageLayout>
  );
} 