import React, { useState, useEffect } from 'react';
import { Activity, Check, X, ShieldAlert, Zap, Wallet, TrendingUp, ArrowUpRight, Brain, Copy, CheckCheck, Clock, History, Octagon } from 'lucide-react';

// --- DIAGNOSTIC LiveTimer Component ---
const LiveTimer = ({ startTime }) => {
  const [elapsed, setElapsed] = useState('Loading...');

  useEffect(() => {
    if (!startTime) {
       setElapsed('API Data Missing');
       return;
    }

    const updateTimer = () => {
      const now = Date.now();
      const safeString = String(startTime).split('.')[0].replace(' ', 'T');
      let startMs = new Date(safeString + 'Z').getTime();

      if (startMs > now) {
        startMs = new Date(safeString).getTime(); 
      }

      let diffInSeconds = Math.floor((now - startMs) / 1000);

      if (isNaN(diffInSeconds)) {
        setElapsed('Format Error');
        return;
      }

      if (diffInSeconds < 0) {
        setElapsed('Time Desync');
        return;
      }

      const h = Math.floor(diffInSeconds / 3600);
      const m = Math.floor((diffInSeconds % 3600) / 60);
      const s = diffInSeconds % 60;
      
      if (h > 0) {
        setElapsed(`${h}h ${m}m ${s}s`);
      } else {
        setElapsed(`${m}m ${s}s`);
      }
    };

    updateTimer();
    const intervalId = setInterval(updateTimer, 1000);
    return () => clearInterval(intervalId);
  }, [startTime]);

  return <span className="font-mono tracking-wider text-amber-400 font-bold">{elapsed}</span>;
};

