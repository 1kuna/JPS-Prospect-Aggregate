import React, { useState, useEffect } from 'react';
import axios from 'axios'; // Import axios
import { DataTable } from '@/components/data-display/DataTable';
import { DataSourceForm, DataSourceFormData } from '@/components/forms/DataSourceForm'; // Import type directly
import { columns } from './DataSourcesColumns';
import { PageLayout } from '@/components/layout/PageLayout';

/*
TODO:
- Remove dependency on Zod schema (commented out below).
- Update data fetching logic (replace commented out useFetch/useMutate).
- Potentially manage form submission state (isSubmitting).
- Integrate DataTable with actual fetched data.
- Ensure DataSourceForm's onSubmit prop is handled correctly.

// Zod schema for validating form input (might be defined in DataSourceForm component instead)
// export const dataSourceSchema = z.object({
//   name: z.string().min(1, 'Name is required'),
//   type: z.enum(['csv', 'database', 'api'], { required_error: 'Type is required' }),
//   // Add other fields as needed
// });

// export type DataSourceFormData = z.infer<typeof dataSourceSchema>;
*/

// Updated interface matching the backend GET /api/data-sources response structure
interface DataSourceApiResponse {
  id: number;
  name: string;
  url: string;
  description?: string | null;
  last_scraped?: string | null;
  proposalCount?: number;
  last_checked?: string | null;
  status?: string; // "working", "not_working", "unknown"
}

// Define the data structure expected by the POST /api/data-sources endpoint
// Based on DataSource model: name, url, description seem most likely
// POST data uses the same structure as the form data now
// type DataSourcePostData = DataSourceFormData; // Alias if needed, or just use DataSourceFormData directly

const DataSourcesPage = () => {
  // State holds the data matching the API response structure
  const [dataSources, setDataSources] = useState<DataSourceApiResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccessMessage, setSubmitSuccessMessage] = useState<string | null>(null);
  const [formKey, setFormKey] = useState<number>(0); // State for resetting the form

  const fetchDataSources = async () => {
    // Keep loading state specific to the table fetch
    setIsLoading(true);
    setError(null);
    try {
      // Use correct endpoint and expect { data: [...] } structure
      const response = await axios.get<{ data: DataSourceApiResponse[] }>('/api/data-sources'); 
      setDataSources(response.data.data); // Extract data from the nested structure
    } catch (err) {
      console.error('Error fetching data sources:', err);
      setError('Failed to load data sources. Please try again later.');
      setDataSources([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDataSources();
  }, []);

  // Handle form submission - now directly uses the validated form data
  const handleFormSubmit = async (formData: DataSourceFormData) => {
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccessMessage(null); // Clear previous success message

    // Remove the adaptation logic
    // const postData: DataSourcePostData = {
    //   name: formDataFromForm.name,
    //   url: formDataFromForm.connection_string || '', 
    //   description: `Source type: ${formDataFromForm.type}`
    // };

    // Remove validation for adapted data
    // if (!postData.url) { ... }

    try {
      // Send formData directly as it now matches the expected structure
      await axios.post('/api/data-sources', formData); 
      setSubmitSuccessMessage('Data source added successfully!'); // Set success message
      setFormKey(prevKey => prevKey + 1); // Change key to reset form
      fetchDataSources();
      // TODO: Consider resetting the form after successful submission
    } catch (err: any) {
      console.error('Error submitting form:', err);
      const message = err.response?.data?.message || 'Failed to add data source. Please check your input and try again.';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageLayout title="Data Sources">
      <div className="space-y-6">
        <section>
          <h2>Add New Data Source</h2>
          {/* Remove the note about data adaptation */}
          <DataSourceForm 
            key={formKey} // Add key prop for resetting form
            onSubmit={handleFormSubmit} 
            isSubmitting={isSubmitting}
          />
          {/* Display Success or Error Messages */}
          {submitSuccessMessage && <p className="text-green-600 mt-2">{submitSuccessMessage}</p>}
          {submitError && <p className="text-red-500 mt-2">{submitError}</p>}
        </section>

        <section>
          <h2>Existing Data Sources</h2>
          {isLoading && <p>Loading data sources...</p>}
          {error && <p className="text-red-500">{error}</p>}
          {!isLoading && !error && (
            /* Ensure columns in DataSourcesColumns.ts match DataSourceApiResponse */
            <DataTable columns={columns} data={dataSources} /> 
          )}
        </section>

        {/* Remove the refactoring note if no longer needed */}
        {/* <p>This page needs refactoring to remove Zod, update data fetching, and integrate refactored form/table components.</p> */}
      </div>
    </PageLayout>
  );
};

export default DataSourcesPage;