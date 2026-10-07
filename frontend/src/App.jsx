import React, { useState, useEffect } from 'react';
import { 
  Activity, Check, X, ShieldAlert, Zap, Wallet, TrendingUp, ArrowUpRight, 
  Brain, Copy, CheckCheck, Clock, History, Octagon, Settings, 
  Globe, Compass, CheckCircle2, Ban, Newspaper, AlertTriangle, ChevronRight, Layers,
  Lock, ShieldCheck
} from 'lucide-react';

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

// --- Risk Scan Circular Loader ---
const RiskScanLoader = ({ now }) => {
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  
  const secondsElapsedInBlock = (minutes % 5) * 60 + seconds;
  const progressPercent = (secondsElapsedInBlock / 300) * 100;
  const secondsLeft = 300 - secondsElapsedInBlock;

  const radius = 6;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progressPercent / 100) * circumference;

  return (
    <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-md text-[11px] font-mono text-slate-400 select-none shadow-sm">
      <span>Auto-Squareoff in {Math.floor(secondsLeft / 60)}m {secondsLeft % 60}s</span>
      <div className="relative w-4 h-4 flex items-center justify-center">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 16 16">
          <circle cx="8" cy="8" r={radius} stroke="currentColor" strokeWidth="2" fill="none" className="text-slate-800" />
          <circle 
            cx="8" 
            cy="8" 
            r={radius} 
            stroke="currentColor" 
            strokeWidth="2" 
            fill="none" 
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="text-blue-400 transition-all duration-1000 ease-linear shadow-[0_0_5px_rgba(96,165,250,0.5)]" 
          />
        </svg>
      </div>
    </div>
  );
};

// --- Helper for Closed Trades Hold Time ---
const formatHoldTime = (start, end) => {
  if (!start || !end) return "--";
  const safeStart = String(start).endsWith('Z') ? start : start + 'Z';
  const safeEnd = String(end).endsWith('Z') ? end : end + 'Z';
  
  const startMs = new Date(safeStart).getTime();
  const endMs = new Date(safeEnd).getTime();
  
  if (isNaN(startMs) || isNaN(endMs)) return "--";

  const diffSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000));
  
  const h = Math.floor(diffSeconds / 3600);
  const m = Math.floor((diffSeconds % 3600) / 60);
  
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
};

// --- Helper for HH:MM AM/PM Display ---
const formatTime = (isoString) => {
  if (!isoString) return "--:--";
  const safeString = String(isoString).endsWith('Z') ? isoString : isoString + 'Z';
  const d = new Date(safeString);
  if (isNaN(d.getTime())) return "--:--";
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
};

// --- Helper to Generate 15-Minute Timeline Slots (9:15 AM to 3:30 PM) ---
const generateMarketSlots = () => {
  const slots = [];
  for (let h = 9; h <= 15; h++) {
    for (let m = 0; m < 60; m += 15) {
      if (h === 9 && m < 15) continue; 
      if (h === 15 && m > 30) continue; 
      
      const hour = h.toString().padStart(2, '0');
      const min = m.toString().padStart(2, '0');
      
      const isPM = h >= 12;
      const displayH = h > 12 ? (h === 12 ? 12 : h - 12) : h;
      const displayTime = `${displayH.toString().padStart(2, '0')}:${min} ${isPM ? 'PM' : 'AM'}`;
      
      slots.push({ key: `${hour}:${min}`, displayTime, trades: [] });
    }
  }
  return slots;
};

