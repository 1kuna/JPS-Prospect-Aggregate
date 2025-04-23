import React, { useState, FormEvent } from 'react';
import {
  Input,
  Button,
  Textarea
} from '@/components';
import styles from './DataSourceForm.module.css';

// Updated form data structure
export interface DataSourceFormData {
  name: string;
  url: string;
  description?: string;
}

// Updated validation errors structure
interface FormErrors {
  name?: string;
  url?: string;
}

// Props remain the same
interface DataSourceFormProps {
  onSubmit: (data: DataSourceFormData) => void;
  initialData?: Partial<DataSourceFormData>;
  isSubmitting?: boolean;
}

export const DataSourceForm = ({
  onSubmit,
  initialData = { name: '', url: '', description: '' },
  isSubmitting = false,
}: DataSourceFormProps) => {
  const [formData, setFormData] = useState<DataSourceFormData>({
    name: initialData.name ?? '',
    url: initialData.url ?? '',
    description: initialData.description ?? '',
  });
  const [errors, setErrors] = useState<FormErrors>({});

  const validateForm = (): FormErrors => {
    const newErrors: FormErrors = {};
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required.';
    }
    if (!formData.url.trim()) {
      newErrors.url = 'URL is required.';
    } else {
      try {
        new URL(formData.url);
      } catch (_) {
        newErrors.url = 'Please enter a valid URL (e.g., http://example.com).';
      }
    }
    return newErrors;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prevData => ({
      ...prevData,
      [name]: value,
    }));
    if (errors[name as keyof FormErrors]) {
      setErrors(prevErrors => ({
        ...prevErrors,
        [name]: undefined,
      }));
    }
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const validationErrors = validateForm();
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length === 0) {
      onSubmit(formData);
    } else {
      console.log('Validation failed:', validationErrors);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.dataSourceForm}>
      <div className={styles.formField}>
        <label htmlFor="name" className={styles.label}>Data Source Name:</label>
        <Input
          id="name"
          name="name"
          type="text"
          value={formData.name}
          onChange={handleChange}
          placeholder="My Important Data"
          className={`${styles.input} ${errors.name ? styles.inputError : ''}`}
          aria-invalid={!!errors.name}
          aria-describedby={errors.name ? "name-error" : undefined}
        />
        {errors.name && <p id="name-error" className={styles.errorMessage}>{errors.name}</p>}
      </div>

      <div className={styles.formField}>
        <label htmlFor="url" className={styles.label}>Data Source URL:</label>
        <Input
          id="url"
          name="url"
          type="text"
          value={formData.url}
          onChange={handleChange}
          placeholder="http://example.com/datafeed"
          className={`${styles.input} ${errors.url ? styles.inputError : ''}`}
          aria-invalid={!!errors.url}
          aria-describedby={errors.url ? "url-error" : undefined}
        />
        {errors.url && <p id="url-error" className={styles.errorMessage}>{errors.url}</p>}
      </div>

      <div className={styles.formField}>
        <label htmlFor="description" className={styles.label}>Description: <span className={styles.optional}>(Optional)</span></label>
        <Textarea
          id="description"
          name="description"
          value={formData.description}
          onChange={handleChange}
          placeholder="Brief description of the data source..."
          className={styles.textarea}
          rows={3}
        />
      </div>

      <Button type="submit" disabled={isSubmitting} className={styles.submitButton}>
        {isSubmitting ? 'Saving...' : 'Save Data Source'}
      </Button>
    </form>
  );
}; 