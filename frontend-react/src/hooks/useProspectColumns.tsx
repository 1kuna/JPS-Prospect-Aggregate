import { useMemo } from 'react';
import { createColumnHelper } from '@tanstack/react-table';
import type { Prospect } from '@/types/prospects';

const columnHelper = createColumnHelper<Prospect>();

export function useProspectColumns(showAIEnhanced: boolean) {
  const columns = useMemo(() => [
    columnHelper.accessor((row) => {
      // Check if we should show AI enhanced title
      if (showAIEnhanced && row.ai_enhanced_title) {
        return row.ai_enhanced_title;
      }
      // Otherwise show original title logic
      if (row.title) return row.title;
      if (row.extra?.summary && typeof row.extra.summary === 'string') return row.extra.summary;
      // Fallback: construct from agency and native_id
      if (row.native_id) {
        const agency = row.extra?.agency || row.agency || 'Unknown Agency';
        return `${agency} - ${row.native_id}`;
      }
      return 'No Title';
    }, {
      id: 'title',
      header: 'Title',
      cell: info => {
        const value = info.getValue();
        const row = info.row.original;
        const isAIEnhanced = showAIEnhanced && !!row.ai_enhanced_title && row.title !== row.ai_enhanced_title;
        const title = isAIEnhanced 
          ? `${value} (AI Enhanced)` 
          : value || 'No Title';
        
        return (
          <div className="w-full truncate" title={title}>
            <span className={isAIEnhanced ? 'text-blue-700 font-medium' : ''}>
              {String(value) || 'No Title'}
            </span>
          </div>
        );
      },
      size: 350,
    }),
    columnHelper.accessor((row) => {
      const naics = showAIEnhanced ? row.naics : (row.naics_source === 'llm_inferred' ? null : row.naics);
      const description = row.naics_description;
      
      if (!naics) return 'N/A';
      
      // Use standardized pipe format: "334516 | Description"
      const display = description ? `${naics} | ${description}` : naics;
      
      return display;
    }, {
      id: 'naics',
      header: 'NAICS',
      cell: info => {
        const value = info.getValue();
        const row = info.row.original;
        const isAIEnhanced = row.naics_source === 'llm_inferred';
        const title = isAIEnhanced 
          ? `${value} (AI Classified)` 
          : row.naics_source === 'original' 
          ? `${value} (Original)` 
          : value;
        
        return (
          <div className="w-full truncate" title={title}>
            <span className={isAIEnhanced && showAIEnhanced ? 'text-blue-700 font-medium' : ''}>
              {value}
            </span>
            {isAIEnhanced && showAIEnhanced && (
              <div className="w-2 h-2 bg-blue-500 rounded-full inline-block ml-2" title="AI Enhanced"></div>
            )}
          </div>
        );
      },
      size: 200,
    }),
    columnHelper.accessor((row) => {
      // Helper function to format dollar amounts
      const formatAmount = (amount: number) => {
        if (amount >= 1000000) {
          return `$${(amount / 1000000).toFixed(1)}M`;
        } else if (amount >= 1000) {
          return `$${(amount / 1000).toFixed(0)}K`;
        } else {
          return `$${amount.toFixed(0)}`;
        }
      };

      // Show enhanced estimated value if available and toggle is on, otherwise fall back to original
      if (showAIEnhanced) {
        // Check for range (min/max populated, single is null)
        if (row.estimated_value_min && row.estimated_value_max && !row.estimated_value_single) {
          const min = parseFloat(row.estimated_value_min);
          const max = parseFloat(row.estimated_value_max);
          return `${formatAmount(min)} - ${formatAmount(max)}`;
        }
        // Check for single value
        else if (row.estimated_value_single) {
          const single = parseFloat(row.estimated_value_single);
          return formatAmount(single);
        }
      }
      
      // Original value logic
      if (row.estimated_value_text) {
        return row.estimated_value_text;
      } else if (row.estimated_value) {
        const value = parseFloat(row.estimated_value);
        return formatAmount(value);
      }
      return 'N/A';
    }, {
      id: 'estimated_value',
      header: 'Est. Value',
      cell: info => {
        const value = info.getValue();
        const row = info.row.original;
        const isAIEnhanced = showAIEnhanced && (!!row.estimated_value_single || (!!row.estimated_value_min && !!row.estimated_value_max));
        
        return (
          <div title={value} className={isAIEnhanced ? 'text-green-700 font-medium' : ''}>
            {value}
            {isAIEnhanced && (
              <div className="w-2 h-2 bg-green-500 rounded-full inline-block ml-2" title="AI Parsed"></div>
            )}
          </div>
        );
      },
      size: 120,
    }),
    columnHelper.accessor((row) => {
      // Determine which date is earlier (due date)
      const awardDate = row.award_date ? new Date(row.award_date) : null;
      const releaseDate = row.release_date ? new Date(row.release_date) : null;
      
      if (!awardDate && !releaseDate) return null;
      if (!awardDate) return { date: releaseDate, type: 'release' };
      if (!releaseDate) return { date: awardDate, type: 'award' };
      
      // Return the earlier date
      return awardDate <= releaseDate 
        ? { date: awardDate, type: 'award' }
        : { date: releaseDate, type: 'release' };
    }, {
      id: 'due_date',
      header: 'Due Date',
      cell: info => {
        const value = info.getValue();
        if (!value || !value.date) return <div>N/A</div>;
        
        const dateStr = value.date.toLocaleDateString();
        const typeLabel = value.type === 'award' ? 'Award' : 'Release';
        const row = info.row.original;
        
        // Check if this is a tentative award date from fiscal quarter
        const isTentativeAward = value.type === 'award' && row.extra?.award_date_is_tentative;
        const quarterNumber = (() => {
          const quarterStr = row.extra?.award_quarter_original;
          if (typeof quarterStr === 'string') {
            const match = quarterStr.match(/Q([1-4])/);
            return match?.[1];
          }
          return undefined;
        })();
        
        return (
          <div className="w-full truncate" title={`${typeLabel}: ${dateStr}${isTentativeAward ? ' (Tentative from quarter)' : ''}`}>
            <span>{dateStr}</span>
            {Boolean(isTentativeAward) && (
              <span className="ml-1 text-xs px-1 py-0.5 rounded bg-orange-100 text-orange-700">
                Q{quarterNumber || '?'}
              </span>
            )}
          </div>
        );
      },
      size: 120,
    }),
    columnHelper.accessor((row) => row.set_aside, {
      id: 'set_aside',
      header: 'Set Aside',
      cell: info => {
        const value = info.getValue();
        return <div className="w-full truncate" title={String(value) || 'N/A'}>{String(value) || 'N/A'}</div>;
      },
      size: 150,
    }),
  ], [showAIEnhanced]);

  return { columns };
}