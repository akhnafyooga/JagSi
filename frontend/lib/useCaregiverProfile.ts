'use client';

import { useEffect, useState } from 'react';
import { createClient } from '@supabase/supabase-js';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export interface CaregiverProfile {
  caregiverName: string | null;
  wearerName: string | null;
  relationship: string | null;
  configured: boolean;
}

/**
 * Reads the names the user entered during /setup from Supabase user_metadata,
 * so the hosted demo reflects the real flow instead of the static Ibu Sari
 * mock. Falls back to the mock names when auth is unconfigured or signed out.
 */
export function useCaregiverProfile(): CaregiverProfile {
  const [profile, setProfile] = useState<CaregiverProfile>({
    caregiverName: null,
    wearerName: null,
    relationship: null,
    configured: Boolean(url && key),
  });

  useEffect(() => {
    if (!url || !key) return;
    const auth = createClient(url, key, { auth: { flowType: 'pkce' } }).auth;
    let cancelled = false;
    auth.getSession().then(({ data }) => {
      if (cancelled) return;
      const meta = data.session?.user.user_metadata ?? {};
      const caregiverName =
        typeof meta.caregiver_name === 'string' && meta.caregiver_name.trim()
          ? meta.caregiver_name.trim()
          : typeof meta.full_name === 'string' && meta.full_name.trim()
            ? meta.full_name.trim()
            : null;
      const wearerName =
        typeof meta.wearer_name === 'string' && meta.wearer_name.trim()
          ? meta.wearer_name.trim()
          : null;
      const relationship =
        typeof meta.wearer_relationship === 'string' && meta.wearer_relationship.trim()
          ? meta.wearer_relationship.trim()
          : null;
      setProfile({ caregiverName, wearerName, relationship, configured: true });
    });
    const { data } = auth.onAuthStateChange((event, session) => {
      if (cancelled || (event !== 'SIGNED_IN' && event !== 'INITIAL_SESSION' && event !== 'USER_UPDATED')) return;
      const meta = session?.user.user_metadata ?? {};
      const caregiverName =
        typeof meta.caregiver_name === 'string' && meta.caregiver_name.trim()
          ? meta.caregiver_name.trim()
          : typeof meta.full_name === 'string' && meta.full_name.trim()
            ? meta.full_name.trim()
            : null;
      const wearerName =
        typeof meta.wearer_name === 'string' && meta.wearer_name.trim()
          ? meta.wearer_name.trim()
          : null;
      const relationship =
        typeof meta.wearer_relationship === 'string' && meta.wearer_relationship.trim()
          ? meta.wearer_relationship.trim()
          : null;
      setProfile({ caregiverName, wearerName, relationship, configured: true });
    });
    return () => {
      cancelled = true;
      data.subscription.unsubscribe();
    };
  }, []);

  return profile;
}
