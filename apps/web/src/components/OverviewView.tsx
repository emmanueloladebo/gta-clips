import React from 'react';
import { Radio, Film, CheckCircle, HardDrive, Zap, Play, Eye } from 'lucide-react';
import { Streamer, Clip, Candidate, SystemMetrics, StorageUsage } from '../types';

interface OverviewViewProps {
  metrics: SystemMetrics | null;
  storage: StorageUsage | null;
  streamers: Streamer[];
  clips: Clip[];
  candidates: Candidate[];
  onSelectTab: (tab: string) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  metrics,
  storage,
  streamers,
  clips,
  candidates,
  onSelectTab,
}) => {
  const liveStreamers = streamers.filter((s) => s.live_status === 'live');
  const pendingClips = clips.filter((c) => c.approval_status === 'pending_review');

  const statCards = [
    {
      title: 'Monitored Streamers',
      value: metrics?.total_streamers_monitored ?? streamers.length,
      subtitle: `${liveStreamers.length} live right now`,
      icon: Radio,
      color: 'from-pink-500/20 to-pink-500/5 text-pink-400 border-pink-500/30',
    },
    {
      title: 'Clips For Review',
      value: pendingClips.length,
      subtitle: 'Need your approval',
      icon: Film,
      color: 'from-orange-500/20 to-orange-500/5 text-orange-400 border-orange-500/30',
      action: () => onSelectTab('review'),
    },
    {
      title: 'Published Clips',
      value: metrics?.total_clips_published ?? clips.filter((c) => c.approval_status === 'approved').length,
      subtitle: 'Shared to social channels',
      icon: CheckCircle,
      color: 'from-emerald-500/20 to-emerald-500/5 text-emerald-400 border-emerald-500/30',
      action: () => onSelectTab('publishing'),
    },
    {
      title: 'R2 Cloud Storage',
      value: `${metrics?.r2_storage_gb ?? 0} GiB`,
      subtitle: 'Strict 10 GiB budget limit',
      icon: HardDrive,
      color: 'from-cyan-500/20 to-cyan-500/5 text-cyan-400 border-cyan-500/30',
      action: () => onSelectTab('storage'),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              onClick={card.action}
              className={`p-5 rounded-2xl bg-gradient-to-br ${card.color} border bg-vice-card/60 backdrop-blur-sm transition-all ${
                card.action ? 'cursor-pointer hover:scale-[1.02]' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  {card.title}
                </span>
                <div className="p-2 rounded-xl bg-vice-dark/40">
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-black text-white">{card.value}</div>
              <div className="text-xs text-slate-400 mt-1">{card.subtitle}</div>
            </div>
          );
        })}
      </div>

      {/* Main Content Layout: Live Streams & Candidate Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Channels Feed (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Stream Monitoring
            </h2>
            <button
              onClick={() => onSelectTab('streamers')}
              className="text-xs font-semibold text-vice-pink hover:text-white transition-colors"
            >
              Manage Streamers &rarr;
            </button>
          </div>

          {liveStreamers.length === 0 ? (
            <div className="p-8 rounded-2xl bg-vice-card border border-vice-border text-center space-y-3">
              <div className="w-12 h-12 mx-auto rounded-full bg-vice-dark flex items-center justify-center text-slate-500">
                <Radio className="w-6 h-6" />
              </div>
              <h3 className="font-bold text-white">No Streamers Live Right Now</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                The cloud worker is checking your list every 30 seconds. Recording starts automatically when someone goes live.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {liveStreamers.map((s) => (
                <div
                  key={s.id}
                  className="p-4 rounded-2xl bg-vice-card border border-emerald-500/30 space-y-3 relative overflow-hidden"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span className="font-bold text-white text-sm">{s.display_name}</span>
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Recording
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-1">
                    {s.stream_title || 'Grand Theft Auto VI Livestream'}
                  </p>
                  <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-vice-border/60">
                    <span className="capitalize">{s.platform}</span>
                    <span className="flex items-center gap-1 font-medium text-slate-300">
                      <Eye className="w-3.5 h-3.5 text-vice-cyan" />
                      {s.viewer_count.toLocaleString()} watching
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pending Review Quick Strip */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Film className="w-4 h-4 text-vice-orange" />
                Latest Clips Ready for Review
              </h3>
              <button
                onClick={() => onSelectTab('review')}
                className="text-xs font-semibold text-vice-orange hover:text-white transition-colors"
              >
                Open Review Studio &rarr;
              </button>
            </div>

            {pendingClips.length === 0 ? (
              <div className="p-6 rounded-2xl bg-vice-card border border-vice-border text-center text-xs text-slate-400">
                No clips waiting for review right now.
              </div>
            ) : (
              <div className="space-y-2">
                {pendingClips.slice(0, 3).map((clip) => (
                  <div
                    key={clip.id}
                    className="p-3.5 rounded-xl bg-vice-card border border-vice-border flex items-center justify-between hover:border-vice-orange/40 transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-vice-dark flex items-center justify-center text-vice-orange shrink-0">
                        <Play className="w-4 h-4 fill-current" />
                      </div>
                      <div>
                        <p className="font-bold text-white text-xs line-clamp-1">{clip.title}</p>
                        <p className="text-[11px] text-slate-400">
                          {clip.duration_seconds.toFixed(0)}s &bull; 9:16 Vertical &bull; Auto-purges in 24h
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => onSelectTab('review')}
                      className="px-3 py-1.5 rounded-lg bg-vice-orange/10 hover:bg-vice-orange/20 text-vice-orange border border-vice-orange/30 text-xs font-semibold"
                    >
                      Review
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* AI Highlight Radar / Activity Column (1 col) */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Zap className="w-4 h-4 text-vice-cyan" />
            AI Highlight Radar
          </h2>

          <div className="p-4 rounded-2xl bg-vice-card border border-vice-border space-y-3">
            <p className="text-xs text-slate-300 font-medium">Recent High-Energy Moments</p>
            {candidates.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">
                Candidate highlights will appear here as live streams are transcribed and scored.
              </p>
            ) : (
              <div className="space-y-3">
                {candidates.slice(0, 4).map((cand) => (
                  <div
                    key={cand.id}
                    className="p-3 rounded-xl bg-vice-dark border border-vice-border/80 space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-white line-clamp-1">{cand.hook_summary}</span>
                      <span className="text-[10px] font-black px-1.5 py-0.5 rounded bg-vice-pink/10 text-vice-pink border border-vice-pink/30">
                        {cand.score.toFixed(0)} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2 italic">
                      "{cand.evidence_quote}"
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800">
                      <span>Excitement: {cand.excitement_score.toFixed(0)}%</span>
                      <span>Length: {cand.duration_seconds.toFixed(0)}s</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Cloud Usage Snapshot */}
          <div className="p-4 rounded-2xl bg-vice-card border border-vice-border space-y-2 text-xs">
            <h4 className="font-bold text-white">Estimated Usage</h4>
            <div className="space-y-1 text-slate-400 text-[11px]">
              <div className="flex justify-between">
                <span>Deepgram Audio:</span>
                <span className="text-slate-200 font-semibold">{metrics?.estimated_api_usage?.deepgram_minutes ?? 0} mins</span>
              </div>
              <div className="flex justify-between">
                <span>Groq LLM Tokens:</span>
                <span className="text-slate-200 font-semibold">
                  {((metrics?.estimated_api_usage?.groq_prompt_tokens ?? 0) + (metrics?.estimated_api_usage?.groq_completion_tokens ?? 0)).toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Streaming Ingest:</span>
                <span className="text-slate-200 font-semibold">{metrics?.estimated_api_usage?.bandwidth_gb ?? 0} GB</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
