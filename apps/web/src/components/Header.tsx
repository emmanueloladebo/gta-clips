import React from 'react';
import { HardDrive, Clock, ShieldCheck, LogOut, Radio } from 'lucide-react';
import { StorageUsage, HealthStatus } from '../types';

interface HeaderProps {
  storage: StorageUsage | null;
  health: HealthStatus | null;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({ storage, health, onLogout }) => {
  const r2GbUsed = storage ? (storage.r2_used_bytes / (1024 ** 3)).toFixed(2) : '0.00';
  const r2HardGb = storage ? (storage.r2_hard_limit_bytes / (1024 ** 3)).toFixed(0) : '10';
  const percentage = storage ? Math.min(100, Math.round((storage.r2_used_bytes / storage.r2_hard_limit_bytes) * 100)) : 0;

  const isWarning = storage?.r2_soft_limit_exceeded;
  const isDanger = storage?.r2_hard_limit_exceeded;

  return (
    <header className="h-16 border-b border-vice-border bg-vice-card/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Brand title */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-vice-pink to-vice-orange flex items-center justify-center font-black text-white text-lg tracking-wider shadow-lg shadow-vice-pink/20">
          VI
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-base tracking-tight text-white">VICE CLIPS</span>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-vice-cyan/10 text-vice-cyan border border-vice-cyan/30">
              Cloud Studio
            </span>
          </div>
          <p className="text-xs text-slate-400">Automated GTA 6 Stream Clipping</p>
        </div>
      </div>

      {/* Cloud Status Badges */}
      <div className="flex items-center gap-5 text-xs">
        {/* Cloud Health */}
        <div className="hidden md:flex items-center gap-2 bg-vice-dark px-3 py-1.5 rounded-lg border border-vice-border">
          <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className="text-slate-300 font-medium">Cloud Workers</span>
          <span className="text-slate-500">|</span>
          <span className="text-emerald-400 font-semibold">{health?.workers_active ?? 1} active</span>
        </div>

        {/* 24-Hour Retention Policy */}
        <div className="hidden lg:flex items-center gap-2 bg-vice-dark px-3 py-1.5 rounded-lg border border-vice-border text-slate-300">
          <Clock className="w-3.5 h-3.5 text-vice-cyan" />
          <span>24h Retention</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-medium">Safe TTL</span>
        </div>

        {/* R2 Storage Gauge */}
        <div className="flex items-center gap-3 bg-vice-dark px-3 py-1.5 rounded-lg border border-vice-border">
          <HardDrive className={`w-4 h-4 ${isDanger ? 'text-rose-400' : isWarning ? 'text-amber-400' : 'text-slate-400'}`} />
          <div>
            <div className="flex items-center justify-between gap-3 text-[11px]">
              <span className="text-slate-400">R2 Budget</span>
              <span className={`font-semibold ${isDanger ? 'text-rose-400' : isWarning ? 'text-amber-400' : 'text-slate-200'}`}>
                {r2GbUsed} / {r2HardGb} GiB
              </span>
            </div>
            <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden mt-1">
              <div
                className={`h-full rounded-full transition-all ${
                  isDanger ? 'bg-rose-500' : isWarning ? 'bg-amber-400' : 'bg-gradient-to-r from-vice-pink to-vice-orange'
                }`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={onLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-vice-border/50 hover:bg-vice-border text-slate-300 hover:text-white transition-colors"
          title="Sign out"
        >
          <LogOut className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
};
