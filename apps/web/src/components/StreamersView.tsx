import React, { useState } from 'react';
import { Plus, Radio, RefreshCw, Trash2, CheckCircle2, AlertCircle, Shield, ExternalLink, Flame } from 'lucide-react';
import { Streamer } from '../types';

interface StreamersViewProps {
  streamers: Streamer[];
  onAddStreamer: (data: any) => Promise<void>;
  onCheckLive: (id: number) => Promise<void>;
  onInstantCapture?: (id: number) => Promise<void>;
  onDeleteStreamer: (id: number) => Promise<void>;
  onUpdatePermission: (id: number, data: any) => Promise<void>;
}

export const StreamersView: React.FC<StreamersViewProps> = ({
  streamers,
  onAddStreamer,
  onCheckLive,
  onInstantCapture,
  onDeleteStreamer,
  onUpdatePermission,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedStreamerForPerm, setSelectedStreamerForPerm] = useState<Streamer | null>(null);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [capturingId, setCapturingId] = useState<number | null>(null);

  // Form states for adding streamer
  const [platform, setPlatform] = useState<'twitch' | 'youtube'>('twitch');
  const [channelId, setChannelId] = useState('');
  const [channelUrl, setChannelUrl] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [permissionStatus, setPermissionStatus] = useState<'granted' | 'pending'>('pending');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!channelId || !displayName) return;
    setIsSubmitting(true);
    try {
      const computedUrl = channelUrl || (platform === 'twitch' ? `https://twitch.tv/${channelId}` : `https://youtube.com/@${channelId}`);
      await onAddStreamer({
        platform,
        channel_id: channelId,
        channel_url: computedUrl,
        display_name: displayName,
        is_monitored: true,
        permission: {
          permission_status: permissionStatus,
          notes: notes || 'Direct streamer consent',
          authorized_by: 'Owner added in dashboard',
        },
      });
      setShowAddModal(false);
      setChannelId('');
      setChannelUrl('');
      setDisplayName('');
      setNotes('');
    } catch (err: any) {
      alert(err.message || 'Failed to add streamer');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCheck = async (id: number) => {
    setCheckingId(id);
    try {
      await onCheckLive(id);
    } finally {
      setCheckingId(null);
    }
  };

  const handleInstantCapture = async (id: number) => {
    if (!onInstantCapture) return;
    setCapturingId(id);
    try {
      await onInstantCapture(id);
      alert('Capture started! We are recording a 60-second slice in the background. It will transcribe the audio, score for viral moments, and appear in Review shortly.');
    } catch (err: any) {
      alert(err.message || 'Capture slice failed');
    } finally {
      setCapturingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-white">Streamer Allowlist</h1>
          <p className="text-xs text-slate-400">
            Monitor authorized Twitch and YouTube channels for live GTA 6 streams.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-vice-pink to-vice-orange hover:opacity-95 text-white font-bold text-xs shadow-lg shadow-vice-pink/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          Add Streamer
        </button>
      </div>

      {/* Virality Modulation Info Banner */}
      <div className="p-4 rounded-2xl bg-vice-card border border-vice-border flex items-start gap-3 text-xs">
        <Flame className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-white flex items-center gap-2">
            <span>Strict Virality Modulation Active</span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30">
              Min Viral Score: 85/100
            </span>
          </div>
          <p className="text-slate-400">
            To prevent flooding storage and the publishing queue with boring clips, every 10-minute segment is strictly filtered. Only moments with crazy reactions, intense police pursuits, or hilarious actions score 85+ and get clipped. Standard cruising or casual chat produces zero clips.
          </p>
        </div>
      </div>

      {/* Streamers Table / Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {streamers.map((s) => {
          const perm = s.permissions?.[0];
          const isGranted = perm?.permission_status === 'granted';
          const isLive = s.live_status === 'live';

          return (
            <div
              key={s.id}
              className="p-5 rounded-2xl bg-vice-card border border-vice-border hover:border-slate-700 transition-all space-y-4 relative"
            >
              {/* Header: Platform & Live badge */}
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-vice-dark text-slate-400 border border-vice-border">
                  {s.platform}
                </span>
                <span
                  className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                    isLive
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 animate-pulse'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  {isLive ? 'Live Now' : 'Offline'}
                </span>
              </div>

              {/* Streamer Name & Channel Link */}
              <div>
                <h3 className="font-bold text-white text-base">{s.display_name}</h3>
                <a
                  href={s.channel_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-slate-400 hover:text-vice-cyan flex items-center gap-1 mt-0.5"
                >
                  <span>@{s.channel_id}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {/* Live Info if live */}
              {isLive && (
                <div className="p-2.5 rounded-xl bg-vice-dark/60 border border-emerald-500/20 text-xs space-y-1">
                  <p className="font-medium text-slate-200 line-clamp-1">{s.stream_title || 'Live GTA 6'}</p>
                  <p className="text-[11px] text-emerald-400 font-semibold">
                    {s.viewer_count.toLocaleString()} viewers &bull; Recording active
                  </p>
                </div>
              )}

              {/* Creator Permission Status Box */}
              <div className="p-3 rounded-xl bg-vice-dark border border-vice-border/80 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Shield className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-slate-400">Permission:</span>
                </div>
                <button
                  onClick={() => setSelectedStreamerForPerm(s)}
                  className={`font-semibold px-2 py-0.5 rounded text-[11px] border cursor-pointer hover:underline ${
                    isGranted
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {isGranted ? 'Granted' : 'Pending Consent'}
                </button>
              </div>

              {/* Actions Footer */}
              <div className="flex items-center justify-between pt-2 border-t border-vice-border/60 gap-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleCheck(s.id)}
                    disabled={checkingId === s.id}
                    className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 hover:text-white px-2.5 py-1.5 rounded-lg bg-vice-dark hover:bg-vice-hover border border-vice-border transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3 h-3 ${checkingId === s.id ? 'animate-spin' : ''}`} />
                    Check Live
                  </button>

                  {isLive && onInstantCapture && (
                    <button
                      onClick={() => handleInstantCapture(s.id)}
                      disabled={capturingId === s.id}
                      className="flex items-center gap-1.5 text-xs font-bold text-vice-cyan hover:text-white px-2.5 py-1.5 rounded-lg bg-vice-cyan/10 hover:bg-vice-cyan/20 border border-vice-cyan/30 transition-all disabled:opacity-50"
                      title="Test live capture: records a 60-second slice, transcribes, tests viral filter, and generates vertical clip"
                    >
                      <Radio className={`w-3 h-3 ${capturingId === s.id ? 'animate-pulse text-vice-pink' : ''}`} />
                      {capturingId === s.id ? 'Capturing 60s...' : 'Capture 60s Slice'}
                    </button>
                  )}
                </div>

                <button
                  onClick={() => {
                    if (confirm(`Remove ${s.display_name} from monitored streamers?`)) {
                      onDeleteStreamer(s.id);
                    }
                  }}
                  className="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                  title="Remove streamer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Streamer Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-vice-card border border-vice-border rounded-2xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-base font-bold text-white">Add Monitored Streamer</h2>
            <p className="text-xs text-slate-400">
              Only add streamers you have permission to clip according to your platform policy.
            </p>

            <form onSubmit={handleAddSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Platform</label>
                <select
                  value={platform}
                  onChange={(e: any) => setPlatform(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
                >
                  <option value="twitch">Twitch</option>
                  <option value="youtube">YouTube</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Channel Username / ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. shroud or kai_cenat"
                  value={channelId}
                  onChange={(e) => setChannelId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white placeholder-slate-600 focus:outline-none focus:border-vice-pink"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Display Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Shroud"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white placeholder-slate-600 focus:outline-none focus:border-vice-pink"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Creator Permission Status</label>
                <select
                  value={permissionStatus}
                  onChange={(e: any) => setPermissionStatus(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
                >
                  <option value="pending">Pending (Review only, no publishing yet)</option>
                  <option value="granted">Granted (Authorized for highlight publishing)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Permission Notes / License</label>
                <input
                  type="text"
                  placeholder="e.g. Permission granted via Discord / Creator license"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white placeholder-slate-600 focus:outline-none focus:border-vice-pink"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-vice-border">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl bg-vice-dark hover:bg-vice-hover text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-vice-pink to-vice-orange text-white font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Adding...' : 'Add Channel'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Permission Edit Modal */}
      {selectedStreamerForPerm && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-vice-card border border-vice-border rounded-2xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-base font-bold text-white">
              Creator Rights: {selectedStreamerForPerm.display_name}
            </h2>
            <p className="text-xs text-slate-400">
              Clips cannot be published unless creator permission is marked as Granted.
            </p>

            <div className="space-y-3 pt-2">
              <button
                onClick={async () => {
                  const permId = selectedStreamerForPerm.permissions?.[0]?.id;
                  if (permId) {
                    await onUpdatePermission(permId, { permission_status: 'granted' });
                    setSelectedStreamerForPerm(null);
                  }
                }}
                className="w-full p-3 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold text-left flex items-center justify-between"
              >
                <div>
                  <div className="font-bold">Set to Granted</div>
                  <div className="text-[11px] text-emerald-300/80 font-normal">
                    Creator gave rights to clip and publish highlights.
                  </div>
                </div>
                <CheckCircle2 className="w-5 h-5 shrink-0" />
              </button>

              <button
                onClick={async () => {
                  const permId = selectedStreamerForPerm.permissions?.[0]?.id;
                  if (permId) {
                    await onUpdatePermission(permId, { permission_status: 'pending' });
                    setSelectedStreamerForPerm(null);
                  }
                }}
                className="w-full p-3 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-bold text-left flex items-center justify-between"
              >
                <div>
                  <div className="font-bold">Set to Pending</div>
                  <div className="text-[11px] text-amber-300/80 font-normal">
                    Clips can be reviewed locally but cannot be posted to social channels.
                  </div>
                </div>
                <AlertCircle className="w-5 h-5 shrink-0" />
              </button>

              <button
                onClick={() => setSelectedStreamerForPerm(null)}
                className="w-full py-2 text-xs font-semibold text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
