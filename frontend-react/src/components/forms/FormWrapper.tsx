import React from 'react';
import { useForm, FormProvider, FieldValues, DefaultValues, SubmitHandler, UseFormProps } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';

interface FormWrapperProps<T extends FieldValues> {
  title?: string;
  description?: string;
  schema: z.ZodType<T>;
  defaultValues: DefaultValues<T>;
  onSubmit: SubmitHandler<T>;
  onCancel?: () => void;
  submitLabel?: string;
  cancelLabel?: string;
  isSubmitting?: boolean;
  error?: string | null;
  successMessage?: string | null;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  formOptions?: Omit<UseFormProps<T>, 'defaultValues' | 'resolver'>;
  cardless?: boolean;
}

export function FormWrapper<T extends FieldValues>({
  title,
  description,
  schema,
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = 'Submit',
  cancelLabel = 'Cancel',
  isSubmitting = false,
  error = null,
  successMessage = null,
  children,
  footer,
  className,
  formOptions,
  cardless = false,
}: FormWrapperProps<T>) {
  const form = useForm<T>({
    resolver: zodResolver(schema),
    defaultValues,
    ...formOptions,
  });

  const handleSubmit = form.handleSubmit(onSubmit);

  const formContent = (
    <>
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {successMessage && (
        <Alert variant="default" className="mb-6 bg-green-50 border-green-200 text-green-800">
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>{successMessage}</AlertDescription>
        </Alert>
      )}

      <FormProvider {...form}>
        <form onSubmit={handleSubmit} className="space-y-6">
          {children}

          <div className="flex justify-end space-x-4">
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                {cancelLabel}
              </Button>
            )}
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Submitting...' : submitLabel}
            </Button>
          </div>
        </form>
      </FormProvider>
    </>
  );

  if (cardless) {
    return <div className={className}>{formContent}</div>;
  }

  return (
    <Card className={className}>
      {(title || description) && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
      )}
      <CardContent>{formContent}</CardContent>
      {footer && <CardFooter>{footer}</CardFooter>}
    </Card>
  );
} 