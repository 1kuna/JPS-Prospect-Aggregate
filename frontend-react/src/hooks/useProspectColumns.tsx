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
    columnHelper.accessor((row) => row.extra?.agency || row.agency, {
      id: 'agency',
      header: 'Agency',
      cell: info => {
        const value = info.getValue();
        return <div className="w-full truncate" title={String(value) || 'N/A'}>{String(value) || 'N/A'}</div>;
      },
      size: 200,
    }),
    columnHelper.accessor((row) => {
      const naics = showAIEnhanced ? row.naics : (row.naics_source === 'llm_inferred' ? null : row.naics);
      const description = showAIEnhanced ? row.naics_description : (row.naics_source !== 'llm_inferred' ? row.naics_description : null);
      
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
      // Show enhanced estimated value if available and toggle is on, otherwise fall back to original
      if (showAIEnhanced && row.estimated_value_single) {
        const single = parseFloat(row.estimated_value_single);
        if (single >= 1000000) {
          return `$${(single / 1000000).toFixed(1)}M`;
        } else if (single >= 1000) {
          return `$${(single / 1000).toFixed(0)}K`;
        } else {
          return `$${single.toFixed(0)}`;
        }
      }
      
      // Original value logic
      if (row.estimated_value_text) {
        return row.estimated_value_text;
      } else if (row.estimated_value) {
        const value = parseFloat(row.estimated_value);
        if (value >= 1000000) {
          return `$${(value / 1000000).toFixed(1)}M`;
        } else if (value >= 1000) {
          return `$${(value / 1000).toFixed(0)}K`;
        } else {
          return `$${value.toFixed(0)}`;
        }
      }
      return 'N/A';
    }, {
      id: 'estimated_value',
      header: 'Est. Value',
      cell: info => {
        const value = info.getValue();
        const row = info.row.original;
        const isAIEnhanced = showAIEnhanced && !!row.estimated_value_single;
        
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
    columnHelper.accessor((row) => row.extra?.acquisition_phase || row.contract_type, {
      id: 'contract_type',
      header: 'Type',
      cell: info => {
        const value = info.getValue();
        return <div className="w-full truncate" title={String(value) || 'N/A'}>{String(value) || 'N/A'}</div>;
      },
      size: 150,
    }),
  ], [showAIEnhanced]);

  return { columns };
}