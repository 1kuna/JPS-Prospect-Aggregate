import { useState, useCallback, useMemo } from 'react';

// Match the Dashboard's Prospect interface for now
interface Prospect {
  id: string;
  native_id: string | null;
  title: string;
  ai_enhanced_title: string | null;
  description: string | null;
  agency: string | null;
  naics: string | null;
  naics_description: string | null;
  naics_source: string | null;
  estimated_value: string | null;
  est_value_unit: string | null;
  estimated_value_text: string | null;
  estimated_value_min: string | null;
  estimated_value_max: string | null;
  estimated_value_single: string | null;
  release_date: string | null;
  award_date: string | null;
  award_fiscal_year: number | null;
  _recentlyUpdated?: string;
  _updateTimestamp?: number;
  place_city: string | null;
  place_state: string | null;
  place_country: string | null;
  contract_type: string | null;
  set_aside: string | null;
  primary_contact_email: string | null;
  primary_contact_name: string | null;
  loaded_at: string | null;
  ollama_processed_at: string | null;
  ollama_model_version: string | null;
  enhancement_status: string | null;
  enhancement_started_at: string | null;
  enhancement_user_id: number | null;
  extra: Record<string, unknown> | null;
  source_id: number | null;
  source_name: string | null;
}

export function useProspectModal(prospects: Prospect[] = []) {
  const [selectedProspectId, setSelectedProspectId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const selectedProspect = useMemo(() => {
    if (!selectedProspectId || !prospects.length) return null;
    return prospects.find((p) => p.id === selectedProspectId) || null;
  }, [selectedProspectId, prospects]);

  const openModal = useCallback((prospect: Prospect) => {
    setSelectedProspectId(prospect.id);
    setIsOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsOpen(false);
    setSelectedProspectId(null);
  }, []);

  const handleOpenChange = useCallback((open: boolean) => {
    setIsOpen(open);
    if (!open) {
      setSelectedProspectId(null);
    }
  }, []);

  return {
    selectedProspect,
    selectedProspectId,
    isOpen,
    openModal,
    closeModal,
    handleOpenChange,
    setSelectedProspectId,
    setIsOpen
  };
}