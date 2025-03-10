# JPS Prospect Aggregate Frontend

This is the frontend for the JPS Prospect Aggregate application, built with React, Vite, shadcn/ui, TanStack Table, and Zustand.

## Features

- Modern React application with TypeScript
- Fast development and build with Vite
- Beautiful UI components with shadcn/ui
- Powerful data tables with TanStack Table
- Simple state management with Zustand
- Form handling with React Hook Form and Zod validation
- Optimized for performance with code splitting and lazy loading

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

1. Clone the repository
2. Navigate to the frontend directory:

```bash
cd frontend-react
```

3. Install dependencies:

```bash
npm install
```

4. Start the development server:

```bash
npm run dev
```

5. Build for production:

```bash
npm run build
```

## Project Structure

```
frontend-react/
├── public/              # Static assets
├── src/
│   ├── assets/          # Images, fonts, etc.
│   ├── components/      # Reusable components
│   │   └── ui/          # shadcn/ui components
│   ├── context/         # React context providers
│   ├── hooks/           # Custom React hooks
│   ├── lib/             # Utility functions
│   ├── pages/           # Page components
│   ├── store/           # Zustand store
│   ├── utils/           # Utility functions
│   ├── App.tsx          # Main application component
│   ├── main.tsx         # Application entry point
│   └── index.css        # Global styles
├── .gitignore
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## Key Technologies

- [React](https://reactjs.org/)
- [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vitejs.dev/)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Table](https://tanstack.com/table/v8)
- [Zustand](https://zustand-demo.pmnd.rs/)
- [React Router](https://reactrouter.com/)
- [React Hook Form](https://react-hook-form.com/)
- [Zod](https://zod.dev/)
- [Tailwind CSS](https://tailwindcss.com/)

## Development Guidelines

### Component Structure

- Use functional components with hooks
- Implement lazy loading for page components
- Use TypeScript interfaces for props and state

### State Management

- Use Zustand for global state
- Use React context for UI state
- Use local state for component-specific state

### Styling

- Use Tailwind CSS for styling
- Use shadcn/ui components for UI elements
- Follow the design system for consistency

### Error Handling

- Use error boundaries for component-level errors
- Implement proper error handling for API calls
- Display user-friendly error messages

### Performance

- Use React.memo for expensive components
- Implement virtualization for large lists
- Use code splitting and lazy loading

## API Integration

The frontend communicates with the backend API using Axios. API functions are defined in `src/store/api.ts`.

## Testing

Run tests with:

```bash
npm test
```

## Deployment

The application is built and deployed using the `rebuild_frontend.py` script, which:

1. Builds the React application
2. Copies the build files to the Flask static directory
3. Updates the Flask server to serve the React build

## License

This project is proprietary and confidential.
