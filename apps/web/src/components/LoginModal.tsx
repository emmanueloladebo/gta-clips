import React, { useState } from 'react';
import { Lock, LogIn } from 'lucide-react';

interface LoginModalProps {
  onLogin: (user: string, pass: string) => Promise<void>;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('GTA6ClipsPass!2026');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await onLogin(username, password);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-vice-card border border-vice-border rounded-3xl w-full max-w-sm p-7 space-y-6 shadow-2xl shadow-vice-pink/10">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-tr from-vice-pink to-vice-orange flex items-center justify-center font-black text-white text-xl shadow-lg shadow-vice-pink/20">
            VI
          </div>
          <h2 className="text-lg font-black text-white tracking-tight">Vice Clips Sign In</h2>
          <p className="text-xs text-slate-400">GTA 6 Cloud Highlight Platform</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 font-semibold mb-1">Username</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-vice-dark border border-vice-border text-white focus:outline-none focus:border-vice-pink"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-vice-pink to-vice-orange hover:opacity-95 text-white font-bold text-xs shadow-lg shadow-vice-pink/20 disabled:opacity-50 transition-all"
          >
            <LogIn className="w-4 h-4" />
            {isLoading ? 'Signing In...' : 'Sign In to Studio'}
          </button>
        </form>

        <div className="p-3 rounded-xl bg-vice-dark/60 border border-vice-border/60 text-[11px] text-slate-400 text-center">
          Default Admin: <span className="font-mono text-slate-200">admin</span> / <span className="font-mono text-slate-200">GTA6ClipsPass!2026</span>
        </div>
      </div>
    </div>
  );
};
