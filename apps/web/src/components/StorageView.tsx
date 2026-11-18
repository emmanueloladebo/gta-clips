import React, { useState } from 'react';
import { HardDrive, Trash2, Clock, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-react';
import { StorageUsage } from '../types';

interface StorageViewProps {
  storage: StorageUsage | null;
  onTriggerCleanup: () => Promise<any>;
}

export const StorageView: React.FC<StorageViewProps> = ({ storage, onTriggerCleanup }) => {
  const [cleaning, setCleaning] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<string | null>(null);

  const r2UsedGb = storage ? (storage.r2_used_bytes / (1024 ** 3)).toFixed(2) : '0.00';
  const r2SoftGb = storage ? (storage.r2_soft_limit_bytes / (1024 ** 3)).toFixed(1) : '8.0';
  const r2HardGb = storage ? (storage.r2_hard_limit_bytes / (1024 ** 3)).toFixed(1) : '10.0';
  const r2Percent = storage
    ? Math.min(100, Math.round((storage.r2_used_bytes / storage.r2_hard_limit_bytes) * 100))
    : 0;

  const scratchUsedGb = storage ? (storage.scratch_used_bytes / (1024 ** 3)).toFixed(2) : '0.00';
  const scratchLimitGb = storage ? (storage.scratch_limit_bytes / (1024 ** 3)).toFixed(0) : '20';
  const scratchPercent = storage
    ? Math.min(100, Math.round((storage.scratch_used_bytes / storage.scratch_limit_bytes) * 100))
    : 0;

  const handleCleanup = async () => {
    setCleaning(true);
    try {
      const res = await onTriggerCleanup();
      setCleanupResult(res.message || '24h cleanup completed.');
    } catch (err: any) {
      alert(err.message || 'Cleanup failed');
    } finally {
      setCleaning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-white">Storage & Retention Limits</h1>
          <p className="text-xs text-slate-400">
            Monitors Cloudflare R2 bucket limits and enforces the strict 24-hour media retention rule.
          </p>
        </div>

        <button
          onClick={handleCleanup}
          disabled={cleaning}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-vice-dark hover:bg-vice-hover border border-vice-border text-slate-200 hover:text-white text-xs font-semibold disabled:opacity-50 transition-colors"
        >
          <Trash2 className={`w-4 h-4 text-rose-400 ${cleaning ? 'animate-spin' : ''}`} />
          Run 24h Purge Now
        </button>
      </div>

      {cleanupResult && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
          {cleanupResult}
        </div>
      )}

      {/* R2 Cloud Budget Card */}
      <div className="p-6 rounded-2xl bg-vice-card border border-vice-border space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-vice-dark flex items-center justify-center text-vice-orange">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm">Cloudflare R2 Storage Budget</h3>
              <p className="text-xs text-slate-400">
                10 GiB hard application ceiling with an 8 GiB soft warning threshold.
              </p>
            </div>
          </div>
          <span className="font-mono text-base font-black text-white">
            {r2UsedGb} / {r2HardGb} GiB
          </span>
        </div>

        {/* Multi-tier progress bar */}
        <div className="space-y-1">
          <div className="w-full h-3 bg-vice-dark rounded-full overflow-hidden p-0.5 border border-vice-border relative">
            {/* Soft limit marker line at 80% */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-amber-400/80 z-10"
              style={{ left: '80%' }}
              title="8 GiB Soft Limit"
            />
            <div
              className={`h-full rounded-full transition-all ${
                storage?.r2_hard_limit_exceeded
                  ? 'bg-rose-500'
                  : storage?.r2_soft_limit_exceeded
                  ? 'bg-amber-400'
                  : 'bg-gradient-to-r from-vice-pink to-vice-orange'
              }`}
              style={{ width: `${r2Percent}%` }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-slate-400 pt-1">
            <span>0 GiB</span>
            <span className="text-amber-400 font-semibold">8 GiB Soft Threshold</span>
            <span className="text-rose-400 font-semibold">10 GiB Hard Cap</span>
          </div>
        </div>

        {storage?.r2_soft_limit_exceeded && (
          <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-2 text-xs text-amber-400 font-medium">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>Storage has reached the 8 GiB warning limit. Older clips will be prioritized for cleanup.</span>
          </div>
        )}
      </div>

      {/* VPS Scratch Storage Card */}
      <div className="p-6 rounded-2xl bg-vice-card border border-vice-border space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-vice-dark flex items-center justify-center text-vice-cyan">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm">VPS Scratch Disk (Captures & Temp Files)</h3>
              <p className="text-xs text-slate-400">
                Temporary workspace for 10-minute stream segments and FFmpeg renders.
              </p>
            </div>
          </div>
          <span className="font-mono text-base font-black text-white">
            {scratchUsedGb} / {scratchLimitGb} GiB
          </span>
        </div>

        <div className="w-full h-3 bg-vice-dark rounded-full overflow-hidden p-0.5 border border-vice-border">
          <div
            className="h-full rounded-full bg-vice-cyan transition-all"
            style={{ width: `${scratchPercent}%` }}
          />
        </div>
      </div>

      {/* 24-Hour Retention Rules Detail */}
      <div className="p-6 rounded-2xl bg-vice-card border border-vice-border space-y-3">
        <div className="flex items-center gap-2 text-white font-bold text-sm">
          <Clock className="w-4 h-4 text-emerald-400" />
          Strict 24-Hour Media Retention Policy
        </div>
        <p className="text-xs text-slate-400 leading-relaxed">
          To comply with creator guidelines and avoid unnecessary cloud hosting fees, all media files are tagged with a 24-hour expiration timestamp on creation. The background cleanup worker runs an hourly automated sweep to permanently delete expired video segments, temporary audio extractions, and Cloudflare R2 objects.
        </p>
      </div>
    </div>
  );
};
