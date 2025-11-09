import { create } from 'zustand'
import { ModuleId } from '@/lib/pantheon-names'

interface PantheonState {
  currentRealm: ModuleId
  oracleOpen: boolean
  pulseVisible: boolean
  spineCollapsed: boolean
  
  setCurrentRealm: (realm: ModuleId) => void
  setOracleOpen: (open: boolean) => void
  setPulseVisible: (visible: boolean) => void
  setSpineCollapsed: (collapsed: boolean) => void
}

export const usePantheonStore = create<PantheonState>((set) => ({
  currentRealm: 'aeon',
  oracleOpen: false,
  pulseVisible: true,
  spineCollapsed: false,
  
  setCurrentRealm: (realm) => set({ currentRealm: realm }),
  setOracleOpen: (open) => set({ oracleOpen: open }),
  setPulseVisible: (visible) => set({ pulseVisible: visible }),
  setSpineCollapsed: (collapsed) => set({ spineCollapsed: collapsed }),
}))
