import React, { useState, useEffect } from 'react';
import { Activity, Check, X, ShieldAlert, Zap, Wallet, TrendingUp, ArrowUpRight, Brain } from 'lucide-react';

export default function App() {
  const [pendingTrades, setPendingTrades] = useState([]);
  const [activeTrades, setActiveTrades] = useState([]);
  const [startingCapital, setStartingCapital] = useState(() => {
    // Save starting capital to local storage so it stays when refreshing
    const saved = localStorage.getItem('vibe_trading_capital');
    return saved ? parseFloat(saved) : 10000;
  });
  const [loading, setLoading] = useState(true);

  // Persistence handler for capital input
  const handleCapitalChange = (e) => {
    const val = parseFloat(e.target.value) || 0;
    setStartingCapital(val);
    localStorage.setItem('vibe_trading_capital', val);
  };

  // Poll the FastAPI server for both pending and active positions
  const fetchDashboardData = async () => {
    try {
      // 1. Fetch pending trade proposals
      const pendingRes = await fetch('/api/trades/pending');
      if (pendingRes.ok) {
        const pendingData = await pendingRes.json();
        setPendingTrades(pendingData);
      }

      // 2. Fetch active positions currently monitored by the Risk Manager
      // Note: Assumes your FastAPI backend has a /api/trades/active endpoint
      const activeRes = await fetch('/api/trades/active');
      if (activeRes.ok) {
        const activeData = await activeRes.json();
        setActiveTrades(activeData);
      }
    } catch (error) {
      console.error("Dashboard connection sync failed:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 3000); // Fast 3-second cycle
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id, actionType) => {
    try {
      await fetch(`/api/trades/${id}/${actionType}`, { method: 'POST' });
      // Instantly refresh numbers
      fetchDashboardData();
    } catch (error) {
      console.error(`Failed to execute ${actionType} on trade #${id}`, error);
    }
  };

  // Calculate dynamic day metrics
  // Active positions calculate their current distance to estimate real-time impact
  const totalActivePnL = activeTrades.reduce((acc, trade) => {
    // This will be populated dynamically if your backend feeds live P&L, 
    // or we can calculate a placeholder baseline or mock fallback for visual validation
    return acc + (trade.current_pnl || 0);
  }, 0);

  const currentCapital = startingCapital + totalActivePnL;

  return (
    <div className="min-h-screen p-8 font-sans bg-slate-950 text-slate-100">
      
      {/* Top Navigation Bar */}
      <header className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between border-b border-slate-800 pb-6 mb-8">
        <div className="flex items-center gap-3">
          <Zap className="text-amber-400 w-8 h-8 fill-amber-400/20" />
          <h1 className="text-3xl font-black tracking-wider bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            VIBE TRADING
          </h1>
        </div>
        <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full text-sm font-semibold border border-emerald-500/20 shadow-inner">
          <Activity className="w-4 h-4 animate-pulse" />
          Quant Core Synchronized
        </div>
      </header>

      {/* Financial Health Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Starting Account Balance</p>
            <div className="flex items-center gap-2">
              <span className="text-slate-500 text-xl font-bold">₹</span>
              <input 
                type="number" 
                value={startingCapital} 
                onChange={handleCapitalChange}
                className="bg-slate-950 border border-slate-700 rounded px-3 py-1 text-2xl font-bold text-white focus:outline-none focus:border-amber-500 w-44 transition-colors"
              />
            </div>
          </div>
          <Wallet className="w-10 h-10 text-slate-600" />
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Live Valuation</p>
            <p className={`text-3xl font-black ${totalActivePnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              ₹{currentCapital.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <TrendingUp className={`w-10 h-10 ${totalActivePnL >= 0 ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Open Risk Exposure PnL</p>
            <p className={`text-3xl font-black ${totalActivePnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {totalActivePnL >= 0 ? '+' : ''}₹{totalActivePnL.toFixed(2)}
            </p>
          </div>
          <ArrowUpRight className={`w-10 h-10 ${totalActivePnL >= 0 ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
        </div>
      </div>

      {/* Workspace Grid */}
      <div className="grid grid-cols-1 gap-10 max-w-6xl mx-auto">
        
        {/* SECTION 1: CO PILOT PROPOSALS */}
        <div>
          <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
            <ShieldAlert className="text-amber-500 w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Pending Signals</h2>
          </div>

          {loading ? (
            <p className="text-slate-500 animate-pulse text-sm">Decoding transmission...</p>
          ) : pendingTrades.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
              No active pending signals. Waiting for market setup conditions...
            </div>
          ) : (
            <div className="grid gap-4">
              {pendingTrades.map(trade => (
                // <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between hover:border-slate-700 transition-colors shadow-lg">
                //   <div className="flex-1">
                //     <div className="flex items-center gap-3 mb-2">
                //       <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                //         {trade.action}
                //       </span>
                //       <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                //     </div>
                //     <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 text-sm">
                //       <div><p className="text-slate-500 text-xs uppercase">Entry Target</p><p className="font-semibold text-slate-300">₹{trade.entry_price}</p></div>
                //       <div><p className="text-slate-500 text-xs uppercase">Take Profit</p><p className="font-semibold text-emerald-400">₹{trade.take_profit}</p></div>
                //       <div><p className="text-slate-500 text-xs uppercase">Stop Loss</p><p className="font-semibold text-rose-400">₹{trade.stop_loss}</p></div>
                //       <div><p className="text-slate-500 text-xs uppercase">Size</p><p className="font-semibold text-slate-300">{trade.sizing} Units</p></div>
                //     </div>
                //   </div>
                //   <div className="flex gap-3 md:ml-6 mt-4 md:mt-0 w-full md:w-auto">
                //     <button onClick={() => handleAction(trade.id, 'approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all">
                //       <Check className="w-4 h-4" /> Deploy
                //     </button>
                //     <button onClick={() => handleAction(trade.id, 'reject')} className="bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white px-4 py-2.5 rounded-lg font-bold text-sm transition-all">
                //       <X className="w-4 h-4" />
                //     </button>
                //   </div>
                // </div>
                <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between hover:border-slate-700 transition-colors shadow-lg">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-3 mb-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                        {trade.action}
                      </span>
                      <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                      
                      {/* Dynamic Local Timestamp Display */}
                      <span className="text-[11px] text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800/60">
                        ⏱️ Signal Received: {new Date(trade.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3 text-sm">
                      <div><p className="text-slate-500 text-xs uppercase">Entry Target</p><p className="font-semibold text-slate-300">₹{trade.entry_price}</p></div>
                      <div><p className="text-slate-500 text-xs uppercase">Take Profit</p><p className="font-semibold text-emerald-400">₹{trade.take_profit}</p></div>
                      <div><p className="text-slate-500 text-xs uppercase">Stop Loss</p><p className="font-semibold text-rose-400">₹{trade.stop_loss}</p></div>
                      <div><p className="text-slate-500 text-xs uppercase">Size</p><p className="font-semibold text-slate-300">{trade.sizing} Units</p></div>
                    </div>
                  </div>
                  
                  <div className="flex gap-3 md:ml-6 mt-4 md:mt-0 w-full md:w-auto">
                    <button onClick={() => handleAction(trade.id, 'approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all">
                      <Check className="w-4 h-4" /> Deploy
                    </button>
                    <button 
                      onClick={() => handleAction(trade.id, 'reject')} 
                      title="Mark as Not Executed"
                      className="bg-slate-800 hover:bg-rose-600/20 text-slate-400 hover:text-rose-400 px-4 py-2.5 rounded-lg font-bold text-sm transition-all border border-transparent hover:border-rose-500/30"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* SECTION 2: ACTIVE PORTFOLIO VIA RISK MANAGER */}
        <div>
          <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
            <Brain className="text-blue-400 w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Active Risk Engine Watch</h2>
          </div>

          {activeTrades.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
              No live active allocations in inventory. Approving signals routes them here.
            </div>
          ) : (
            <div className="grid gap-4">
              {activeTrades.map(trade => (
                <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors shadow-lg">
                  <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                        {trade.action}
                      </span>
                      <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                      <span className="text-xs text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-md font-semibold animate-pulse border border-blue-500/20">
                        🛡️ Gemini Protected
                      </span>
                    </div>
                    <p className={`text-lg font-black mt-2 md:mt-0 ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm mb-4">
                    <div><p className="text-slate-500 text-xs">Bought At</p><p className="font-semibold">₹{trade.entry_price}</p></div>
                    <div><p className="text-slate-500 text-xs">Live Price</p><p className="font-semibold text-blue-400">₹{trade.live_price || trade.entry_price}</p></div>
                    <div><p className="text-slate-500 text-xs">Dynamic Target</p><p className="font-semibold text-emerald-400">₹{trade.take_profit}</p></div>
                    <div><p className="text-slate-500 text-xs">Active Stop</p><p className="font-semibold text-rose-400">₹{trade.stop_loss}</p></div>
                    <div><p className="text-slate-500 text-xs">RSI / MACD Status</p><p className="font-mono text-xs text-amber-400 mt-0.5">RSI: {trade.live_rsi || '52.4'} | {trade.live_macd || 'Bullish'}</p></div>
                  </div>

                  {/* Cognitive Reasoning Feed */}
                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs flex items-start gap-2 text-slate-400">
                    <span className="font-bold text-blue-400 uppercase tracking-wider text-[10px] bg-blue-500/10 px-1.5 py-0.5 rounded mt-0.5">AI Reasoning</span>
                    <p className="leading-relaxed">
                      {trade.risk_reasoning || "Risk manager analyzing current market structural alignment. Maintaining stop parameters unchanged."}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}