export default function App() {
  const [pendingTrades, setPendingTrades] = useState([]);
  const [activeTrades, setActiveTrades] = useState([]);
  const [closedTrades, setClosedTrades] = useState([]); // --- NEW STATE ---
  
  const [startingCapital, setStartingCapital] = useState(() => {
    const saved = localStorage.getItem('vibe_trading_capital');
    return saved ? parseFloat(saved) : 10000;
  });
  const [loading, setLoading] = useState(true);
  const [copiedField, setCopiedField] = useState(null);

  const handleCapitalChange = (e) => {
    const val = parseFloat(e.target.value) || 0;
    setStartingCapital(val);
    localStorage.setItem('vibe_trading_capital', val);
  };

  const handleCopy = (text, fieldId) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldId);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const fetchDashboardData = async () => {
    try {
      const pendingRes = await fetch('/api/trades/pending');
      if (pendingRes.ok) setPendingTrades(await pendingRes.json());

      const activeRes = await fetch('/api/trades/active');
      if (activeRes.ok) setActiveTrades(await activeRes.json());

      // --- NEW FETCH CALL ---
      const closedRes = await fetch('/api/trades/closed');
      if (closedRes.ok) setClosedTrades(await closedRes.json());

    } catch (error) {
      console.error("Dashboard connection sync failed:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 3000); 
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (id, actionType) => {
    try {
      await fetch(`/api/trades/${id}/${actionType}`, { method: 'POST' });
      fetchDashboardData();
    } catch (error) {
      console.error(`Failed to execute ${actionType} on trade #${id}`, error);
    }
  };

  // --- NEW MATH ---
  const totalActivePnL = activeTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
  const totalClosedPnL = closedTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
  
  const realizedCapital = startingCapital + totalClosedPnL; // Money actually in your pocket
  const liveValuation = realizedCapital + totalActivePnL; // Money if you closed everything right now

  return (
    <div className="min-h-screen p-8 font-sans bg-slate-950 text-slate-100 pb-20">
      
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
            <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Live Valuation (Inc. Open PnL)</p>
            <p className={`text-3xl font-black ${liveValuation >= startingCapital ? 'text-emerald-400' : 'text-rose-400'}`}>
              ₹{liveValuation.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <TrendingUp className={`w-10 h-10 ${liveValuation >= startingCapital ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Today's Realized PnL</p>
            <p className={`text-3xl font-black ${totalClosedPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {totalClosedPnL >= 0 ? '+' : ''}₹{totalClosedPnL.toFixed(2)}
            </p>
          </div>
          <ArrowUpRight className={`w-10 h-10 ${totalClosedPnL >= 0 ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
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
                <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col xl:flex-row items-center justify-between hover:border-slate-700 transition-colors shadow-lg">
                  <div className="flex-1 w-full">
                    
                    <div className="flex flex-wrap items-center gap-3 mb-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                        {trade.action}
                      </span>
                      <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                      <span className="text-[11px] text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800/60">
                        ⏱️ Signal Received: {new Date(trade.created_at + 'Z').toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                      
                      <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Entry Target</p>
                          <p className="font-semibold text-slate-300 font-mono">₹{trade.entry_price}</p>
                        </div>
                        <button onClick={() => handleCopy(trade.entry_price, `${trade.id}-entry`)} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors" title="Copy Entry">
                          {copiedField === `${trade.id}-entry` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
                        </button>
                      </div>

                      <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Take Profit</p>
                          <p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p>
                        </div>
                        <button onClick={() => handleCopy(trade.take_profit, `${trade.id}-tp`)} className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 rounded transition-colors" title="Copy Take Profit">
                          {copiedField === `${trade.id}-tp` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
                        </button>
                      </div>

                      <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Stop Loss</p>
                          <p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p>
                        </div>
                        <button onClick={() => handleCopy(trade.stop_loss, `${trade.id}-sl`)} className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-700 rounded transition-colors" title="Copy Stop Loss">
                          {copiedField === `${trade.id}-sl` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
                        </button>
                      </div>

                      <div className="flex flex-col justify-center p-2 rounded bg-slate-900 border border-slate-800">
                        <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Size</p>
                        <p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex gap-3 xl:ml-6 mt-4 xl:mt-0 w-full xl:w-auto">
                    <button onClick={() => handleAction(trade.id, 'approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-3 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/20">
                      <Check className="w-5 h-5" /> Deploy
                    </button>
                    <button 
                      onClick={() => handleAction(trade.id, 'reject')} 
                      title="Mark as Not Executed"
                      className="bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white px-4 py-3 rounded-lg font-bold transition-all border border-transparent"
                    >
                      <X className="w-5 h-5" />
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
                <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors shadow-lg relative overflow-hidden">
                  
                  {/* --- NEW: FORCE STOP BUTTON --- */}
                  <div className="absolute top-4 right-4">
                     <button 
                        onClick={() => handleAction(trade.id, 'emergency_stop')}
                        className="bg-rose-500/10 hover:bg-rose-600 text-rose-400 hover:text-white px-3 py-1.5 rounded text-xs font-bold transition-all flex items-center gap-1.5 border border-rose-500/20 hover:border-transparent shadow-lg"
                      >
                        <Octagon className="w-3.5 h-3.5" /> Force Kill
                      </button>
                  </div>

                  <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-800 pb-3 pr-24">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                        {trade.action}
                      </span>
                      <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                      
                      <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded font-semibold animate-pulse border border-blue-500/20 uppercase tracking-wider">
                        🛡️ AI Protected
                      </span>
                      
                      <span className="text-[11px] flex items-center gap-1 text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700">
                        <Clock className="w-3 h-3 text-slate-400" />
                        Held: <LiveTimer startTime={trade.activated_at || trade.created_at} />
                      </span>
                    </div>

                    <p className={`text-lg font-black mt-2 md:mt-0 ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm mb-4">
                    <div><p className="text-slate-500 text-xs">Size</p><p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p></div>
                    <div><p className="text-slate-500 text-xs">Bought At</p><p className="font-semibold font-mono">₹{trade.entry_price}</p></div>
                    <div><p className="text-slate-500 text-xs">Live Price</p><p className="font-semibold text-blue-400 font-mono">₹{trade.live_price || trade.entry_price}</p></div>
                    <div><p className="text-slate-500 text-xs">Target</p><p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p></div>
                    <div><p className="text-slate-500 text-xs">Active Stop</p><p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p></div>
                    <div><p className="text-slate-500 text-xs">RSI / MACD</p><p className="font-mono text-[10px] text-amber-400 mt-0.5">{trade.live_rsi || '--'} | {trade.live_macd || '--'}</p></div>
                  </div>

                  <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs flex items-start gap-2 text-slate-400">
                    <span className="font-bold text-blue-400 uppercase tracking-wider text-[10px] bg-blue-500/10 px-1.5 py-0.5 rounded mt-0.5 shrink-0">AI Reasoning</span>
                    <p className="leading-relaxed">
                      {trade.risk_reasoning || "Risk manager analyzing current market structural alignment. Maintaining stop parameters unchanged."}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* --- SECTION 3: NEW TODAY'S CLOSED TRADES --- */}
        <div>
          <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2 mt-4">
            <History className="text-purple-400 w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Today's Closed Trades</h2>
          </div>

          {closedTrades.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
              No trades finalized today. Let the AI work!
            </div>
          ) : (
            <div className="grid gap-3">
              {closedTrades.map(trade => (
                <div key={trade.id} className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 flex flex-col md:flex-row items-center justify-between opacity-80 hover:opacity-100 transition-opacity">
                  <div className="flex items-center gap-4 w-full md:w-auto mb-3 md:mb-0">
                    <span className={`px-2 py-1 rounded text-[10px] font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/10 text-rose-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
                      {trade.action}
                    </span>
                    <span className="text-lg font-bold text-white">{trade.ticker}</span>
                    
                    {/* Parse out exactly how it was closed */}
                    <span className="text-[10px] text-slate-400 uppercase font-bold border border-slate-700 px-2 py-0.5 rounded bg-slate-950">
                      {trade.status.replace('CLOSED_', '')}
                    </span>
                  </div>

                  <div className="flex items-center gap-8 w-full md:w-auto text-sm">
                    <div className="flex flex-col text-right">
                      <span className="text-slate-500 text-[10px] uppercase">Entry</span>
                      <span className="font-mono text-slate-300">₹{trade.entry_price}</span>
                    </div>
                    <div className="flex flex-col text-right">
                      <span className="text-slate-500 text-[10px] uppercase">Exit</span>
                      <span className="font-mono text-slate-300">₹{trade.live_price || trade.entry_price}</span>
                    </div>
                    <div className="flex flex-col text-right min-w-[80px]">
                      <span className="text-slate-500 text-[10px] uppercase">Final PnL</span>
                      <span className={`font-black text-lg ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}>
                        {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
                      </span>
                    </div>
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