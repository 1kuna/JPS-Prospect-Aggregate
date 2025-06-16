/**
 * Date formatting utilities for consistent date display across the application
 */

export type DateFormat = 'date' | 'datetime' | 'time' | 'relative';

export interface DateFormatOptions {
  fallback?: string;
  format?: DateFormat;
  locale?: string;
}

/**
 * Formats a date string consistently across the application
 * @param dateString - ISO date string or null
 * @param options - Formatting options
 * @returns Formatted date string
 */
export const formatDate = (
  dateString: string | null | undefined,
  options: DateFormatOptions = {}
): string => {
  const { fallback = 'N/A', format = 'datetime', locale = 'en-US' } = options;

  if (!dateString) return fallback;

  try {
    // Ensure proper ISO format by adding Z if timezone info is missing
    const dateStr = dateString.includes('Z') || dateString.includes('+') || dateString.includes('-')
      ? dateString
      : dateString + 'Z';

    const date = new Date(dateStr);

    // Check if date is valid
    if (isNaN(date.getTime())) {
      console.warn(`Invalid date string: ${dateString}`);
      return fallback;
    }

    switch (format) {
      case 'date':
        return date.toLocaleDateString(locale);
      case 'time':
        return date.toLocaleTimeString(locale);
      case 'datetime':
        return date.toLocaleString(locale);
      case 'relative':
        return formatRelativeTime(date);
      default:
        return date.toLocaleString(locale);
    }
  } catch (error) {
    console.warn(`Error formatting date: ${dateString}`, error);
    return fallback;
  }
};

/**
 * Formats a date as relative time (e.g., "2 hours ago", "3 days ago")
 * @param date - Date object
 * @returns Relative time string
 */
export const formatRelativeTime = (date: Date): string => {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return 'Just now';
  } else if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  } else if (diffDays < 7) {
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleDateString();
  }
};

/**
 * Checks if a date string is today
 * @param dateString - ISO date string
 * @returns True if the date is today
 */
export const isToday = (dateString: string | null): boolean => {
  if (!dateString) return false;

  try {
    const date = new Date(dateString);
    const today = new Date();
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  } catch {
    return false;
  }
};

/**
 * Checks if a date is in the future
 * @param dateString - ISO date string
 * @returns True if the date is in the future
 */
export const isFuture = (dateString: string | null): boolean => {
  if (!dateString) return false;

  try {
    const date = new Date(dateString);
    return date > new Date();
  } catch {
    return false;
  }
};