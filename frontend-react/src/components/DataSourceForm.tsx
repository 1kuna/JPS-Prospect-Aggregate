import * as z from 'zod';
import { FormWrapper } from './forms/FormWrapper';
import {
  FormField,
  FormControl,
  FormDescription,
  FormItem,
  FormLabel,
  FormMessage,
  Input,
} from '@/components';

// Define the form schema with Zod
const formSchema = z.object({
  name: z.string().min(2, {
    message: 'Name must be at least 2 characters.',
  }),
  url: z.string().url({
    message: 'Please enter a valid URL.',
  }),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface DataSourceFormProps {
  initialData?: {
    id?: number;
    name: string;
    url: string;
    description?: string;
  };
  onSubmit: (data: FormValues) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
  error?: string | null;
  successMessage?: string | null;
}

export function DataSourceForm({
  initialData,
  onSubmit,
  onCancel,
  isSubmitting = false,
  error = null,
  successMessage = null,
}: DataSourceFormProps) {
  return (
    <FormWrapper
      schema={formSchema}
      defaultValues={initialData || {
        name: '',
        url: '',
        description: '',
      }}
      onSubmit={onSubmit}
      onCancel={onCancel}
      submitLabel={initialData ? 'Update' : 'Create'}
      isSubmitting={isSubmitting}
      error={error}
      successMessage={successMessage}
      title={initialData ? 'Edit Data Source' : 'Create Data Source'}
      description="Configure a data source for proposal aggregation."
    >
      <FormField
        name="name"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Name</FormLabel>
            <FormControl>
              <Input placeholder="Enter data source name" {...field} />
            </FormControl>
            <FormDescription>
              A descriptive name for the data source.
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        name="url"
        render={({ field }) => (
          <FormItem>
            <FormLabel>URL</FormLabel>
            <FormControl>
              <Input placeholder="https://example.com/api" {...field} />
            </FormControl>
            <FormDescription>
              The endpoint URL for the data source.
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        name="description"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Description (Optional)</FormLabel>
            <FormControl>
              <Input placeholder="Enter a description" {...field} />
            </FormControl>
            <FormDescription>
              A brief description of the data source.
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />
    </FormWrapper>
  );
} 