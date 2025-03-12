# Project Structure and Organization

This document describes the organization, naming conventions, and code structure of the JPS-Prospect-Aggregate project.

## Table of Contents

- [Directory Structure](#directory-structure)
- [Key Files](#key-files)
- [Naming Conventions](#naming-conventions)
  - [Files](#files)
  - [Directories](#directories)
  - [Component Naming](#component-naming)
  - [CSS Class Naming](#css-class-naming)
  - [Variable Naming](#variable-naming)
  - [Interface and Type Naming](#interface-and-type-naming)
- [Code Organization](#code-organization)
  - [Component Organization](#component-organization)
  - [Hook Organization](#hook-organization)
  - [State Management](#state-management)
  - [Page Organization](#page-organization)
  - [Import Organization](#import-organization)
  - [Code Splitting](#code-splitting)
  - [Best Practices](#best-practices)

## Directory Structure

```
JPS-Prospect-Aggregate/
├── data/                  # Data files and database
├── docs/                  # Documentation
│   ├── api.md             # API documentation
│   ├── backend-architecture.md # Backend architecture documentation
│   ├── components.md      # Component documentation
│   ├── patterns.md        # Pattern documentation
│   └── project-structure.md # Project structure documentation
├── frontend-react/        # React frontend
│   ├── audit/             # Audit and implementation plans
│   ├── public/            # Public assets
│   └── src/               # Source code
│       ├── components/    # React components
│       │   ├── data-display/  # Data display components
│       │   ├── forms/         # Form components
│       │   ├── layout/        # Layout components
│       │   └── ui/            # UI components
│       ├── hooks/         # Custom React hooks
│       ├── lib/           # Utility functions
│       ├── pages/         # Page components
│       └── store/         # State management
├── logs/                  # Log files
├── scripts/               # Utility scripts
├── src/                   # Backend source code
└── temp/                  # Temporary files
```

## Key Files

- `server.py`: Main backend server
- `start_all.py`: Script to start all services
- `frontend-react/src/index.tsx`: Entry point for the React application
- `.env`: Environment variables
- `requirements.txt`: Python dependencies

## Naming Conventions

### Files

- **React Components**: Use PascalCase for component files and match the component name with the file name. Include the file extension `.tsx` for TypeScript components.

  Examples:
  - `Button.tsx`
  - `DataTable.tsx`
  - `PageLayout.tsx`

- **Hooks**: Use camelCase with 'use' prefix and include the file extension `.ts` for TypeScript hooks.

  Examples:
  - `useDataFetching.ts`
  - `useForm.ts`
  - `useLocalStorage.ts`

- **Utilities**: Use camelCase and name should describe the function's purpose. Include the file extension `.ts` for TypeScript utilities.

  Examples:
  - `formatDate.ts`
  - `validateEmail.ts`
  - `calculateTotal.ts`

- **Constants**: Use UPPER_SNAKE_CASE for constant files and include the file extension `.ts` for TypeScript constants.

  Examples:
  - `API_ENDPOINTS.ts`
  - `COLOR_CONSTANTS.ts`
  - `FORM_VALIDATION_MESSAGES.ts`

### Directories

- Use **kebab-case** for directory names
- Group related components in descriptive directories

Examples:
- `data-display/`
- `form-controls/`
- `user-management/`

### Component Naming

#### Base Components

- Use clear, descriptive names
- Avoid abbreviations unless widely understood
- Prefix with purpose if part of a group

Examples:
- `Button` (not `Btn`)
- `FormInput` (not `Input` if specifically for forms)
- `DataTable` (not just `Table` if it has data-specific features)

#### Component Variants

- Use descriptive suffixes for variants
- Keep the base component name as a prefix

Examples:
- `ButtonPrimary`, `ButtonSecondary`
- `CardBasic`, `CardInteractive`
- `TableSortable`, `TableFilterable`

### CSS Class Naming

- Use **kebab-case** for CSS class names
- Follow a component-element-modifier pattern

Examples:
- `card-header`
- `button-primary`
- `form-input-error`

### Variable Naming

- Use **camelCase** for variables and function names
- Use descriptive names that indicate purpose
- Boolean variables should use prefixes like `is`, `has`, or `should`

Examples:
- `userData` (not `data`)
- `isLoading` (not `loading`)
- `handleSubmit` (not `submit`)

### Interface and Type Naming

- Use **PascalCase** for interfaces and types
- Interfaces for props should end with `Props`
- Interfaces for state should end with `State`

Examples:
- `ButtonProps`
- `UserData`
- `FormState`

## Code Organization

### Component Organization

#### Directory Structure

Components are organized by category:

```
components/
├── data-display/    # Components for displaying data (tables, cards, etc.)
├── forms/           # Form-related components
├── layout/          # Layout components (page layouts, containers, etc.)
├── ui/              # Basic UI components (buttons, inputs, etc.)
└── index.ts         # Re-exports for easier imports
```

#### Component File Structure

Each component file follows a consistent structure:

1. Imports
2. Types/Interfaces
3. Component definition
4. Exports

Example:
```tsx
// 1. Imports
import React from 'react';
import { Button } from '@/components/ui/button';

// 2. Types/Interfaces
interface CardProps {
  title: string;
  children: React.ReactNode;
}

// 3. Component definition
export function Card({ title, children }: CardProps) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <div>{children}</div>
    </div>
  );
}

// 4. Exports (if additional exports are needed)
export const CardTitle = ({ children }: { children: React.ReactNode }) => (
  <h3>{children}</h3>
);
```

### Hook Organization

Hooks are organized in a dedicated `hooks` directory:

```
hooks/
├── useDataFetching.ts
├── useForm.ts
├── useLocalStorage.ts
└── index.ts         # Re-exports for easier imports
```

### State Management

State management is centralized in the `store` directory:

```
store/
├── api.ts           # API functions
├── slices/          # State slices
├── types.ts         # Type definitions
└── index.ts         # Store configuration and exports
```

### Page Organization

Pages are organized by feature or route:

```
pages/
├── dashboard/
│   ├── components/  # Page-specific components
│   └── index.tsx    # Main page component
├── users/
│   ├── components/  # Page-specific components
│   └── index.tsx    # Main page component
└── index.tsx        # Entry point
```

### Import Organization

Imports are organized in the following order:

1. React and external libraries
2. Internal components and hooks
3. Types and interfaces
4. Assets and styles

Example:
```tsx
// 1. React and external libraries
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// 2. Internal components and hooks
import { Button } from '@/components/ui/button';
import { useDataFetching } from '@/hooks';

// 3. Types and interfaces
import type { User } from '@/types';

// 4. Assets and styles
import './styles.css';
```

### Code Splitting

Code splitting is used to reduce bundle size:

- Dynamic imports for large components
- Lazy loading for routes
- Separate chunks for vendor code

### Best Practices

- Keep components small and focused on a single responsibility
- Extract reusable logic into custom hooks
- Use TypeScript interfaces for component props
- Avoid deeply nested component hierarchies
- Use index files to simplify imports
- Follow consistent formatting and structure
- Provide explicit type information
- Include clear examples
- Avoid ambiguous language
- Use descriptive headings and subheadings

> **Note**: For detailed information about the backend architecture, including the Flask application, database models, API endpoints, background tasks, and data scrapers, please refer to the [Backend Architecture](backend-architecture.md) documentation.