export default function App() {
  const [pendingTrades, setPendingTrades] = useState([]);
  const [activeTrades, setActiveTrades] = useState([]);
  const [closedTrades, setClosedTrades] = useState([]);
  const [macroPlaybook, setMacroPlaybook] = useState(null);
  const [cooldowns, setCooldowns] = useState([]);
  
  const [autoDeploy, setAutoDeploy] = useState(false);
  const [startingCapital, setStartingCapital] = useState(10000);
  const [loading, setLoading] = useState(true);
  const [copiedField, setCopiedField] = useState(null);

  // --- Real-time clock ---
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleCapitalChange = async (e) => {
    const val = parseFloat(e.target.value) || 0;
    setStartingCapital(val); 
    
    try {
      await fetch('/api/account/capital', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_capital: val })
      });
    } catch (error) {
      console.error("Failed to update capital in database", error);
    }
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

      const closedRes = await fetch('/api/trades/closed');
      if (closedRes.ok) setClosedTrades(await closedRes.json());

      const macroRes = await fetch('/api/macro/playbook');
      if (macroRes.ok) setMacroPlaybook(await macroRes.json());

      const cdRes = await fetch('/api/cooldown/all');
      if (cdRes.ok) setCooldowns(await cdRes.json());

      const autoDeployRes = await fetch('/api/account/auto_deploy');
      if (autoDeployRes.ok) {
        const adData = await autoDeployRes.json();
        setAutoDeploy(adData.auto_deploy);
      }

      const capitalRes = await fetch('/api/account/capital');
      if (capitalRes.ok) {
        const capData = await capitalRes.json();
        if (document.activeElement.type !== "number") {
            setStartingCapital(capData.current_capital);
        }
      }

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

  const toggleAutoDeploy = async () => {
    const newState = !autoDeploy;
    setAutoDeploy(newState);
    try {
      await fetch('/api/account/auto_deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_deploy: newState })
      });
    } catch (error) {
      console.error("Failed to update auto_deploy", error);
      setAutoDeploy(!newState);
    }
  };

  const sortedClosedTrades = [...closedTrades].sort((a, b) => {
    const timeA = new Date((a.activated_at || a.created_at) + 'Z').getTime();
    const timeB = new Date((b.activated_at || b.created_at) + 'Z').getTime();
    return timeB - timeA;
  });

  const totalActivePnL = activeTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
  const totalClosedPnL = closedTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
  
  // Calculate realistic guaranteed/locked PnL from dynamic Trailing SL across active trades
  const totalLockedActivePnL = activeTrades.reduce((acc, trade) => {
    const isShort = trade.action?.includes('SHORT');
    const entry = Number(trade.entry_price) || 0;
    const sl = Number(trade.stop_loss) || 0;
    const sizing = Number(trade.sizing) || 0;
    const slDelta = isShort ? (entry - sl) : (sl - entry);
    return acc + (slDelta * sizing);
  }, 0);

  const realisticFloorPnL = totalClosedPnL + totalLockedActivePnL;
  const realizedCapital = startingCapital + totalClosedPnL; 
  const liveValuation = realizedCapital + totalActivePnL; 

  // --- GROUP ACTIVE TRADES INTO 15-MIN TIMELINE ---
  const activeTimeline = generateMarketSlots();
  
  activeTrades.forEach(trade => {
    const timeStr = trade.activated_at || trade.created_at;
    if (!timeStr) return;
    
    const safeString = String(timeStr).endsWith('Z') ? timeStr : timeStr + 'Z';
    const d = new Date(safeString);
    if (isNaN(d.getTime())) return;
    
    const h = d.getHours();
    const m = d.getMinutes();
    
    const bucketM = Math.floor(m / 15) * 15;
    const slotKey = `${h.toString().padStart(2, '0')}:${bucketM.toString().padStart(2, '0')}`;
    
    const slot = activeTimeline.find(s => s.key === slotKey);
    if (slot) {
      slot.trades.push(trade);
    }
  });

  return (
    <div className="min-h-screen p-8 font-sans bg-slate-950 text-slate-100 pb-20 overflow-x-hidden">
      
      {/* Top Navigation Bar */}
      <header className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between border-b border-slate-800 pb-6 mb-8">
        <div className="flex items-center gap-3">
          <Zap className="text-amber-400 w-8 h-8 fill-amber-400/20" />
          <h1 className="text-3xl font-black tracking-wider bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            VIBE TRADING
          </h1>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 px-4 py-2 rounded-full shadow-inner">
            <Settings className={`w-4 h-4 ${autoDeploy ? 'text-amber-400 animate-spin-slow' : 'text-slate-500'}`} style={{ animationDuration: '4s' }} />
            <span className={`text-xs font-bold tracking-wider ${autoDeploy ? 'text-slate-200' : 'text-slate-500'}`}>
              AUTO DEPLOY
            </span>
            <button 
              onClick={toggleAutoDeploy}
              className={`ml-2 w-10 h-5 rounded-full relative transition-colors ${autoDeploy ? 'bg-amber-500' : 'bg-slate-700'}`}
            >
              <div className={`w-3.5 h-3.5 bg-white rounded-full absolute top-[3px] transition-all ${autoDeploy ? 'left-[22px]' : 'left-[3px]'}`} />
            </button>
          </div>

          <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full text-sm font-semibold border border-emerald-500/20 shadow-inner hidden md:flex">
            <Activity className="w-4 h-4 animate-pulse" />
            Quant Core Active
          </div>
        </div>
      </header>

      {/* Financial Health Matrix */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 max-w-6xl mx-auto">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Starting Capital</p>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 text-lg font-bold">₹</span>
              <input 
                type="number" 
                value={startingCapital} 
                onChange={handleCapitalChange}
                className="bg-slate-950 border border-slate-700 rounded px-2.5 py-0.5 text-xl font-bold text-white focus:outline-none focus:border-amber-500 w-36 transition-colors font-mono"
              />
            </div>
          </div>
          <Wallet className="w-8 h-8 text-slate-600 shrink-0" />
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Live Valuation (Floating)</p>
            <p className={`text-2xl font-black font-mono ${liveValuation >= startingCapital ? 'text-emerald-400' : 'text-rose-400'}`}>
              ₹{liveValuation.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
            <p className="text-[10px] text-slate-500">Unrealized: {totalActivePnL >= 0 ? '+' : ''}₹{totalActivePnL.toFixed(2)}</p>
          </div>
          <TrendingUp className={`w-8 h-8 ${liveValuation >= startingCapital ? 'text-emerald-500/40' : 'text-rose-500/40'} shrink-0`} />
        </div>

        <div className="bg-slate-900 border border-amber-500/30 rounded-xl p-5 shadow-xl flex items-center justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 w-2 h-full bg-amber-500/40" />
          <div>
            <p className="text-amber-400 text-xs font-bold uppercase tracking-wider mb-1 flex items-center gap-1">
              <Lock className="w-3.5 h-3.5 text-amber-400" />
              Realistic SL Day Floor
            </p>
            <p className={`text-2xl font-black font-mono ${realisticFloorPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {realisticFloorPnL >= 0 ? '+' : ''}₹{realisticFloorPnL.toFixed(2)}
            </p>
            <p className="text-[10px] text-slate-400">Guaranteed if SLs hit now</p>
          </div>
          <ShieldCheck className={`w-8 h-8 ${realisticFloorPnL >= 0 ? 'text-emerald-400/40' : 'text-amber-400/40'} shrink-0`} />
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Today's Realized PnL</p>
            <p className={`text-2xl font-black font-mono ${totalClosedPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {totalClosedPnL >= 0 ? '+' : ''}₹{totalClosedPnL.toFixed(2)}
            </p>
            <p className="text-[10px] text-slate-500">{closedTrades.length} Closed Trades</p>
          </div>
          <ArrowUpRight className={`w-8 h-8 ${totalClosedPnL >= 0 ? 'text-emerald-500/40' : 'text-rose-500/40'} shrink-0`} />
        </div>
      </div>

      {/* NEW: MACRO CIO INTELLIGENCE & SECTOR EXPLAINABILITY CARD */}
      <div className="max-w-6xl mx-auto mb-10">
        <div className="bg-gradient-to-br from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
          
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-4 mb-5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                <Compass className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white tracking-wide flex items-center gap-2">
                  MACRO CIO INTELLIGENCE & SECTOR BREADTH
                  <span className="text-[10px] bg-blue-500/20 text-blue-300 font-mono px-2 py-0.5 rounded-full border border-blue-500/30">
                    Live News & Quant Engine
                  </span>
                </h2>
                <p className="text-xs text-slate-400">Pre-market global cues, sector breadth & real-time catalyst analysis</p>
              </div>
            </div>

            {/* Regime & Risk Badges */}
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg">
                <span className="text-[10px] uppercase font-bold text-slate-500">Regime:</span>
                <span className={`text-xs font-black tracking-wider ${
                  macroPlaybook?.market_regime === 'BULLISH' ? 'text-emerald-400' :
                  macroPlaybook?.market_regime === 'BEARISH' ? 'text-rose-400' : 'text-amber-400'
                }`}>
                  {macroPlaybook?.market_regime || 'ANALYZING...'}
                </span>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg">
                <span className="text-[10px] uppercase font-bold text-slate-500">Risk Appetite:</span>
                <span className={`text-xs font-black tracking-wider ${
                  macroPlaybook?.risk_level === 'AGGRESSIVE' ? 'text-emerald-400' :
                  macroPlaybook?.risk_level === 'DEFENSIVE' ? 'text-rose-400' : 'text-blue-400'
                }`}>
                  {macroPlaybook?.risk_level || 'MODERATE'}
                </span>
              </div>
            </div>
          </div>

          {/* Sector Allocation & News Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Left 6 cols: Approved & Banned Sectors Visual Radar */}
            <div className="lg:col-span-6 flex flex-col justify-between space-y-4">
              <div>
                <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  Approved Sectors (Active Hunt List)
                </p>
                <div className="flex flex-wrap gap-2">
                  {macroPlaybook?.approved_sectors?.length > 0 ? (
                    macroPlaybook.approved_sectors.map(sec => (
                      <span key={sec} className="px-3 py-1 rounded-lg text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        {sec}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-500 italic">No approved sectors active</span>
                  )}
                </div>
              </div>

              <div>
                <p className="text-[11px] font-bold text-rose-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                  <Ban className="w-4 h-4 text-rose-400" />
                  Banned Sectors & Penalty Box
                </p>
                <div className="flex flex-wrap gap-2">
                  {macroPlaybook?.banned_sectors?.length > 0 ? (
                    macroPlaybook.banned_sectors.map(sec => (
                      <span key={sec} className="px-3 py-1 rounded-lg text-xs font-bold bg-rose-500/15 text-rose-300 border border-rose-500/30 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                        {sec} (Macro Risk)
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-500 italic">No sectors banned</span>
                  )}

                  {/* Cooldown penalty box tickers */}
                  {cooldowns?.map(cd => (
                    <span key={cd.ticker} className="px-3 py-1 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-amber-400" />
                      {cd.ticker} (Cooldown)
                    </span>
                  ))}
                </div>
              </div>

              {/* Macro Summary Reasoning Box */}
              <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800/80">
                <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-1">CIO Market Summary</p>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {macroPlaybook?.reasoning || "Scanning market data and news feeds..."}
                </p>
              </div>
            </div>

            {/* Right 6 cols: Live News Headlines Feed */}
            <div className="lg:col-span-6 bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 flex flex-col justify-between">
              <div className="flex items-center justify-between mb-3 border-b border-slate-800/60 pb-2">
                <p className="text-[11px] font-bold text-slate-300 uppercase tracking-widest flex items-center gap-1.5">
                  <Newspaper className="w-4 h-4 text-blue-400" />
                  Live Indian Financial Media Catalyst Stream
                </p>
                <span className="text-[10px] text-slate-500 font-mono">15m Refresh</span>
              </div>

              <div className="space-y-2.5 overflow-y-auto max-h-[160px] pr-1">
                {macroPlaybook?.top_headlines?.length > 0 ? (
                  macroPlaybook.top_headlines.slice(0, 4).map((item, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs text-slate-300 hover:text-white transition-colors group">
                      <ChevronRight className="w-3.5 h-3.5 text-blue-400 mt-0.5 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                      <div className="flex-1">
                        <p className="line-clamp-1 font-medium">{item.title}</p>
                        <p className="text-[10px] text-slate-500">{item.source || "Financial Media"}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 italic">Streaming live financial headlines...</p>
                )}
              </div>
            </div>

          </div>

        </div>
      </div>

      {/* Workspace Grid */}
      <div className="grid grid-cols-1 gap-10 max-w-6xl mx-auto">
        
        {/* SECTION 1: PENDING SIGNALS */}
        <div>
          <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
            <ShieldAlert className="text-amber-500 w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Pending Signals</h2>
          </div>

          {loading ? (
            <p className="text-slate-500 animate-pulse text-sm">Decoding transmission...</p>
          ) : pendingTrades.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
              {autoDeploy ? "Auto-Deploy is ON. Signals will bypass this queue and activate instantly." : "No active pending signals. Waiting for market setup conditions..."}
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
                        ⏱️ Signal Received: {formatTime(trade.created_at)}
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
                          <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Initial SL</p>
                          <p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p>
                        </div>
                        <button onClick={() => handleCopy(trade.stop_loss, `${trade.id}-sl`)} className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-700 rounded transition-colors" title="Copy Stop Loss">
                          {copiedField === `${trade.id}-sl` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
                        </button>
                      </div>

                      <div className="flex flex-col justify-center p-2 rounded bg-slate-900 border border-slate-800">
                        <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">SL Delta (Max Risk)</p>
                        <p className="font-semibold text-rose-400 font-mono text-xs">
                          -₹{Math.abs(trade.action?.includes('SHORT') ? (trade.stop_loss - trade.entry_price) : (trade.entry_price - trade.stop_loss)).toFixed(2)}
                          <span className="text-[10px] text-slate-400 font-medium ml-1">
                            (-₹{(Math.abs(trade.action?.includes('SHORT') ? (trade.stop_loss - trade.entry_price) : (trade.entry_price - trade.stop_loss)) * trade.sizing).toFixed(2)})
                          </span>
                        </p>
                      </div>

                      <div className="flex flex-col justify-center p-2 rounded bg-slate-900 border border-slate-800">
                        <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Size (Units)</p>
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

        {/* SECTION 2: LIVE PROGRESS TIMELINE */}
        <div>
          <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
            <Brain className="text-blue-400 w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Active Risk Engine Watch</h2>
          </div>

          <div className="relative ml-20 md:ml-24 pb-4 mt-6">
            {activeTimeline.map((slot, index) => {
              const [hourStr, minStr] = slot.key.split(':');
              const slotStart = new Date(now);
              slotStart.setHours(parseInt(hourStr), parseInt(minStr), 0, 0);

              const slotEnd = new Date(slotStart);
              slotEnd.setMinutes(slotStart.getMinutes() + 15);

              const nowMs = now.getTime();
              const startMs = slotStart.getTime();
              const endMs = slotEnd.getTime();

              let status = 'future';
              let progress = 0;

              if (nowMs >= endMs) {
                status = 'past';
                progress = 100;
              } else if (nowMs >= startMs && nowMs < endMs) {
                status = 'present';
                progress = ((nowMs - startMs) / (endMs - startMs)) * 100;
              }

              const isPast = status === 'past';
              const isPresent = status === 'present';

              return (
                <div key={slot.key} className="relative mb-8 last:mb-0 pl-6 md:pl-8 min-h-[60px]">
                  
                  {index < activeTimeline.length - 1 && (
                    <div 
                      className={`absolute left-[7px] top-[14px] bottom-[-32px] w-[2px] transition-colors duration-500 ${
                        isPast ? 'bg-emerald-500/50' : 'bg-slate-800'
                      }`} 
                    />
                  )}

                  <div className="absolute -left-20 md:-left-24 top-0 w-16 text-right font-mono text-xs text-slate-500 font-semibold select-none">
                    {slot.displayTime}
                  </div>

                  <div className="absolute left-0 top-[2px] w-4 h-4 flex items-center justify-center">
                    {isPast && (
                      <div className="w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                    )}
                    {isPresent && (
                      <div className="relative w-4 h-4 flex items-center justify-center">
                        <div className="absolute w-full h-full rounded-full bg-blue-500/30 animate-ping" />
                        <div className="w-3 h-3 rounded-full bg-blue-500 ring-4 ring-blue-500/20 shadow-[0_0_10px_rgba(59,130,246,0.8)]" />
                      </div>
                    )}
                    {!isPast && !isPresent && (
                      <div className="w-2.5 h-2.5 rounded-full bg-slate-800 ring-2 ring-slate-900" />
                    )}
                  </div>

                  <div className="flex flex-col gap-3">
                    {isPresent && (
                      <div className="flex items-center gap-3">
                        <RiskScanLoader now={now} />
                      </div>
                    )}

                    {slot.trades.length > 0 ? (
                      <div className="grid gap-3">
                        {slot.trades.map(trade => {
                          const isShort = trade.action?.includes('SHORT');
                          const entry = Number(trade.entry_price) || 0;
                          const livePrice = Number(trade.live_price || trade.entry_price) || 0;
                          const sl = Number(trade.stop_loss) || 0;
                          const sizing = Number(trade.sizing) || 0;

                          // Difference between Trailing SL and Entry (Realistic outcome if stopped out right now)
                          const slDeltaPerShare = isShort ? (entry - sl) : (sl - entry);
                          const lockedFloorPnL = slDeltaPerShare * sizing;
                          const isProfitLocked = slDeltaPerShare > 0;

                          // Floating unrealized PnL (Live Price vs Entry)
                          const liveDeltaPerShare = isShort ? (entry - livePrice) : (livePrice - entry);
                          const floatingPnL = Number(trade.current_pnl) || (liveDeltaPerShare * sizing);

                          return (
                            <div 
                              key={trade.id} 
                              className="bg-slate-900 border border-slate-700/80 rounded-xl p-4 shadow-xl flex flex-col items-start justify-between gap-3 border-l-4 border-l-blue-500"
                            >
                              <div className="w-full">
                                <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
                                  <div className="flex items-center gap-3">
                                    <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${
                                      isShort ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
                                    }`}>
                                      {trade.action}
                                    </span>
                                    <span className="text-lg font-bold text-white tracking-wide">{trade.ticker}</span>
                                    <span className="text-xs text-slate-400 font-mono">({sizing} Units)</span>
                                    
                                    <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 px-2 py-0.5 rounded text-xs text-slate-400">
                                      <Clock className="w-3 h-3 text-slate-500" />
                                      <LiveTimer startTime={trade.activated_at} />
                                    </div>
                                  </div>

                                  {/* Realistic SL Exit Outcome Badge */}
                                  <div className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-black tracking-wide border shadow-sm ${
                                    isProfitLocked 
                                      ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' 
                                      : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                                  }`}>
                                    {isProfitLocked ? (
                                      <>
                                        <Lock className="w-3.5 h-3.5 text-emerald-400" />
                                        <span>SL Locked Floor: +₹{lockedFloorPnL.toFixed(2)}</span>
                                      </>
                                    ) : (
                                      <>
                                        <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                                        <span>SL Max Risk: -₹{Math.abs(lockedFloorPnL).toFixed(2)}</span>
                                      </>
                                    )}
                                  </div>
                                </div>

                                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-3 text-xs bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                                  <div>
                                    <span className="text-slate-500 block uppercase text-[9px] font-bold">Entry Price</span>
                                    <span className="font-mono text-slate-300 font-semibold">₹{entry.toFixed(2)}</span>
                                  </div>
                                  <div>
                                    <span className="text-slate-500 block uppercase text-[9px] font-bold">Live Price</span>
                                    <span className="font-mono text-white font-bold">₹{livePrice.toFixed(2)}</span>
                                  </div>
                                  <div>
                                    <span className="text-slate-500 block uppercase text-[9px] font-bold">Dynamic Trailed SL</span>
                                    <span className="font-mono text-rose-400 font-bold">₹{sl.toFixed(2)}</span>
                                  </div>
                                  <div>
                                    <span className="text-slate-500 block uppercase text-[9px] font-bold">SL ➔ Entry Delta</span>
                                    <span className={`font-mono font-bold ${slDeltaPerShare >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                      {slDeltaPerShare >= 0 ? '+' : ''}₹{slDeltaPerShare.toFixed(2)} <span className="text-[9px] text-slate-500 font-normal">/ unit</span>
                                    </span>
                                  </div>
                                  <div>
                                    <span className="text-slate-500 block uppercase text-[9px] font-bold">Realistic Floor PnL</span>
                                    <span className={`font-mono font-black ${lockedFloorPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                      {lockedFloorPnL >= 0 ? '+' : ''}₹{lockedFloorPnL.toFixed(2)}
                                      <span className="text-[9px] text-slate-500 block font-normal">
                                        (Live: {floatingPnL >= 0 ? '+' : ''}₹{floatingPnL.toFixed(2)})
                                      </span>
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-xs text-slate-600 italic select-none py-1">
                        {isPast ? "No positions triggered in this cycle" : isPresent ? "Watching live order book..." : "Scheduled scan window"}
                      </div>
                    )}
                  </div>

                </div>
              );
            })}
          </div>
        </div>

        {/* SECTION 3: CLOSED TRADES */}
        <div>
          <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
            <History className="text-slate-400 w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Trade Execution History</h2>
          </div>

          {sortedClosedTrades.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
              No executed trades archived for today.
            </div>
          ) : (
            <div className="grid gap-3">
              {sortedClosedTrades.map(trade => (
                <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${
                        trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
                      }`}>
                        {trade.action}
                      </span>
                      <span className="text-lg font-bold text-white tracking-wide">{trade.ticker}</span>
                      <span className="text-xs text-slate-400 font-mono">({trade.sizing} Units)</span>
                      
                      <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                        trade.status === 'CLOSED_TRAILING_STOP' ? 'bg-emerald-500/20 text-emerald-400' :
                        trade.status === 'CLOSED_CUT_LOSS' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {trade.status.replace('CLOSED_', '')}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-3 text-xs bg-slate-950 p-2.5 rounded-lg border border-slate-800/60">
                      <div>
                        <span className="text-slate-500 block uppercase text-[9px] font-bold">Entry</span>
                        <span className="font-mono text-slate-300">₹{trade.entry_price}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block uppercase text-[9px] font-bold">Exit</span>
                        <span className="font-mono text-slate-300">₹{trade.live_price || trade.entry_price}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block uppercase text-[9px] font-bold">Hold Time</span>
                        <span className="font-mono text-amber-400 font-semibold">{formatHoldTime(trade.activated_at, trade.closed_at)}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block uppercase text-[9px] font-bold">Realized PnL</span>
                        <span className={`font-mono font-bold ${trade.current_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {trade.current_pnl >= 0 ? '+' : ''}₹{trade.current_pnl || '0.00'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block uppercase text-[9px] font-bold">Exit Time</span>
                        <span className="font-mono text-slate-400">{formatTime(trade.closed_at)}</span>
                      </div>
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