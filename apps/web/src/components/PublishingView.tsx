import React, { useState } from 'react';
import { Send, Plus, RefreshCw, CheckCircle2, Clock, AlertTriangle, ShieldCheck, ExternalLink } from 'lucide-react';
import { DestinationAccount, PublishJob, Clip } from '../types';

interface PublishingViewProps {
  destinations: DestinationAccount[];
  jobs: PublishJob[];
  clips: Clip[];
  autoPostEnabled: boolean;
  onAddDestination: (data: any) => Promise<void>;
  onSyncZernio?: () => Promise<void>;
  onPublishClip: (clipId: number, destId: number) => Promise<void>;
  onRetryJob: (jobId: number) => Promise<void>;
}

export const PublishingView: React.FC<PublishingViewProps> = ({
  destinations,
  jobs,
  clips,
  autoPostEnabled,
  onAddDestination,
  onSyncZernio,
  onPublishClip,
  onRetryJob,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [platform, setPlatform] = useState('tiktok');
  const [accountName, setAccountName] = useState('');
  const [externalId, setExternalId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [retryingId, setRetryingId] = useState<number | null>(null);

  // Manual publish modal
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [selectedClipId, setSelectedClipId] = useState<number>(clips[0]?.id || 0);
  const [selectedDestId, setSelectedDestId] = useState<number>(destinations[0]?.id || 0);

  const approvedClips = clips.filter((c) => c.approval_status === 'approved');

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accountName || !externalId) return;
    setIsSubmitting(true);
    try {
      await onAddDestination({
        platform,
        account_name: accountName,
        external_account_id: externalId,
        is_active: true,
        auto_post_enabled: false,
      });
      setShowAddModal(false);
      setAccountName('');
      setExternalId('');
    } catch (err: any) {
      alert(err.message || 'Failed to add destination');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleManualPublish = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClipId || !selectedDestId) return;
    setIsSubmitting(true);
    try {
      await onPublishClip(selectedClipId, selectedDestId);
      setShowPublishModal(false);
    } catch (err: any) {
      alert(err.message || 'Publishing failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetry = async (jobId: number) => {
    setRetryingId(jobId);
    try {
      await onRetryJob(jobId);
    } catch (err: any) {
      alert(err.message || 'Retry failed');
    } finally {
      setRetryingId(null);
    }
  };

  const handleSyncZernio = async () => {
    if (!onSyncZernio) return;
    setIsSyncing(true);
    try {
      await onSyncZernio();
    } catch (err: any) {
      alert(err.message || 'Syncing Zernio accounts failed');
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-black text-white">Publishing Hub</h1>
          <p className="text-xs text-slate-400">
            Schedule and publish approved GTA 6 vertical clips through Zernio.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {onSyncZernio && (
            <button
              onClick={handleSyncZernio}
              disabled={isSyncing}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-vice-dark hover:bg-vice-hover border border-vice-cyan/40 text-xs font-semibold text-vice-cyan disabled:opacity-50 transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
              {isSyncing ? 'Syncing...' : 'Sync Zernio Accounts'}
            </button>
          )}

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-vice-dark hover:bg-vice-hover border border-vice-border text-xs font-semibold text-slate-300"
          >
            <Plus className="w-4 h-4" />
            Connect Account
          </button>

          <button
            onClick={() => setShowPublishModal(true)}
            disabled={approvedClips.length === 0 || destinations.length === 0}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-vice-pink to-vice-orange hover:opacity-95 text-white font-bold text-xs shadow-lg shadow-vice-pink/20 disabled:opacity-50 transition-all"
          >
            <Send className="w-3.5 h-3.5" />
            Publish Approved Clip
          </button>
        </div>
      </div>

      {/* Safety Banner */}
      <div className="p-4 rounded-2xl bg-vice-card border border-vice-border flex items-start gap-3 text-xs">
        <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-white">Review-Before-Post Guard Active</div>
          <p className="text-slate-400">
            Auto-post is disabled by default. Every clip must have confirmed creator rights and explicit approval before submission to social networks.
          </p>
        </div>
      </div>

      {/* Connected Accounts Bar */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
          Connected Social Accounts ({destinations.length})
        </h3>
        {destinations.length === 0 ? (
          <div className="p-6 rounded-2xl bg-vice-card border border-vice-border text-center text-xs text-slate-400 space-y-2">
            <p>No publishing accounts connected yet.</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="font-semibold text-vice-pink hover:underline"
            >
              Connect YouTube Shorts, TikTok, or Instagram Reels &rarr;
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {destinations.map((dest) => (
              <div
                key={dest.id}
                className="p-4 rounded-2xl bg-vice-card border border-vice-border space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-vice-dark text-slate-400 border border-vice-border">
                    {dest.platform.replace('_', ' ')}
                  </span>
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                </div>
                <h4 className="font-bold text-white text-sm">{dest.account_name}</h4>
                <p className="text-[11px] text-slate-400">ID: {dest.external_account_id}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Publishing Jobs List */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Publish Queue & History ({jobs.length})
        </h3>

        {jobs.length === 0 ? (
          <div className="p-8 rounded-2xl bg-vice-card border border-vice-border text-center text-xs text-slate-400">
            No publish jobs yet. Approve a clip in the review station to send it here.
          </div>
        ) : (
          <div className="space-y-2">
            {jobs.map((job) => {
              const isPublished = job.status === 'published';
              const isFailed = job.status === 'failed';

              return (
                <div
                  key={job.id}
                  className="p-4 rounded-2xl bg-vice-card border border-vice-border flex items-center justify-between gap-4 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                          isPublished
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : isFailed
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        }`}
                      >
                        {job.status}
                      </span>
                      <span className="font-bold text-white">Clip #{job.clip_id}</span>
                      <span className="text-slate-400">&bull; {job.platform.replace('_', ' ')}</span>
                    </div>
                    {job.external_post_id && (
                      <p className="text-[11px] text-slate-400">
                        Zernio ID: <span className="font-mono text-slate-300">{job.external_post_id}</span>
                      </p>
                    )}
                    {job.error_message && (
                      <p className="text-[11px] text-rose-400">{job.error_message}</p>
                    )}
                  </div>

                  {isFailed && (
                    <button
                      onClick={() => handleRetry(job.id)}
                      disabled={retryingId === job.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 font-semibold"
                    >
                      <RefreshCw className={`w-3 h-3 ${retryingId === job.id ? 'animate-spin' : ''}`} />
                      Retry
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Connect Account Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-vice-card border border-vice-border rounded-2xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-base font-bold text-white">Connect Publishing Destination</h2>
            <form onSubmit={handleAddSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Platform</label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
                >
                  <option value="youtube_shorts">YouTube Shorts</option>
                  <option value="tiktok">TikTok</option>
                  <option value="instagram_reels">Instagram Reels</option>
                  <option value="x">X (Twitter)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Account Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. @GTA6DailyClips"
                  value={accountName}
                  onChange={(e) => setAccountName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">External Account ID</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. UC12345678 or tiktok_handle"
                  value={externalId}
                  onChange={(e) => setExternalId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
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
                  {isSubmitting ? 'Connecting...' : 'Connect Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Manual Publish Modal */}
      {showPublishModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-vice-card border border-vice-border rounded-2xl w-full max-w-md p-6 space-y-4">
            <h2 className="text-base font-bold text-white">Publish Approved Clip</h2>
            <form onSubmit={handleManualPublish} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Select Approved Clip</label>
                <select
                  value={selectedClipId}
                  onChange={(e) => setSelectedClipId(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
                >
                  {approvedClips.map((c) => (
                    <option key={c.id} value={c.id}>
                      #{c.id}: {c.title} ({c.duration_seconds.toFixed(0)}s)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Select Destination</label>
                <select
                  value={selectedDestId}
                  onChange={(e) => setSelectedDestId(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
                >
                  {destinations.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.account_name} ({d.platform.replace('_', ' ')})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-vice-border">
                <button
                  type="button"
                  onClick={() => setShowPublishModal(false)}
                  className="px-4 py-2 rounded-xl bg-vice-dark hover:bg-vice-hover text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-vice-pink to-vice-orange text-white font-bold disabled:opacity-50"
                >
                  {isSubmitting ? 'Publishing...' : 'Publish Now'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
