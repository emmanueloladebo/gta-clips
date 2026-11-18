import React from 'react';
import { Radio, Film, CheckCircle, HardDrive, Zap, Play, Eye, ArrowUpRight } from 'lucide-react';
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
  const publishedClips = clips.filter((c) => c.approval_status === 'approved' || c.approval_status === 'published');

  const scratchUsedGb = storage ? (storage.scratch_used_bytes / (1024 ** 3)).toFixed(1) : '0.0';
  const scratchLimitGb = storage ? (storage.scratch_limit_bytes / (1024 ** 3)).toFixed(0) : '60';

  const statCards = [
    {
      title: 'Monitored Channels',
      value: streamers.length,
      subtitle: `${liveStreamers.length} live right now`,
      icon: Radio,
      badge: liveStreamers.length > 0 ? `${liveStreamers.length} Live` : 'Idle',
      badgeColor: liveStreamers.length > 0 ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-slate-800 text-slate-400 border-slate-700',
      action: () => onSelectTab('streamers'),
    },
    {
      title: 'Clips in Review',
      value: pendingClips.length,
      subtitle: pendingClips.length === 1 ? '1 clip ready for review' : `${pendingClips.length} clips ready for review`,
      icon: Film,
      badge: pendingClips.length > 0 ? 'Action Needed' : 'Up to Date',
      badgeColor: pendingClips.length > 0 ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-slate-800 text-slate-400 border-slate-700',
      action: () => onSelectTab('review'),
    },
    {
      title: 'Published Clips',
      value: metrics?.total_clips_published ?? publishedClips.length,
      subtitle: 'Delivered to social channels',
      icon: CheckCircle,
      badge: 'Auto-Post Ready',
      badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      action: () => onSelectTab('publishing'),
    },
    {
      title: 'Scratch Storage',
      value: `${scratchUsedGb} / ${scratchLimitGb} GB`,
      subtitle: '24-hour auto-clean cycle',
      icon: HardDrive,
      badge: 'Protected',
      badgeColor: 'bg-vice-cyan/10 text-vice-cyan border-vice-cyan/20',
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
              className="p-5 rounded-2xl bg-[#0f121b] border border-white/[0.08] hover:border-white/[0.18] transition-all cursor-pointer group space-y-3 relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-400">
                  {card.title}
                </span>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${card.badgeColor}`}>
                  {card.badge}
                </span>
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-2xl font-bold text-white tracking-tight">{card.value}</div>
                <div className="p-2 rounded-xl bg-white/[0.03] text-slate-400 group-hover:text-white transition-colors">
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="text-xs text-slate-400 font-medium">{card.subtitle}</div>
            </div>
          );
        })}
      </div>

      {/* Main Content Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Channels Feed (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Live Stream Monitoring
            </h2>
            <button
              onClick={() => onSelectTab('streamers')}
              className="text-xs font-semibold text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
            >
              <span>Manage Streamers</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {liveStreamers.length === 0 ? (
            <div className="p-8 rounded-2xl bg-[#0f121b] border border-white/[0.08] text-center space-y-2">
              <div className="w-10 h-10 mx-auto rounded-full bg-white/[0.04] flex items-center justify-center text-slate-400">
                <Radio className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-white text-sm">No Streamers Live Right Now</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                The cloud checks monitored channels automatically every 30 seconds. Ingest begins the moment a stream goes live.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {liveStreamers.map((s) => (
                <div
                  key={s.id}
                  className="p-5 rounded-2xl bg-[#0f121b] border border-white/[0.08] hover:border-emerald-500/30 space-y-3 relative overflow-hidden transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400" />
                      <span className="font-bold text-white text-sm">{s.display_name}</span>
                    </div>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Live
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 font-medium line-clamp-1">
                    {s.stream_title || 'Grand Theft Auto VI Livestream'}
                  </p>
                  <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-white/[0.06]">
                    <span className="capitalize">{s.platform}</span>
                    <span className="flex items-center gap-1.5 font-medium text-slate-200">
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
                Latest Clips for Review
              </h3>
              <button
                onClick={() => onSelectTab('review')}
                className="text-xs font-semibold text-vice-orange hover:text-white transition-colors"
              >
                Open Review Station &rarr;
              </button>
            </div>

            {pendingClips.length === 0 ? (
              <div className="p-6 rounded-2xl bg-[#0f121b] border border-white/[0.08] text-center text-xs text-slate-400">
                No clips waiting for review right now.
              </div>
            ) : (
              <div className="space-y-2">
                {pendingClips.slice(0, 3).map((clip) => (
                  <div
                    key={clip.id}
                    className="p-4 rounded-2xl bg-[#0f121b] border border-white/[0.08] flex items-center justify-between hover:border-white/[0.15] transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-white/[0.03] flex items-center justify-center text-vice-orange shrink-0">
                        <Play className="w-4 h-4 fill-current" />
                      </div>
                      <div>
                        <p className="font-bold text-white text-xs line-clamp-1">{clip.title}</p>
                        <p className="text-[11px] text-slate-400">
                          {clip.duration_seconds.toFixed(0)}s &bull; 9:16 Vertical &bull; Ready to publish
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => onSelectTab('review')}
                      className="px-3.5 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-white text-xs font-semibold cursor-pointer transition-all"
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
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Zap className="w-4 h-4 text-vice-cyan" />
            AI Highlight Radar
          </h2>

          <div className="p-5 rounded-2xl bg-[#0f121b] border border-white/[0.08] space-y-3">
            <p className="text-xs text-slate-300 font-semibold">Live Scored Moments</p>
            {candidates.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">
                Highlights will appear here in real time as live streams are transcribed and evaluated.
              </p>
            ) : (
              <div className="space-y-3">
                {candidates.slice(0, 4).map((cand) => (
                  <div
                    key={cand.id}
                    className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-white line-clamp-1">{cand.hook_summary}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-vice-pink/10 text-vice-pink border border-vice-pink/20">
                        {cand.score.toFixed(0)} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 line-clamp-2 italic">
                      "{cand.evidence_quote}"
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-white/[0.04]">
                      <span>Excitement: {cand.excitement_score.toFixed(0)}%</span>
                      <span>Length: {cand.duration_seconds.toFixed(0)}s</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Cloud Usage Snapshot */}
          <div className="p-5 rounded-2xl bg-[#0f121b] border border-white/[0.08] space-y-3 text-xs">
            <h4 className="font-bold text-white">Resource Metrics</h4>
            <div className="space-y-1.5 text-slate-400 text-[11px]">
              <div className="flex justify-between">
                <span>Deepgram Audio:</span>
                <span className="text-slate-200 font-medium">{metrics?.estimated_api_usage?.deepgram_minutes ?? 0} mins</span>
              </div>
              <div className="flex justify-between">
                <span>Groq LLM Tokens:</span>
                <span className="text-slate-200 font-medium">
                  {((metrics?.estimated_api_usage?.groq_prompt_tokens ?? 0) + (metrics?.estimated_api_usage?.groq_completion_tokens ?? 0)).toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Monitored Streams:</span>
                <span className="text-slate-200 font-medium">{streamers.length} channels</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
