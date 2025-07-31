import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { TimezoneProvider, useTimezone, COMMON_TIMEZONES } from './TimezoneContext';
import type { User } from '@/types/api';

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
};

Object.defineProperty(global, 'localStorage', {
  value: mockLocalStorage,
  writable: true
});

// Mock Intl.DateTimeFormat for system timezone detection
const mockIntlDateTimeFormat = vi.fn();
global.Intl = {
  ...global.Intl,
  DateTimeFormat: mockIntlDateTimeFormat as any
};

// Test component that uses the timezone context
const TestComponent = () => {
  const {
    timezone,
    locale,
    setUserTimezone,
    detectSystemTimezone,
    getTimezoneOffset
  } = useTimezone();

  const handleSetTimezone = () => {
    setUserTimezone('America/Los_Angeles', 'en-US');
  };

  const handleDetectSystem = () => {
    const systemTz = detectSystemTimezone();
    const systemElement = document.createElement('div');
    systemElement.setAttribute('data-testid', 'system-timezone');
    systemElement.textContent = systemTz;
    document.body.appendChild(systemElement);
  };

  const handleGetOffset = () => {
    const offset = getTimezoneOffset();
    const offsetElement = document.createElement('div');
    offsetElement.setAttribute('data-testid', 'timezone-offset');
    offsetElement.textContent = offset;
    document.body.appendChild(offsetElement);
  };

  return (
    <div>
      <div data-testid="current-timezone">{timezone}</div>
      <div data-testid="current-locale">{locale}</div>
      <button onClick={handleSetTimezone} data-testid="set-timezone">
        Set Timezone
      </button>
      <button onClick={handleDetectSystem} data-testid="detect-system">
        Detect System
      </button>
      <button onClick={handleGetOffset} data-testid="get-offset">
        Get Offset
      </button>
    </div>
  );
};

// Test component for error handling
const TestComponentWithoutProvider = () => {
  const context = useTimezone();
  return <div>{context ? 'has context' : 'no context'}</div>;
};

