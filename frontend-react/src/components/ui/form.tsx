import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"
import { Slot } from "@radix-ui/react-slot"
import {
  Controller,
  ControllerProps,
  FieldPath,
  FieldValues,
  FormProvider,
  useFormContext,
  UseFormReturn,
  SubmitHandler,
  DefaultValues,
  SubmitErrorHandler,
} from "react-hook-form"
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from './button'

import { cn } from "../../lib/utils"
import { Label } from "./label"

const Form = FormProvider

type FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> = {
  name: TName
}

const FormFieldContext = React.createContext<FormFieldContextValue>(
  {} as FormFieldContextValue
)

const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({
  ...props
}: ControllerProps<TFieldValues, TName>) => {
  return (
    <FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  )
}

const useFormField = () => {
  const fieldContext = React.useContext(FormFieldContext)
  const itemContext = React.useContext(FormItemContext)
  const { getFieldState, formState } = useFormContext()

  const fieldState = getFieldState(fieldContext.name, formState)

  if (!fieldContext) {
    throw new Error("useFormField should be used within <FormField>")
  }

  const { id } = itemContext

  return {
    id,
    name: fieldContext.name,
    formItemId: `${id}-form-item`,
    formDescriptionId: `${id}-form-item-description`,
    formMessageId: `${id}-form-item-message`,
    ...fieldState,
  }
}

type FormItemContextValue = {
  id: string
}

const FormItemContext = React.createContext<FormItemContextValue>(
  {} as FormItemContextValue
)

const FormItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  const id = React.useId()

  return (
    <FormItemContext.Provider value={{ id }}>
      <div ref={ref} className={cn("space-y-2", className)} {...props} />
    </FormItemContext.Provider>
  )
})
FormItem.displayName = "FormItem"

const FormLabel = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => {
  const { error, formItemId } = useFormField()

  return (
    <Label
      ref={ref}
      className={cn(error && "text-destructive", className)}
      htmlFor={formItemId}
      {...props}
    />
  )
})
FormLabel.displayName = "FormLabel"

const FormControl = React.forwardRef<
  React.ElementRef<typeof Slot>,
  React.ComponentPropsWithoutRef<typeof Slot>
>(({ ...props }, ref) => {
  const { error, formItemId, formDescriptionId, formMessageId } = useFormField()

  return (
    <Slot
      ref={ref}
      id={formItemId}
      aria-describedby={
        !error
          ? `${formDescriptionId}`
          : `${formDescriptionId} ${formMessageId}`
      }
      aria-invalid={!!error}
      {...props}
    />
  )
})
FormControl.displayName = "FormControl"

const FormDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => {
  const { formDescriptionId } = useFormField()

  return (
    <p
      ref={ref}
      id={formDescriptionId}
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
})
FormDescription.displayName = "FormDescription"

const FormMessage = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => {
  const { error, formMessageId } = useFormField()
  const body = error ? String(error?.message) : children

  if (!body) {
    return null
  }

  return (
    <p
      ref={ref}
      id={formMessageId}
      className={cn("text-sm font-medium text-destructive", className)}
      {...props}
    >
      {body}
    </p>
  )
})
FormMessage.displayName = "FormMessage"

interface FormProps<TFormValues extends FieldValues = FieldValues> {
  /**
   * Default values for form fields
   */
  defaultValues?: DefaultValues<TFormValues>
  
  /**
   * Form children - typically FormField components
   */
  children: React.ReactNode
  
  /**
   * Handler called on successful form submission
   */
  onSubmit: SubmitHandler<TFormValues>
  
  /**
   * Optional error handler for form submission
   */
  onError?: SubmitErrorHandler<TFormValues>
  
  /**
   * Optional Zod schema for validation
   */
  schema?: z.ZodType<TFormValues>
  
  /**
   * Additional form attributes
   */
  formProps?: React.HTMLAttributes<HTMLFormElement>
  
  /**
   * Optional form ID
   */
  id?: string
  
  /**
   * Optional submit button text
   */
  submitText?: string
  
  /**
   * Optional cancel handler
   */
  onCancel?: () => void
  
  /**
   * Optional cancel button text
   */
  cancelText?: string
  
  /**
   * Whether the form is currently submitting
   */
  isSubmitting?: boolean
  
  /**
   * Form hook options
   */
  formOptions?: {
    mode?: "onBlur" | "onChange" | "onSubmit" | "onTouched" | "all"
    reValidateMode?: "onBlur" | "onChange" | "onSubmit"
    shouldUnregister?: boolean
  }
  
  /**
   * Whether the form should render form actions
   */
  showActions?: boolean
}

/**
 * Form wrapper with React Hook Form integration and Zod validation
 */
export function Form<TFormValues extends FieldValues>({
  defaultValues,
  children,
  onSubmit,
  onError,
  schema,
  formProps,
  id,
  submitText = 'Submit',
  onCancel,
  cancelText = 'Cancel',
  isSubmitting = false,
  formOptions = { mode: 'onBlur' },
  showActions = true
}: FormProps<TFormValues>) {
  // Initialize the form with optional schema validation
  const methods = useFormContext<TFormValues>() || 
    useForm<TFormValues>({
      defaultValues,
      resolver: schema ? zodResolver(schema) : undefined,
      ...formOptions
    });
  
  // Handle form submission
  const handleSubmit = methods.handleSubmit(onSubmit, onError);
  
  return (
    <FormProvider {...methods}>
      <form 
        id={id} 
        onSubmit={handleSubmit} 
        className="space-y-4" 
        {...formProps}
      >
        {children}
        
        {showActions && (
          <FormActions 
            submitText={submitText}
            cancelText={cancelText}
            onCancel={onCancel}
            isSubmitting={isSubmitting}
          />
        )}
      </form>
    </FormProvider>
  );
}

interface FormActionsProps {
  submitText?: string
  cancelText?: string
  onCancel?: () => void
  isSubmitting?: boolean
  align?: 'left' | 'center' | 'right'
}

export function FormActions({
  submitText = 'Submit',
  cancelText = 'Cancel',
  onCancel,
  isSubmitting = false,
  align = 'right'
}: FormActionsProps) {
  const alignClass = {
    left: 'justify-start',
    center: 'justify-center',
    right: 'justify-end',
  }[align];
  
  return (
    <div className={`flex gap-2 pt-2 ${alignClass}`}>
      {onCancel && (
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          {cancelText}
        </Button>
      )}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : submitText}
      </Button>
    </div>
  );
}

export {
  useFormField,
  Form,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
  FormField,
  FormProvider
} 