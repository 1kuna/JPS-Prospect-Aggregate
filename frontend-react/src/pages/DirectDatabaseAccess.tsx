import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { useDatabase } from '@/hooks/api/useDatabase';
import { toast } from '@/hooks/use-toast';

export default function DirectDatabaseAccess() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  
  const { mutate: executeQuery, isLoading } = useDatabase.useExecuteQuery();

  const handleExecute = () => {
    if (!query.trim()) return;

    executeQuery({ query: query.trim() }, {
      onSuccess: (data) => {
        setResults(data);
        toast.success({ title: 'Success', description: 'Query executed successfully' });
      },
      onError: (error) => {
        toast.error({ title: 'Error', description: error.message });
      }
    });
  };

  const handleClear = () => {
    setQuery('');
    setResults(null);
  };

  return (
    <DataPageLayout
      title="Direct Database Access"
      subtitle="Execute SQL queries directly on the database"
      data={results}
      loading={isLoading}
      renderHeader={() => (
        <Alert variant="warning">
          <AlertTitle>Warning: Advanced Feature</AlertTitle>
          <AlertDescription>
            This page allows direct SQL queries to the database. Use with caution as improper queries may damage your data.
            SELECT queries are recommended. Avoid INSERT, UPDATE, or DELETE operations unless you know what you're doing.
          </AlertDescription>
        </Alert>
      )}
      renderContent={() => (
        <div className="space-y-4">
          <div>
            <label htmlFor="query" className="block text-sm font-medium mb-1">
              SQL Query
            </label>
            <Textarea
              id="query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="SELECT * FROM proposals LIMIT 10;"
              className="h-32 font-mono"
            />
          </div>
          
          <div className="flex gap-2">
            <Button
              onClick={handleExecute}
              disabled={!query.trim() || isLoading}
            >
              {isLoading ? 'Executing...' : 'Execute Query'}
            </Button>
            <Button
              variant="outline"
              onClick={handleClear}
              disabled={!query && !results}
            >
              Clear
            </Button>
          </div>

          {results && (
            <div className="mt-4">
              <h3 className="text-lg font-semibold mb-2">Results</h3>
              <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-96">
                {JSON.stringify(results, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    />
  );
} 