describe('TimezoneContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clean up any elements added to body during tests
    document.querySelectorAll('[data-testid="system-timezone"]').forEach(el => el.remove());
    document.querySelectorAll('[data-testid="timezone-offset"]').forEach(el => el.remove());
    
    // Reset localStorage mocks
    mockLocalStorage.getItem.mockReturnValue(null);
    
    // Reset Intl mock
    mockIntlDateTimeFormat.mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'America/Chicago' }),
      formatToParts: () => [
        { type: 'timeZoneName', value: 'CST' }
      ]
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('provides timezone context to children with default values', () => {
    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/New_York');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('en-US');
  });

  it('throws error when useTimezone is used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    expect(() => {
      render(<TestComponentWithoutProvider />);
    }).toThrow('useTimezone must be used within a TimezoneProvider');
  
    consoleSpy.mockRestore();
  });

  it('initializes with user preference from props', () => {
    const mockUser: User = {
      id: 1,
      username: 'testuser',
      first_name: 'John',
      last_name: 'Doe',
      email: 'john@example.com',
      role: 'user',
      timezone: 'America/Los_Angeles',
      locale: 'es-ES',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };

    render(
      <TimezoneProvider user={mockUser}>
        <TestComponent />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/Los_Angeles');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('es-ES');
  });

  it('falls back to localStorage when no user preference', () => {
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'userTimezone') return 'America/Denver';
      if (key === 'userLocale') return 'fr-FR';
      return null;
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    expect(mockLocalStorage.getItem).toHaveBeenCalledWith('userTimezone');
    expect(mockLocalStorage.getItem).toHaveBeenCalledWith('userLocale');
    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/Denver');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('fr-FR');
  });

  it('falls back to system detection when no user or localStorage preference', () => {
    mockIntlDateTimeFormat.mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'Europe/London' })
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('current-timezone')).toHaveTextContent('Europe/London');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('en-US');
  });

  it('does not use UTC for system detection', () => {
    mockIntlDateTimeFormat.mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'UTC' })
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    // Should fall back to default instead of using UTC
    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/New_York');
  });

  it('handles system detection errors gracefully', () => {
    mockIntlDateTimeFormat.mockImplementation(() => {
      throw new Error('Intl not supported');
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    // Should fall back to default
    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/New_York');
  });

  it('sets user timezone and saves to localStorage', () => {
    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    fireEvent.click(screen.getByTestId('set-timezone'));

    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/Los_Angeles');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('en-US');
    
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('userTimezone', 'America/Los_Angeles');
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('userLocale', 'en-US');
  });

  it('sets timezone without changing locale when locale not provided', () => {
    const TimezoneOnlyComponent = () => {
      const { setUserTimezone } = useTimezone();
      
      const handleSetTimezoneOnly = () => {
        setUserTimezone('Europe/Paris');
      };

      return (
        <button onClick={handleSetTimezoneOnly} data-testid="set-timezone-only">
          Set Timezone Only
        </button>
      );
    };

    render(
      <TimezoneProvider>
        <TimezoneOnlyComponent />
        <TestComponent />
      </TimezoneProvider>
    );

    const originalLocale = screen.getByTestId('current-locale').textContent;
    
    fireEvent.click(screen.getByTestId('set-timezone-only'));

    expect(screen.getByTestId('current-timezone')).toHaveTextContent('Europe/Paris');
    expect(screen.getByTestId('current-locale')).toHaveTextContent(originalLocale || '');
    
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('userTimezone', 'Europe/Paris');
    expect(mockLocalStorage.setItem).not.toHaveBeenCalledWith('userLocale', expect.anything());
  });

  it('detects system timezone correctly', () => {
    mockIntlDateTimeFormat.mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'Asia/Tokyo' })
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    fireEvent.click(screen.getByTestId('detect-system'));

    expect(screen.getByTestId('system-timezone')).toHaveTextContent('Asia/Tokyo');
  });

  it('handles system timezone detection errors', () => {
    mockIntlDateTimeFormat.mockImplementation(() => {
      throw new Error('Detection failed');
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    fireEvent.click(screen.getByTestId('detect-system'));

    expect(screen.getByTestId('system-timezone')).toHaveTextContent('America/New_York');
  });

  it('gets timezone offset correctly', () => {
    mockIntlDateTimeFormat.mockReturnValue({
      formatToParts: vi.fn().mockReturnValue([
        { type: 'month', value: '1' },
        { type: 'day', value: '15' },
        { type: 'year', value: '2024' },
        { type: 'timeZoneName', value: 'PST' }
      ])
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    fireEvent.click(screen.getByTestId('get-offset'));

    expect(screen.getByTestId('timezone-offset')).toHaveTextContent('PST');
  });

  it('handles timezone offset errors gracefully', () => {
    mockIntlDateTimeFormat.mockReturnValue({
      formatToParts: vi.fn().mockImplementation(() => {
        throw new Error('Format error');
      })
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    fireEvent.click(screen.getByTestId('get-offset'));

    expect(screen.getByTestId('timezone-offset')).toHaveTextContent('');
  });

  it('handles missing timeZoneName in format parts', () => {
    mockIntlDateTimeFormat.mockReturnValue({
      formatToParts: vi.fn().mockReturnValue([
        { type: 'month', value: '1' },
        { type: 'day', value: '15' },
        { type: 'year', value: '2024' }
        // No timeZoneName part
      ])
    });

    render(
      <TimezoneProvider>
        <TestComponent />
      </TimezoneProvider>
    );

    fireEvent.click(screen.getByTestId('get-offset'));

    expect(screen.getByTestId('timezone-offset')).toHaveTextContent('');
  });

  it('updates when user prop changes', () => {
    const initialUser: User = {
      id: 1,
      username: 'testuser',
      first_name: 'John',
      last_name: 'Doe',
      email: 'john@example.com',
      role: 'user',
      timezone: 'America/Chicago',
      locale: 'en-US',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };

    const { rerender } = render(
      <TimezoneProvider user={initialUser}>
        <TestComponent />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/Chicago');

    const updatedUser: User = {
      ...initialUser,
      timezone: 'Europe/London',
      locale: 'en-GB'
    };

    rerender(
      <TimezoneProvider user={updatedUser}>
        <TestComponent />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('current-timezone')).toHaveTextContent('Europe/London');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('en-GB');
  });

  it('prioritizes user preference over localStorage', () => {
    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'userTimezone') return 'America/Denver';
      if (key === 'userLocale') return 'es-ES';
      return null;
    });

    const mockUser: User = {
      id: 1,
      username: 'testuser',
      first_name: 'John',
      last_name: 'Doe',
      email: 'john@example.com',
      role: 'user',
      timezone: 'Asia/Tokyo',
      locale: 'ja-JP',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };

    render(
      <TimezoneProvider user={mockUser}>
        <TestComponent />
      </TimezoneProvider>
    );

    // Should use user preference, not localStorage
    expect(screen.getByTestId('current-timezone')).toHaveTextContent('Asia/Tokyo');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('ja-JP');
  });

  it('handles user without timezone/locale properties', () => {
    const userWithoutTimezone: User = {
      id: 1,
      username: 'testuser',
      first_name: 'John',
      last_name: 'Doe',
      email: 'john@example.com',
      role: 'user',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };

    mockLocalStorage.getItem.mockImplementation((key) => {
      if (key === 'userTimezone') return 'America/Denver';
      return null;
    });

    render(
      <TimezoneProvider user={userWithoutTimezone}>
        <TestComponent />
      </TimezoneProvider>
    );

    // Should fall back to localStorage
    expect(screen.getByTestId('current-timezone')).toHaveTextContent('America/Denver');
    expect(screen.getByTestId('current-locale')).toHaveTextContent('en-US');
  });

  it('saves locale to localStorage when provided', () => {
    const LocaleTestComponent = () => {
      const { setUserTimezone } = useTimezone();
      
      const handleSetWithLocale = () => {
        setUserTimezone('Europe/Berlin', 'de-DE');
      };

      return (
        <button onClick={handleSetWithLocale} data-testid="set-with-locale">
          Set With Locale
        </button>
      );
    };

    render(
      <TimezoneProvider>
        <LocaleTestComponent />
      </TimezoneProvider>
    );

    fireEvent.click(screen.getByTestId('set-with-locale'));

    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('userTimezone', 'Europe/Berlin');
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith('userLocale', 'de-DE');
  });

  it('provides stable function references across re-renders', () => {
    let firstRenderFunctions: any;
    
    const FunctionRefComponent = () => {
      const context = useTimezone();
      
      if (!firstRenderFunctions) {
        firstRenderFunctions = {
          setUserTimezone: context.setUserTimezone,
          detectSystemTimezone: context.detectSystemTimezone,
          getTimezoneOffset: context.getTimezoneOffset
        };
      }
      
      const isStable = 
        Object.is(context.setUserTimezone, firstRenderFunctions.setUserTimezone) &&
        Object.is(context.detectSystemTimezone, firstRenderFunctions.detectSystemTimezone) &&
        Object.is(context.getTimezoneOffset, firstRenderFunctions.getTimezoneOffset);
      
      return (
        <div data-testid="functions-stable">
          {isStable ? 'stable' : 'changed'}
        </div>
      );
    };

    const { rerender } = render(
      <TimezoneProvider>
        <FunctionRefComponent />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('functions-stable')).toHaveTextContent('stable');

    rerender(
      <TimezoneProvider>
        <FunctionRefComponent />
      </TimezoneProvider>
    );

    expect(screen.getByTestId('functions-stable')).toHaveTextContent('stable');
  });
});

describe('COMMON_TIMEZONES', () => {
  it('exports common timezone options', () => {
    expect(COMMON_TIMEZONES).toBeDefined();
    expect(Array.isArray(COMMON_TIMEZONES)).toBe(true);
    expect(COMMON_TIMEZONES.length).toBeGreaterThan(0);
  });

  it('contains expected US timezones', () => {
    const usTimezones = COMMON_TIMEZONES.filter(tz => tz.group === 'US');
    
    expect(usTimezones).toContainEqual({
      value: 'America/New_York',
      label: 'Eastern Time (ET)',
      group: 'US'
    });
    
    expect(usTimezones).toContainEqual({
      value: 'America/Chicago',
      label: 'Central Time (CT)',
      group: 'US'
    });
    
    expect(usTimezones).toContainEqual({
      value: 'America/Los_Angeles',
      label: 'Pacific Time (PT)',
      group: 'US'
    });
  });

  it('contains international timezones', () => {
    const intlTimezones = COMMON_TIMEZONES.filter(tz => tz.group === 'International');
    
    expect(intlTimezones).toContainEqual({
      value: 'UTC',
      label: 'UTC (Coordinated Universal Time)',
      group: 'International'
    });
    
    expect(intlTimezones).toContainEqual({
      value: 'Europe/London',
      label: 'London (GMT/BST)',
      group: 'International'
    });
  });

  it('has proper structure for all timezone entries', () => {
    COMMON_TIMEZONES.forEach(timezone => {
      expect(timezone).toHaveProperty('value');
      expect(timezone).toHaveProperty('label');
      expect(timezone).toHaveProperty('group');
      expect(typeof timezone.value).toBe('string');
      expect(typeof timezone.label).toBe('string');
      expect(typeof timezone.group).toBe('string');
      expect(['US', 'International']).toContain(timezone.group);
    });
  });
});