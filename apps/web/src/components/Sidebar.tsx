import React from 'react';
import { Radio, Users, Film, Send, HardDrive, Sliders, PlayCircle } from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  pendingClipsCount: number;
  liveStreamersCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  pendingClipsCount,
  liveStreamersCount,
}) => {
  const navItems = [
    {
      id: 'overview',
      label: 'Live Feeds',
      icon: Radio,
      badge: liveStreamersCount > 0 ? `${liveStreamersCount} live` : null,
      badgeColor: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    },
    {
      id: 'streamers',
      label: 'Streamers',
      icon: Users,
    },
    {
      id: 'review',
      label: 'Review Clips',
      icon: Film,
      badge: pendingClipsCount > 0 ? `${pendingClipsCount}` : null,
      badgeColor: 'bg-vice-pink/20 text-vice-pink border-vice-pink/30',
    },
    {
      id: 'publishing',
      label: 'Publishing',
      icon: Send,
    },
    {
      id: 'storage',
      label: 'Storage & Retention',
      icon: HardDrive,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: Sliders,
    },
  ];

  return (
    <aside className="w-64 border-r border-vice-border bg-vice-card flex flex-col justify-between p-4 shrink-0">
      <div className="space-y-6">
        <div>
          <p className="px-3 text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Navigation
          </p>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-vice-pink/15 to-transparent text-white border-l-4 border-vice-pink font-bold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-vice-dark/60'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${isActive ? 'text-vice-pink' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${item.badgeColor}`}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Quick cloud stats box */}
        <div className="p-3.5 rounded-xl bg-vice-dark border border-vice-border text-xs space-y-2">
          <div className="flex items-center gap-2 text-slate-300 font-bold">
            <PlayCircle className="w-3.5 h-3.5 text-vice-cyan" />
            <span>Cloud Highlight Pipeline</span>
          </div>
          <p className="text-slate-400 text-[11px] leading-relaxed">
            Running automated capture on cloud worker. Clips are kept for 24 hours only.
          </p>
        </div>
      </div>

      <div className="pt-4 border-t border-vice-border/60 text-[11px] text-slate-400 space-y-1">
        <p className="font-semibold text-slate-300">GTA 6 Clipping Platform</p>
        <p>Production Cloud Edition</p>
      </div>
    </aside>
  );
};
