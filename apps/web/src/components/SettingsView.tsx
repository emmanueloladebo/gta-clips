import React, { useState } from 'react';
import { Sliders, Shield, CheckCircle2, AlertCircle, HardDrive, Key, Lock, Cpu, Zap, Power, ArrowRight } from 'lucide-react';
import { HealthStatus, AiModelSettings } from '../types';

interface SettingsViewProps {
  health: HealthStatus | null;
  aiSettings: AiModelSettings | null;
  onToggleRouter?: () => Promise<void>;
  onUpdateAiSettings?: (data: Partial<AiModelSettings>) => Promise<void>;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  health,
  aiSettings,
  onToggleRouter,
  onUpdateAiSettings,
}) => {
  const [toggling, setToggling] = useState(false);

  const handleToggle = async () => {
    if (!onToggleRouter) return;
    setToggling(true);
    try {
      await onToggleRouter();
    } catch (err: any) {
      alert(err.message || 'Failed to toggle AI model');
    } finally {
      setToggling(false);
    }
  };

  const isRouterActive = aiSettings ? aiSettings.router_enabled : true;

  const providers = [
    {
      name: '9router Gateway',
      description: 'Primary AI model for picking viral clips (openai/gpt-6-luna)',
      status: isRouterActive ? 'Active' : 'Turned Off (Saving Credits)',
      isActive: isRouterActive,
      envVar: 'ROUTER_API_KEY & ROUTER_BASE_URL',
    },
    {
      name: 'Groq Cloud Engine',
      description: 'High-speed model (openai/gpt-oss-120b) used as backup and primary when 9router is off',
      status: 'Active (Always Ready)',
      isActive: true,
      envVar: 'GROQ_API_KEY',
    },
    {
      name: 'Deepgram Audio',
      description: 'Listens to stream speech and creates accurate timestamps',
      status: 'Active (Nova-3 model)',
      isActive: true,
      envVar: 'DEEPGRAM_API_KEY',
    },
    {
      name: 'Cloudflare R2 Storage',
      description: 'Stores final vertical MP4 clips and thumbnails',
      status: 'Active (10 GB budget)',
      isActive: true,
      envVar: 'R2_ACCESS_KEY_ID & R2_SECRET_ACCESS_KEY',
    },
    {
      name: 'Zernio Publishing',
      description: 'Posts clips directly to TikTok and YouTube Shorts',
      status: 'Connected',
      isActive: true,
      envVar: 'ZERNIO_API_KEY',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-black text-white">System Settings & AI Controls</h1>
        <p className="text-xs text-slate-400">
          Control which AI model finds highlights, turn 9router on or off to save credits, and check provider health.
        </p>
      </div>

      {/* AI Engine & Credit Control Section */}
      <div className="p-6 rounded-2xl bg-vice-card border border-vice-border space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-vice-dark flex items-center justify-center text-vice-cyan">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm">AI Highlight Engine Control</h3>
              <p className="text-xs text-slate-400">
                Switch or pause models whenever you want to cut down on API usage and save credits.
              </p>
            </div>
          </div>

          <button
            onClick={handleToggle}
            disabled={toggling}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all border ${
              isRouterActive
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20'
            }`}
          >
            <Power className={`w-4 h-4 ${toggling ? 'animate-spin' : ''}`} />
            {toggling
              ? 'Switching...'
              : isRouterActive
              ? '9router is ON (Click to turn off)'
              : '9router is OFF (Click to turn on)'}
          </button>
        </div>

        {/* Status Comparison Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* 9router Card */}
          <div
            className={`p-4 rounded-xl border transition-all space-y-3 ${
              isRouterActive
                ? 'bg-vice-dark/80 border-vice-cyan/40 shadow-lg shadow-vice-cyan/5'
                : 'bg-vice-dark/40 border-slate-800 opacity-60'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">9router Gateway</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-vice-dark border border-slate-700 text-slate-300">
                  openai/gpt-6-luna
                </span>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  isRouterActive
                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {isRouterActive ? 'IN USE' : 'PAUSED'}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Finds viral clips, relationship drama, and funny moments using GPT-6 Luna. Turn this off when you want to avoid high credit charges.
            </p>
            <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-vice-border/60">
              <span>Cost tier: Higher</span>
              <span className={isRouterActive ? 'text-emerald-400 font-semibold' : 'text-slate-500'}>
                {isRouterActive ? 'Active in clip detection' : '0 credits being used'}
              </span>
            </div>
          </div>

          {/* Groq Card */}
          <div
            className={`p-4 rounded-xl border transition-all space-y-3 ${
              !isRouterActive
                ? 'bg-vice-dark/80 border-vice-pink/40 shadow-lg shadow-vice-pink/5'
                : 'bg-vice-dark/80 border-vice-border'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">Groq GPT-OSS</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-vice-dark border border-slate-700 text-slate-300">
                  openai/gpt-oss-120b
                </span>
              </div>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  !isRouterActive
                    ? 'bg-vice-pink/15 text-vice-pink border-vice-pink/30 animate-pulse'
                    : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}
              >
                {!isRouterActive ? 'ACTIVE PRIMARY' : 'FALLBACK READY'}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Ultra-fast model with strict highlight extraction. When 9router is paused, Groq immediately handles 100% of highlight detection.
            </p>
            <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1 border-t border-vice-border/60">
              <span>Cost tier: Low cost</span>
              <span className="text-emerald-400 font-semibold">Always available</span>
            </div>
          </div>
        </div>

        {/* Helpful Explanation Note */}
        <div className="p-3.5 rounded-xl bg-vice-dark border border-vice-border flex items-start gap-3 text-xs">
          <Zap className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-slate-300 leading-relaxed">
            <strong className="text-white">Credit-Saving Mode: </strong>
            Whenever you turn off 9router, the worker completely stops calling 9router. No extra setup is needed — Groq takes over right away to score transcripts and generate clips without spending your 9router balance.
          </p>
        </div>
      </div>

      {/* Cloud Blockers / Live Status Section */}
      <div className="p-6 rounded-2xl bg-vice-card border border-vice-border space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-vice-dark flex items-center justify-center text-vice-pink">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">Connected Services & API Status</h3>
            <p className="text-xs text-slate-400">
              All cloud connections and services powering the background pipeline.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          {providers.map((p, idx) => (
            <div key={idx} className="p-3.5 rounded-xl bg-vice-dark border border-vice-border space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">{p.name}</span>
                <span
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                    p.isActive
                      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                      : 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                  }`}
                >
                  {p.status}
                </span>
              </div>
              <p className="text-slate-400 text-[11px]">{p.description}</p>
              <p className="text-[10px] font-mono text-slate-500 pt-1">Env: {p.envVar}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Safety Policy & Guardrails */}
      <div className="p-6 rounded-2xl bg-vice-card border border-vice-border space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-vice-dark flex items-center justify-center text-emerald-400">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">Rules & Content Safety</h3>
            <p className="text-xs text-slate-400">
              Protections built into the system to keep clips clean and costs controlled.
            </p>
          </div>
        </div>

        <div className="space-y-3 text-xs text-slate-300">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">Review Before Posting: </span>
              Clips must be approved by you in the dashboard before posting. Auto-posting is turned off by default.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">Streamer Permission Check: </span>
              Clips cannot be approved or published unless the streamer is marked as Granted in the dashboard.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">24-Hour Storage Cleanup: </span>
              Raw footage, audio, and old media files are cleared after 24 hours to keep disk usage low and avoid extra fees.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">Runs 100% in the Cloud: </span>
              All recording, transcribing, AI scoring, video editing, and social posting run in Docker containers on the cloud server. Your computer never has to do the heavy lifting.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
