import { useState } from 'react';
import { DataPageLayout } from '@/components/layout';
import { useExecuteQuery } from '@/hooks/api/useDatabase';
import styles from './DirectDatabaseAccess.module.css';
import { DatabaseOperations } from '@/components/DatabaseOperations';
import { Button } from '@/components/ui';

export default function DirectDatabaseAccess() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  const { mutate: executeQuery, isPending: isLoading } = useExecuteQuery();

  const handleExecute = () => {
    if (!query.trim()) {
      setResults('Please enter a query.');
      return;
    }
    executeQuery({ query: query.trim() }, {
      onSuccess: (data: any) => {
        setResults(JSON.stringify(data, null, 2));
        setError(null);
      },
      onError: (error: any) => {
        setResults(null);
        setError(error.message || 'Query execution failed');
      }
    });
  };

  const handleClear = () => {
    setQuery('');
    setResults(null);
    setError(null);
  };

  return (
    <DataPageLayout
      title="Direct Database Access"
      subtitle="Execute SQL queries directly on the database"
      data={results}
      loading={isLoading}
      error={error as Error | null}
      renderHeader={() => (
        <div role="alert" className={styles.warningBox}>
          <h4 className={styles.warningTitle}>Warning: Advanced Feature</h4>
          <p>
            This page allows direct SQL queries to the database. Use with caution as improper queries may damage your data.
            SELECT queries are recommended. Avoid INSERT, UPDATE, or DELETE operations unless you know what you're doing.
          </p>
        </div>
      )}
    >
      <div className={styles.contentWrapper}>
        <div>
          <label htmlFor="query" className={styles.queryLabel}>
            SQL Query
          </label>
          <textarea
            id="query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="SELECT * FROM proposals LIMIT 10;"
            className={styles.queryTextarea}
          />
        </div>
        
        <div className={styles.buttonGroup}>
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
          <div className={styles.resultsWrapper}>
            <h3 className={styles.resultsTitle}>Results</h3>
            <pre className={styles.resultsPre}>
              {results}
            </pre>
          </div>
        )}

        <div className={styles.operationsWrapper}>
          <DatabaseOperations />
        </div>
      </div>
    </DataPageLayout>
  );
} 