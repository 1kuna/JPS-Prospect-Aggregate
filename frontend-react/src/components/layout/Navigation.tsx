import { Link, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { useAuth } from '../AuthProvider';
import { useSignOut, useIsAdmin } from '../../hooks/api';
import { Button } from '../ui/button';
import { ThemeToggle } from '../ui/theme-toggle';
import { useError } from '@/hooks/useError';

export function Navigation() {
  const location = useLocation();
  const { user } = useAuth();
  const isAdmin = useIsAdmin();
  const signOutMutation = useSignOut();
  const { handleError } = useError();
  
  const navItems = [
    { path: '/', label: 'Dashboard' },
    ...(isAdmin ? [
      { path: '/advanced', label: 'Advanced' },
      { path: '/admin', label: 'Admin' }
    ] : []),
  ];

  const handleSignOut = async () => {
    try {
      await signOutMutation.mutateAsync();
    } catch (error) {
      handleError(error, {
        context: { operation: 'signOut' },
        fallbackMessage: 'Failed to sign out'
      });
    }
  };
  
  return (
    <nav className="bg-background shadow-sm border-b">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-xl font-semibold">JPS Prospect Aggregate</h1>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium",
                    location.pathname === item.path
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
          
          {/* User menu */}
          <div className="flex items-center space-x-3">
            {user && (
              <>
                <div className="text-sm">
                  Welcome, <span className="font-medium">{user.first_name}</span>
                  {isAdmin && (
                    <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20 dark:border-primary/40">
                      Admin
                    </span>
                  )}
                </div>
                <ThemeToggle />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSignOut}
                  disabled={signOutMutation.isPending}
                >
                  {signOutMutation.isPending ? 'Signing out...' : 'Sign Out'}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}