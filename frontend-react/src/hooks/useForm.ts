import { useState, useCallback } from 'react';
import { useForm as useReactHookForm, UseFormProps, FieldValues, UseFormReturn, SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from '@/hooks/use-toast';

export interface UseFormOptions<TFormValues extends FieldValues> extends UseFormProps<TFormValues> {
  /**
   * Zod schema for validation
   */
  schema?: z.ZodType<TFormValues>;
  
  /**
   * Initial values for the form
   */
  initialValues?: Partial<TFormValues>;
  
  /**
   * Callback to run when the form is successfully submitted
   */
  onSubmit: SubmitHandler<TFormValues>;
  
  /**
   * Function to execute the submission (e.g., API call)
   */
  submitHandler?: (values: TFormValues) => Promise<any>;
  
  /**
   * Whether to show a success toast on successful submission
   */
  showSuccessToast?: boolean;
  
  /**
   * Message to show in the success toast
   */
  successMessage?: string;
  
  /**
   * Whether to show an error toast on failed submission
   */
  showErrorToast?: boolean;
  
  /**
   * Message to show in the error toast
   */
  errorMessage?: string;
  
  /**
   * Callback to run after successful submission
   */
  onSuccess?: (data: any) => void;
  
  /**
   * Callback to run after failed submission
   */
  onError?: (error: any) => void;
  
  /**
   * Whether to reset the form after successful submission
   */
  resetOnSuccess?: boolean;
}

export interface UseFormReturn<TFormValues extends FieldValues> extends UseFormReturn<TFormValues> {
  /**
   * Whether the form is submitting
   */
  isSubmitting: boolean;
  
  /**
   * Whether the form was successfully submitted
   */
  isSubmitSuccessful: boolean;
  
  /**
   * Any error that occurred during submission
   */
  submitError: Error | null;
  
  /**
   * Function to handle form submission
   */
  handleSubmit: (e?: React.BaseSyntheticEvent) => Promise<void>;
  
  /**
   * Function to reset the submission state
   */
  resetSubmitState: () => void;
}

/**
 * Enhanced form hook that combines React Hook Form with submission handling,
 * toast notifications, and Zod validation
 */
export function useForm<TFormValues extends FieldValues>({
  schema,
  initialValues,
  onSubmit,
  submitHandler,
  showSuccessToast = true,
  successMessage = 'Form submitted successfully',
  showErrorToast = true,
  errorMessage = 'Form submission failed',
  onSuccess,
  onError,
  resetOnSuccess = false,
  ...formOptions
}: UseFormOptions<TFormValues>): UseFormReturn<TFormValues> {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitSuccessful, setIsSubmitSuccessful] = useState(false);
  const [submitError, setSubmitError] = useState<Error | null>(null);
  
  // Create form with React Hook Form
  const form = useReactHookForm<TFormValues>({
    ...(schema ? { resolver: zodResolver(schema) } : {}),
    defaultValues: initialValues as TFormValues,
    ...formOptions
  });
  
  // Reset submission state
  const resetSubmitState = useCallback(() => {
    setIsSubmitting(false);
    setIsSubmitSuccessful(false);
    setSubmitError(null);
  }, []);
  
  // Handle form submission
  const handleSubmit = useCallback(
    async (e?: React.BaseSyntheticEvent) => {
      // Prevent default form submission
      e?.preventDefault();
      
      // Reset submission state
      resetSubmitState();
      
      // Start submission
      setIsSubmitting(true);
      
      try {
        // Get form values
        const values = await form.handleSubmit(async (data) => {
          // If submitHandler is provided, execute it
          if (submitHandler) {
            return await submitHandler(data);
          }
          return data;
        })(e);
        
        // If values is undefined, form validation failed
        if (!values) {
          setIsSubmitting(false);
          return;
        }
        
        // Call onSubmit callback
        await onSubmit(values as TFormValues);
        
        // Set success state
        setIsSubmitSuccessful(true);
        
        // Show success toast
        if (showSuccessToast) {
          toast.success({
            title: 'Success',
            description: successMessage
          });
        }
        
        // Call onSuccess callback
        if (onSuccess) {
          onSuccess(values);
        }
        
        // Reset form if needed
        if (resetOnSuccess) {
          form.reset();
        }
      } catch (error) {
        // Set error state
        const errorObj = error instanceof Error ? error : new Error(String(error));
        setSubmitError(errorObj);
        
        // Show error toast
        if (showErrorToast) {
          toast.error({
            title: 'Error',
            description: errorObj.message || errorMessage
          });
        }
        
        // Call onError callback
        if (onError) {
          onError(error);
        }
      } finally {
        // End submission
        setIsSubmitting(false);
      }
    },
    [
      form,
      onSubmit,
      submitHandler,
      showSuccessToast,
      successMessage,
      showErrorToast,
      errorMessage,
      onSuccess,
      onError,
      resetOnSuccess,
      resetSubmitState
    ]
  );
  
  return {
    ...form,
    isSubmitting,
    isSubmitSuccessful,
    submitError,
    handleSubmit,
    resetSubmitState
  };
}

export default useForm; 