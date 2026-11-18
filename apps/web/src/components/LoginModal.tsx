import React, { useState } from 'react';
import { Lock, LogIn } from 'lucide-react';

interface LoginModalProps {
  onLogin: (user: string, pass: string) => Promise<void>;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setIsLoading(true);
    setError(null);
    try {
      await onLogin(username.trim(), password);
    } catch (err: any) {
      setError(err.message || 'Invalid username or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-xl flex items-center justify-center p-4">
      <div className="bg-[#11141f]/95 border border-white/[0.08] rounded-3xl w-full max-w-sm p-8 space-y-6 shadow-2xl shadow-black/80">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-gradient-to-tr from-vice-pink to-vice-orange flex items-center justify-center font-black text-white text-xl shadow-lg shadow-vice-pink/20">
            VI
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">Studio Sign In</h2>
          <p className="text-xs text-slate-400">GTA 6 Cloud Highlight Platform</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs text-center font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1.5 text-xs">Username</label>
            <input
              type="text"
              required
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white placeholder-slate-500 text-sm focus:outline-none focus:border-vice-pink/70 transition-all"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1.5 text-xs">Password</label>
            <input
              type="password"
              required
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white placeholder-slate-500 text-sm focus:outline-none focus:border-vice-pink/70 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !username || !password}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-gradient-to-r from-vice-pink to-vice-orange hover:opacity-95 text-white font-bold text-sm shadow-lg shadow-vice-pink/20 disabled:opacity-40 transition-all mt-2 cursor-pointer"
          >
            <LogIn className="w-4 h-4" />
            {isLoading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};
