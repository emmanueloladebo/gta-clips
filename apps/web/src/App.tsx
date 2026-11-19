import React, { useState, useEffect } from 'react';
import { api, getAuthToken, removeAuthToken } from './api';
import { Streamer, Clip, Candidate, DestinationAccount, PublishJob, StorageUsage, SystemMetrics, HealthStatus, AiModelSettings } from './types';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { OverviewView } from './components/OverviewView';
import { StreamersView } from './components/StreamersView';
import { ReviewView } from './components/ReviewView';
import { PublishingView } from './components/PublishingView';
import { StorageView } from './components/StorageView';
import { SettingsView } from './components/SettingsView';
import { LoginModal } from './components/LoginModal';

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(Boolean(getAuthToken()));
  const [currentTab, setCurrentTab] = useState<string>('overview');

  // Core Data States
  const [streamers, setStreamers] = useState<Streamer[]>([]);
  const [clips, setClips] = useState<Clip[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [destinations, setDestinations] = useState<DestinationAccount[]>([]);
  const [jobs, setJobs] = useState<PublishJob[]>([]);
  const [storage, setStorage] = useState<StorageUsage | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [autoPostEnabled, setAutoPostEnabled] = useState<boolean>(false);
  const [aiSettings, setAiSettings] = useState<AiModelSettings | null>(null);

  const fetchData = async () => {
    if (!isAuthenticated) return;
    try {
      const [
        streamersData,
        clipsData,
        candidatesData,
        destinationsData,
        jobsData,
        storageData,
        healthData,
        metricsData,
        autoPostData,
        aiSettingsData,
      ] = await Promise.allSettled([
        api.getStreamers(),
        api.getClips(),
        api.getCandidates(),
        api.getDestinations(),
        api.getPublishJobs(),
        api.getStorageUsage(),
        api.getHealth(),
        api.getMetrics(),
        api.getAutoPostStatus(),
        api.getAiModelSettings(),
      ]);

      if (streamersData.status === 'fulfilled') setStreamers(streamersData.value);
      if (clipsData.status === 'fulfilled') setClips(clipsData.value);
      if (candidatesData.status === 'fulfilled') setCandidates(candidatesData.value);
      if (destinationsData.status === 'fulfilled') setDestinations(destinationsData.value);
      if (jobsData.status === 'fulfilled') setJobs(jobsData.value);
      if (storageData.status === 'fulfilled') setStorage(storageData.value);
      if (healthData.status === 'fulfilled') setHealth(healthData.value);
      if (metricsData.status === 'fulfilled') setMetrics(metricsData.value);
      if (autoPostData.status === 'fulfilled') setAutoPostEnabled(autoPostData.value.auto_post_enabled);
      if (aiSettingsData.status === 'fulfilled') setAiSettings(aiSettingsData.value);
    } catch (err) {
      console.error('Fetch error:', err);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
      const interval = setInterval(fetchData, 10000); // 10s auto refresh
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const handleLogin = async (user: string, pass: string) => {
    await api.login(user, pass);
    setIsAuthenticated(true);
    fetchData();
  };

  const handleLogout = () => {
    removeAuthToken();
    setIsAuthenticated(false);
  };

  const handleAddStreamer = async (data: any) => {
    await api.addStreamer(data);
    await fetchData();
  };

  const handleCheckLive = async (id: number) => {
    await api.checkStreamerLive(id);
    await fetchData();
  };

  const handleToggleStreamerRecording = async (id: number) => {
    await api.toggleStreamerRecording(id);
    await fetchData();
  };

  const handleInstantCapture = async (id: number) => {
    await api.triggerInstantCapture(id, 60);
    await fetchData();
  };

  const handleUpdateStreamer = async (id: number, data: Partial<Streamer>) => {
    await api.updateStreamer(id, data);
    await fetchData();
  };

  const handleDeleteStreamer = async (id: number) => {
    await api.deleteStreamer(id);
    await fetchData();
  };

  const handleUpdatePermission = async (id: number, data: any) => {
    await api.updatePermission(id, data);
    await fetchData();
  };

  const handleReviewClip = async (id: number, action: 'approve' | 'reject', meta?: any) => {
    await api.reviewClip(id, action, meta);
    await fetchData();
  };

  const handleReRenderClip = async (id: number, headline: string, caption?: string, tags?: string) => {
    const updated = await api.reRenderClip(id, headline, caption, tags);
    await fetchData();
    return updated;
  };

  const handleAddDestination = async (data: any) => {
    await api.addDestination(data);
    await fetchData();
  };

  const handleDeleteDestination = async (id: number) => {
    await api.deleteDestination(id);
    await fetchData();
  };

  const handleSyncZernio = async () => {
    await api.syncZernioDestinations();
    await fetchData();
  };

  const handlePublishClip = async (clipId: number, destId: number) => {
    await api.publishClip(clipId, destId);
    await fetchData();
  };

  const handleRetryJob = async (jobId: number) => {
    await api.retryPublishJob(jobId);
    await fetchData();
  };

  const handleTriggerCleanup = async () => {
    const res = await api.triggerCleanup();
    await fetchData();
    return res;
  };

  const handleToggleRouter = async () => {
    const updated = await api.toggleRouterEngine();
    setAiSettings(updated);
  };

  const handleUpdateAiSettings = async (data: Partial<AiModelSettings>) => {
    const updated = await api.updateAiModelSettings(data);
    setAiSettings(updated);
  };

  const pendingClipsCount = clips.filter((c) => c.approval_status === 'pending_review').length;
  const liveStreamersCount = streamers.filter((s) => s.live_status === 'live').length;

  return (
    <div className="min-h-screen bg-vice-dark text-slate-100 flex flex-col">
      {!isAuthenticated && <LoginModal onLogin={handleLogin} />}

      <Header storage={storage} health={health} onLogout={handleLogout} />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          currentTab={currentTab}
          onTabChange={setCurrentTab}
          pendingClipsCount={pendingClipsCount}
          liveStreamersCount={liveStreamersCount}
        />

        <main className="flex-1 overflow-y-auto p-6 lg:p-8 max-w-7xl mx-auto w-full">
          {currentTab === 'overview' && (
            <OverviewView
              metrics={metrics}
              storage={storage}
              streamers={streamers}
              clips={clips}
              candidates={candidates}
              onSelectTab={setCurrentTab}
            />
          )}

          {currentTab === 'streamers' && (
            <StreamersView
              streamers={streamers}
              onAddStreamer={handleAddStreamer}
              onCheckLive={handleCheckLive}
              onToggleRecording={handleToggleStreamerRecording}
              onInstantCapture={handleInstantCapture}
              onDeleteStreamer={handleDeleteStreamer}
              onUpdatePermission={handleUpdatePermission}
              onUpdateStreamer={handleUpdateStreamer}
            />
          )}

          {currentTab === 'review' && (
            <ReviewView
              clips={clips}
              onReviewClip={handleReviewClip}
              onReRenderClip={handleReRenderClip}
            />
          )}

          {currentTab === 'publishing' && (
            <PublishingView
              destinations={destinations}
              jobs={jobs}
              clips={clips}
              autoPostEnabled={autoPostEnabled}
              onAddDestination={handleAddDestination}
              onDeleteDestination={handleDeleteDestination}
              onSyncZernio={handleSyncZernio}
              onPublishClip={handlePublishClip}
              onRetryJob={handleRetryJob}
            />
          )}

          {currentTab === 'storage' && (
            <StorageView storage={storage} onTriggerCleanup={handleTriggerCleanup} />
          )}

          {currentTab === 'settings' && (
            <SettingsView
              health={health}
              aiSettings={aiSettings}
              onToggleRouter={handleToggleRouter}
              onUpdateAiSettings={handleUpdateAiSettings}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
