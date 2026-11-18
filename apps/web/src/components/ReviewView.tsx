import React, { useState } from 'react';
import { Film, Check, X, Clock, Play, Tag, Flame, ShieldAlert, AlertCircle } from 'lucide-react';
import { Clip } from '../types';

interface ReviewViewProps {
  clips: Clip[];
  onReviewClip: (id: number, action: 'approve' | 'reject', meta?: any) => Promise<void>;
}

export const ReviewView: React.FC<ReviewViewProps> = ({ clips, onReviewClip }) => {
  const [selectedClipId, setSelectedClipId] = useState<number | null>(clips[0]?.id || null);
  const [filter, setFilter] = useState<'pending_review' | 'approved' | 'rejected' | 'all'>('pending_review');
  const [editTitle, setEditTitle] = useState('');
  const [editTags, setEditTags] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const filteredClips = clips.filter((c) => {
    if (filter === 'all') return true;
    return c.approval_status === filter;
  });

  const activeClip = clips.find((c) => c.id === selectedClipId) || filteredClips[0];

  const handleSelectClip = (clip: Clip) => {
    setSelectedClipId(clip.id);
    setEditTitle(clip.title);
    setEditTags(clip.tags || '#GTA6 #Gaming #Shorts');
  };

  const handleApprove = async () => {
    if (!activeClip) return;
    setIsProcessing(true);
    try {
      await onReviewClip(activeClip.id, 'approve', {
        custom_title: editTitle || activeClip.title,
        custom_tags: editTags || activeClip.tags,
      });
    } catch (err: any) {
      alert(err.message || 'Approval failed');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    if (!activeClip) return;
    setIsProcessing(true);
    try {
      await onReviewClip(activeClip.id, 'reject');
    } catch (err: any) {
      alert(err.message || 'Rejection failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* View Header & Filter Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-white">Clip Review Station</h1>
          <p className="text-xs text-slate-400">
            Preview 9:16 vertical clips, tweak titles, and approve for social publishing.
          </p>
        </div>

        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-vice-card border border-vice-border text-xs font-semibold">
          {(['pending_review', 'approved', 'rejected', 'all'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded-lg transition-all capitalize ${
                filter === tab
                  ? 'bg-vice-pink text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {filteredClips.length === 0 ? (
        <div className="p-12 rounded-2xl bg-vice-card border border-vice-border text-center space-y-3">
          <div className="w-12 h-12 mx-auto rounded-full bg-vice-dark flex items-center justify-center text-slate-500">
            <Film className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-white">No Clips Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {filter === 'pending_review'
              ? 'All caught up! Newly rendered highlights will appear here ready for review.'
              : `No clips in the ${filter.replace('_', ' ')} list.`}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Clips List (4 cols) */}
          <div className="lg:col-span-5 space-y-3 max-h-[720px] overflow-y-auto pr-1">
            {filteredClips.map((clip) => {
              const isSelected = activeClip?.id === clip.id;
              const isApproved = clip.approval_status === 'approved';
              const isRejected = clip.approval_status === 'rejected';

              return (
                <div
                  key={clip.id}
                  onClick={() => handleSelectClip(clip)}
                  className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex gap-3.5 ${
                    isSelected
                      ? 'bg-vice-hover border-vice-pink shadow-lg shadow-vice-pink/10'
                      : 'bg-vice-card border-vice-border hover:border-slate-700'
                  }`}
                >
                  {/* Thumbnail box */}
                  <div className="w-20 h-28 rounded-xl bg-vice-dark border border-slate-800 shrink-0 overflow-hidden relative flex items-center justify-center">
                    {clip.r2_thumbnail_url ? (
                      <img
                        src={clip.r2_thumbnail_url}
                        alt="thumbnail"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="text-slate-600">
                        <Play className="w-6 h-6 fill-current" />
                      </div>
                    )}
                    <span className="absolute bottom-1 right-1 text-[10px] font-black bg-black/80 px-1 py-0.5 rounded text-white">
                      {clip.duration_seconds.toFixed(0)}s
                    </span>
                  </div>

                  {/* Clip Details */}
                  <div className="flex-1 min-w-0 flex flex-col justify-between py-0.5">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                            isApproved
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : isRejected
                              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          }`}
                        >
                          {clip.approval_status.replace('_', ' ')}
                        </span>
                        <span className="text-[10px] text-slate-400 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          24h TTL
                        </span>
                      </div>
                      <h4 className="font-bold text-white text-xs line-clamp-2">{clip.title}</h4>
                    </div>

                    <div className="text-[11px] text-slate-400 flex items-center justify-between pt-2 border-t border-vice-border/60">
                      <span>9:16 Vertical &bull; 1080p</span>
                      <span className="text-vice-cyan font-semibold">Ready</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Active Clip Preview & Review Studio (7 cols) */}
          {activeClip && (
            <div className="lg:col-span-7 p-6 rounded-2xl bg-vice-card border border-vice-border space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-center">
                {/* 9:16 Phone Frame Mockup */}
                <div className="w-full max-w-[240px] mx-auto aspect-[9/16] rounded-3xl bg-black border-4 border-slate-800 shadow-2xl overflow-hidden relative flex items-center justify-center">
                  {activeClip.r2_url ? (
                    <video
                      key={activeClip.r2_url}
                      src={activeClip.r2_url}
                      controls
                      playsInline
                      className="w-full h-full object-cover"
                      poster={activeClip.r2_thumbnail_url}
                    />
                  ) : (
                    <div className="text-center p-4 text-xs text-slate-400 space-y-2">
                      <Play className="w-8 h-8 mx-auto text-vice-pink" />
                      <p>Video rendering or cloud link loading...</p>
                    </div>
                  )}
                  {/* Watermark overlay preview */}
                  <div className="absolute top-4 left-3 right-3 text-center pointer-events-none">
                    <span className="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-black/60 text-white backdrop-blur-sm">
                      GTA 6 Highlights
                    </span>
                  </div>
                </div>

                {/* Metadata & Actions Column */}
                <div className="space-y-4 text-xs">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Highlight Title
                    </span>
                    <input
                      type="text"
                      value={editTitle || activeClip.title}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full mt-1 px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white text-xs font-semibold focus:outline-none focus:border-vice-pink"
                    />
                  </div>

                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Hashtags
                    </span>
                    <input
                      type="text"
                      value={editTags || activeClip.tags || '#GTA6 #Gaming #Shorts'}
                      onChange={(e) => setEditTags(e.target.value)}
                      className="w-full mt-1 px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white text-xs focus:outline-none focus:border-vice-pink"
                    />
                  </div>

                  {/* Highlights Spec Card */}
                  <div className="p-3.5 rounded-xl bg-vice-dark border border-vice-border space-y-2">
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Aspect Ratio:</span>
                      <span className="font-semibold text-white">9:16 (1080x1920)</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Length:</span>
                      <span className="font-semibold text-white">{activeClip.duration_seconds.toFixed(0)} seconds</span>
                    </div>
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Media Retention:</span>
                      <span className="font-semibold text-emerald-400">Deletes after 24h</span>
                    </div>
                  </div>

                  {/* Review Action Buttons */}
                  <div className="pt-2 space-y-2">
                    <button
                      onClick={handleApprove}
                      disabled={isProcessing}
                      className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:opacity-95 text-white font-bold text-xs shadow-lg shadow-emerald-500/20 disabled:opacity-50 transition-all"
                    >
                      <Check className="w-4 h-4" />
                      Approve & Queue for Publishing
                    </button>

                    <button
                      onClick={handleReject}
                      disabled={isProcessing}
                      className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-vice-dark hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 border border-vice-border text-xs font-semibold transition-all"
                    >
                      <X className="w-4 h-4" />
                      Reject Clip
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
