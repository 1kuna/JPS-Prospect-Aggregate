import React, { ReactNode } from 'react';
import { cn } from '@/lib/utils';

// --- Card Component --- //

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', padding = 'md', children, ...props }, ref) => {
    const variantClasses = {
      default: 'bg-card text-card-foreground',
      outline: 'border border-gray-200 bg-transparent',
      elevated: 'bg-card text-card-foreground shadow-lg',
    };

    const paddingClasses = {
      none: 'p-0',
      sm: 'p-3',
      md: 'p-5',
      lg: 'p-8',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg',
          variantClasses[variant],
          paddingClasses[padding],
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// --- Card Header --- //

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 pb-4', className)}
    {...props}
  />
));

CardHeader.displayName = 'CardHeader';

// --- Card Title --- //

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn('text-xl font-semibold leading-none tracking-tight', className)}
    {...props}
  />
));

CardTitle.displayName = 'CardTitle';

// --- Card Description --- //

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-muted-foreground', className)}
    {...props}
  />
));

CardDescription.displayName = 'CardDescription';

// --- Card Content --- //

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('', className)} {...props} />
));

CardContent.displayName = 'CardContent';

// --- Card Footer --- //

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center pt-4', className)}
    {...props}
  />
));

CardFooter.displayName = 'CardFooter';

// --- Page Container --- //

interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  paddingX?: 'none' | 'sm' | 'md' | 'lg';
  paddingY?: 'none' | 'sm' | 'md' | 'lg';
  centered?: boolean;
}

const PageContainer = ({
  children,
  className,
  maxWidth = 'lg',
  paddingX = 'md',
  paddingY = 'md',
  centered = false,
  ...props
}: PageContainerProps) => {
  const maxWidthClasses = {
    xs: 'max-w-xs',
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    full: 'max-w-full',
  };

  const paddingXClasses = {
    none: 'px-0',
    sm: 'px-4',
    md: 'px-6',
    lg: 'px-8',
  };

  const paddingYClasses = {
    none: 'py-0',
    sm: 'py-4',
    md: 'py-6',
    lg: 'py-8',
  };

  return (
    <div
      className={cn(
        'w-full',
        maxWidthClasses[maxWidth],
        paddingXClasses[paddingX],
        paddingYClasses[paddingY],
        centered && 'mx-auto',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

// --- Section Container --- //

interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  backgroundVariant?: 'default' | 'primary' | 'secondary' | 'muted';
  paddingY?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
}

const Section = ({
  children,
  className,
  backgroundVariant = 'default',
  paddingY = 'md',
  ...props
}: SectionProps) => {
  const backgroundClasses = {
    default: 'bg-background',
    primary: 'bg-primary/10',
    secondary: 'bg-secondary/10',
    muted: 'bg-muted',
  };

  const paddingYClasses = {
    none: 'py-0',
    sm: 'py-4',
    md: 'py-8',
    lg: 'py-12',
    xl: 'py-16',
  };

  return (
    <section
      className={cn(
        backgroundClasses[backgroundVariant],
        paddingYClasses[paddingY],
        className
      )}
      {...props}
    >
      {children}
    </section>
  );
};

// --- Grid Container --- //

interface GridProps extends React.HTMLAttributes<HTMLDivElement> {
  columns?: 1 | 2 | 3 | 4 | 5 | 6;
  gap?: 'none' | 'sm' | 'md' | 'lg';
  responsive?: boolean;
}

const Grid = ({
  children,
  className,
  columns = 3,
  gap = 'md',
  responsive = true,
  ...props
}: GridProps) => {
  const columnsClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6',
  };

  const gapClasses = {
    none: 'gap-0',
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
  };

  // Responsive columns
  const responsiveClasses = responsive
    ? 'grid-cols-1 sm:grid-cols-2 md:' + columnsClasses[columns]
    : columnsClasses[columns];

  return (
    <div
      className={cn(
        'grid',
        responsive ? responsiveClasses : columnsClasses[columns],
        gapClasses[gap],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

// --- Flex Container --- //

interface FlexProps extends React.HTMLAttributes<HTMLDivElement> {
  direction?: 'row' | 'col';
  justify?: 'start' | 'end' | 'center' | 'between' | 'around' | 'evenly';
  align?: 'start' | 'end' | 'center' | 'baseline' | 'stretch';
  gap?: 'none' | 'sm' | 'md' | 'lg';
  wrap?: boolean;
}

const Flex = ({
  children,
  className,
  direction = 'row',
  justify = 'start',
  align = 'start',
  gap = 'md',
  wrap = false,
  ...props
}: FlexProps) => {
  const directionClasses = {
    row: 'flex-row',
    col: 'flex-col',
  };

  const justifyClasses = {
    start: 'justify-start',
    end: 'justify-end',
    center: 'justify-center',
    between: 'justify-between',
    around: 'justify-around',
    evenly: 'justify-evenly',
  };

  const alignClasses = {
    start: 'items-start',
    end: 'items-end',
    center: 'items-center',
    baseline: 'items-baseline',
    stretch: 'items-stretch',
  };

  const gapClasses = {
    none: 'gap-0',
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
  };

  return (
    <div
      className={cn(
        'flex',
        directionClasses[direction],
        justifyClasses[justify],
        alignClasses[align],
        gapClasses[gap],
        wrap && 'flex-wrap',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  PageContainer,
  Section,
  Grid,
  Flex,
}; 