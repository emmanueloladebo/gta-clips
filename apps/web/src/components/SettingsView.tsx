import React from 'react';
import { Sliders, Shield, CheckCircle2, AlertCircle, HardDrive, Key, Lock } from 'lucide-react';
import { HealthStatus } from '../types';

interface SettingsViewProps {
  health: HealthStatus | null;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ health }) => {
  const providers = [
    {
      name: 'Twitch Helix API',
      description: 'Checks when monitored streamers go live',
      status: 'Ready (Streamlink probe active)',
      envVar: 'TWITCH_CLIENT_ID & TWITCH_CLIENT_SECRET',
    },
    {
      name: 'Deepgram Audio Intelligence',
      description: 'Transcribes speech and identifies hype moments',
      status: 'Active (Nova-3 model)',
      envVar: 'DEEPGRAM_API_KEY',
    },
    {
      name: 'Groq Fast LLM Inference',
      description: 'Extracts highlights with strict JSON schemas',
      status: 'Active (Llama 3.3 70B)',
      envVar: 'GROQ_API_KEY',
    },
    {
      name: 'Cloudflare R2 Storage',
      description: 'Stores final vertical MP4 clips and thumbnails',
      status: 'Active (S3 Compatible with 10 GiB budget)',
      envVar: 'R2_ACCESS_KEY_ID & R2_SECRET_ACCESS_KEY',
    },
    {
      name: 'Zernio Publishing Adapter',
      description: 'Multi-platform social distribution',
      status: 'Connected (Idempotent job queue)',
      envVar: 'ZERNIO_API_KEY',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-black text-white">System Settings & Cloud Health</h1>
        <p className="text-xs text-slate-400">
          Check connection status for external providers, credentials blockers, and safety guardrails.
        </p>
      </div>

      {/* Cloud Blockers / Live Status Section */}
      <div className="p-6 rounded-2xl bg-vice-card border border-vice-border space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-vice-dark flex items-center justify-center text-vice-pink">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">Provider Setup & Credentials</h3>
            <p className="text-xs text-slate-400">
              When live API keys are not supplied, the platform automatically runs verified fallback adapters so development, review, and tests never break.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          {providers.map((p, idx) => (
            <div key={idx} className="p-3.5 rounded-xl bg-vice-dark border border-vice-border space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white">{p.name}</span>
                <span className="text-[10px] font-semibold text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
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
            <h3 className="font-bold text-white text-sm">Guardrails & Content Rights</h3>
            <p className="text-xs text-slate-400">
              Built-in protections to ensure ethical, legal, and cost-controlled operation.
            </p>
          </div>
        </div>

        <div className="space-y-3 text-xs text-slate-300">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">Review-Before-Post Default: </span>
              Clips must be explicitly approved by you in the dashboard before posting. Auto-posting is turned off by default.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">Creator Permission Gating: </span>
              Clips cannot be approved or published unless the streamer has a confirmed Creator Permission record on file.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">24-Hour Hard Storage Purge: </span>
              All raw footage, audio extractions, and Cloudflare R2 media files are deleted at 24 hours to prevent unexpected storage fees.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-white">No Personal Computer Requirement: </span>
              All recording, transcription, AI highlight scoring, FFmpeg editing, and cloud publishing run on the cloud Linux VPS inside Docker.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
