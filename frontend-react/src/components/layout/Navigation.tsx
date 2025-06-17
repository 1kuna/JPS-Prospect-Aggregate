import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useAuth } from '../AuthProvider';
import { useSignOut } from '../../hooks/api';
import { Button } from '../ui/button';

export function Navigation() {
  const location = useLocation();
  const { user } = useAuth();
  const signOutMutation = useSignOut();
  
  const navItems = [
    { path: '/', label: 'Dashboard' },
    { path: '/advanced', label: 'Advanced' },
  ];

  const handleSignOut = async () => {
    try {
      await signOutMutation.mutateAsync();
    } catch (error) {
      console.error('Sign out failed:', error);
    }
  };
  
  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">JPS Prospect Aggregate</h1>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium",
                    location.pathname === item.path
                      ? "border-blue-500 text-gray-900"
                      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
          
          {/* User menu */}
          <div className="flex items-center space-x-4">
            {user && (
              <>
                <div className="text-sm text-gray-700">
                  Welcome, <span className="font-medium">{user.first_name}</span>
                </div>
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