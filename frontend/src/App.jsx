// import React, { useState, useEffect } from 'react';
// import { Activity, Check, X, ShieldAlert, Zap, Wallet, TrendingUp, ArrowUpRight, Brain, Copy, CheckCheck, Clock, History, Octagon, Settings } from 'lucide-react';

// // --- DIAGNOSTIC LiveTimer Component ---
// const LiveTimer = ({ startTime }) => {
//   const [elapsed, setElapsed] = useState('Loading...');

//   useEffect(() => {
//     if (!startTime) {
//        setElapsed('API Data Missing');
//        return;
//     }

//     const updateTimer = () => {
//       const now = Date.now();
//       const safeString = String(startTime).split('.')[0].replace(' ', 'T');
//       let startMs = new Date(safeString + 'Z').getTime();

//       if (startMs > now) {
//         startMs = new Date(safeString).getTime(); 
//       }

//       let diffInSeconds = Math.floor((now - startMs) / 1000);

//       if (isNaN(diffInSeconds)) {
//         setElapsed('Format Error');
//         return;
//       }

//       if (diffInSeconds < 0) {
//         setElapsed('Time Desync');
//         return;
//       }

//       const h = Math.floor(diffInSeconds / 3600);
//       const m = Math.floor((diffInSeconds % 3600) / 60);
//       const s = diffInSeconds % 60;
      
//       if (h > 0) {
//         setElapsed(`${h}h ${m}m ${s}s`);
//       } else {
//         setElapsed(`${m}m ${s}s`);
//       }
//     };

//     updateTimer();
//     const intervalId = setInterval(updateTimer, 1000);
//     return () => clearInterval(intervalId);
//   }, [startTime]);

//   return <span className="font-mono tracking-wider text-amber-400 font-bold">{elapsed}</span>;
// };

// // --- Helper for Closed Trades Hold Time (Fixed NaN issue) ---
// const formatHoldTime = (start, end) => {
//   if (!start || !end) return "--";
//   const safeStart = String(start).endsWith('Z') ? start : start + 'Z';
//   const safeEnd = String(end).endsWith('Z') ? end : end + 'Z';
  
//   const startMs = new Date(safeStart).getTime();
//   const endMs = new Date(safeEnd).getTime();
  
//   if (isNaN(startMs) || isNaN(endMs)) return "--";

//   const diffSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000));
  
//   const h = Math.floor(diffSeconds / 3600);
//   const m = Math.floor((diffSeconds % 3600) / 60);
  
//   if (h > 0) return `${h}h ${m}m`;
//   return `${m}m`;
// };

// // --- Helper for HH:MM AM/PM Display ---
// const formatTime = (isoString) => {
//   if (!isoString) return "--:--";
//   const safeString = String(isoString).endsWith('Z') ? isoString : isoString + 'Z';
//   const d = new Date(safeString);
//   if (isNaN(d.getTime())) return "--:--";
//   return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
// };

// export default function App() {
//   const [pendingTrades, setPendingTrades] = useState([]);
//   const [activeTrades, setActiveTrades] = useState([]);
//   const [closedTrades, setClosedTrades] = useState([]);
  
//   const [autoDeploy, setAutoDeploy] = useState(false);

//   // --- THE FIX 1: Simplify initial state ---
//   const [startingCapital, setStartingCapital] = useState(10000);
//   const [loading, setLoading] = useState(true);
//   const [copiedField, setCopiedField] = useState(null);

//   // --- THE FIX 2: Update database when you type a new capital amount ---
//   const handleCapitalChange = async (e) => {
//     const val = parseFloat(e.target.value) || 0;
//     setStartingCapital(val); 
    
//     try {
//       await fetch('/api/account/capital', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ current_capital: val })
//       });
//     } catch (error) {
//       console.error("Failed to update capital in database", error);
//     }
//   };

//   const handleCopy = (text, fieldId) => {
//     navigator.clipboard.writeText(text);
//     setCopiedField(fieldId);
//     setTimeout(() => setCopiedField(null), 2000);
//   };

//   const fetchDashboardData = async () => {
//     try {
//       const pendingRes = await fetch('/api/trades/pending');
//       if (pendingRes.ok) setPendingTrades(await pendingRes.json());

//       const activeRes = await fetch('/api/trades/active');
//       if (activeRes.ok) setActiveTrades(await activeRes.json());

//       const closedRes = await fetch('/api/trades/closed');
//       if (closedRes.ok) setClosedTrades(await closedRes.json());

//       const autoDeployRes = await fetch('/api/account/auto_deploy');
//       if (autoDeployRes.ok) {
//         const adData = await autoDeployRes.json();
//         setAutoDeploy(adData.auto_deploy);
//       }

//       // --- THE FIX 3: Fetch live capital from DB continuously ---
//       const capitalRes = await fetch('/api/account/capital');
//       if (capitalRes.ok) {
//         const capData = await capitalRes.json();
//         // Only override the UI state if the user is not actively typing in the box
//         if (document.activeElement.type !== "number") {
//             setStartingCapital(capData.current_capital);
//         }
//       }

//     } catch (error) {
//       console.error("Dashboard connection sync failed:", error);
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchDashboardData();
//     const interval = setInterval(fetchDashboardData, 3000); 
//     return () => clearInterval(interval);
//   }, []);

//   const handleAction = async (id, actionType) => {
//     try {
//       await fetch(`/api/trades/${id}/${actionType}`, { method: 'POST' });
//       fetchDashboardData();
//     } catch (error) {
//       console.error(`Failed to execute ${actionType} on trade #${id}`, error);
//     }
//   };

//   const toggleAutoDeploy = async () => {
//     const newState = !autoDeploy;
//     setAutoDeploy(newState);
//     try {
//       await fetch('/api/account/auto_deploy', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ auto_deploy: newState })
//       });
//     } catch (error) {
//       console.error("Failed to update auto_deploy", error);
//       setAutoDeploy(!newState);
//     }
//   };

//   // --- SORT BY ENTRY TIME (Newest at the top) ---
//   const sortedClosedTrades = [...closedTrades].sort((a, b) => {
//     const timeA = new Date((a.activated_at || a.created_at) + 'Z').getTime();
//     const timeB = new Date((b.activated_at || b.created_at) + 'Z').getTime();
//     return timeB - timeA;
//   });

//   const totalActivePnL = activeTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
//   const totalClosedPnL = closedTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
  
//   const realizedCapital = startingCapital + totalClosedPnL; 
//   const liveValuation = realizedCapital + totalActivePnL; 

//   return (
//     <div className="min-h-screen p-8 font-sans bg-slate-950 text-slate-100 pb-20 overflow-x-hidden">
      
//       {/* Top Navigation Bar */}
//       <header className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between border-b border-slate-800 pb-6 mb-8">
//         <div className="flex items-center gap-3">
//           <Zap className="text-amber-400 w-8 h-8 fill-amber-400/20" />
//           <h1 className="text-3xl font-black tracking-wider bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
//             VIBE TRADING
//           </h1>
//         </div>
        
//         <div className="flex items-center gap-4">
//           <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 px-4 py-2 rounded-full shadow-inner">
//             <Settings className={`w-4 h-4 ${autoDeploy ? 'text-amber-400 animate-spin-slow' : 'text-slate-500'}`} style={{ animationDuration: '4s' }} />
//             <span className={`text-xs font-bold tracking-wider ${autoDeploy ? 'text-slate-200' : 'text-slate-500'}`}>
//               AUTO DEPLOY
//             </span>
//             <button 
//               onClick={toggleAutoDeploy}
//               className={`ml-2 w-10 h-5 rounded-full relative transition-colors ${autoDeploy ? 'bg-amber-500' : 'bg-slate-700'}`}
//             >
//               <div className={`w-3.5 h-3.5 bg-white rounded-full absolute top-[3px] transition-all ${autoDeploy ? 'left-[22px]' : 'left-[3px]'}`} />
//             </button>
//           </div>

//           <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full text-sm font-semibold border border-emerald-500/20 shadow-inner hidden md:flex">
//             <Activity className="w-4 h-4 animate-pulse" />
//             Quant Core Active
//           </div>
//         </div>
//       </header>

//       {/* Financial Health Matrix */}
//       <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Starting Account Balance</p>
//             <div className="flex items-center gap-2">
//               <span className="text-slate-500 text-xl font-bold">₹</span>
//               <input 
//                 type="number" 
//                 value={startingCapital} 
//                 onChange={handleCapitalChange}
//                 className="bg-slate-950 border border-slate-700 rounded px-3 py-1 text-2xl font-bold text-white focus:outline-none focus:border-amber-500 w-44 transition-colors"
//               />
//             </div>
//           </div>
//           <Wallet className="w-10 h-10 text-slate-600" />
//         </div>

//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Live Valuation (Inc. Open PnL)</p>
//             <p className={`text-3xl font-black ${liveValuation >= startingCapital ? 'text-emerald-400' : 'text-rose-400'}`}>
//               ₹{liveValuation.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
//             </p>
//           </div>
//           <TrendingUp className={`w-10 h-10 ${liveValuation >= startingCapital ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
//         </div>

//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Today's Realized PnL</p>
//             <p className={`text-3xl font-black ${totalClosedPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
//               {totalClosedPnL >= 0 ? '+' : ''}₹{totalClosedPnL.toFixed(2)}
//             </p>
//           </div>
//           <ArrowUpRight className={`w-10 h-10 ${totalClosedPnL >= 0 ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
//         </div>
//       </div>

//       {/* Workspace Grid */}
//       <div className="grid grid-cols-1 gap-10 max-w-6xl mx-auto">
        
//         {/* SECTION 1: CO PILOT PROPOSALS */}
//         <div>
//           <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
//             <ShieldAlert className="text-amber-500 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Pending Signals</h2>
//           </div>

//           {loading ? (
//             <p className="text-slate-500 animate-pulse text-sm">Decoding transmission...</p>
//           ) : pendingTrades.length === 0 ? (
//             <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
//               {autoDeploy ? "Auto-Deploy is ON. Signals will bypass this queue and activate instantly." : "No active pending signals. Waiting for market setup conditions..."}
//             </div>
//           ) : (
//             <div className="grid gap-4">
//               {pendingTrades.map(trade => (
//                 <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col xl:flex-row items-center justify-between hover:border-slate-700 transition-colors shadow-lg">
//                   <div className="flex-1 w-full">
                    
//                     <div className="flex flex-wrap items-center gap-3 mb-2">
//                       <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
//                         {trade.action}
//                       </span>
//                       <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
//                       <span className="text-[11px] text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800/60">
//                         ⏱️ Signal Received: {formatTime(trade.created_at)}
//                       </span>
//                     </div>
                    
//                     <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                      
//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Entry Target</p>
//                           <p className="font-semibold text-slate-300 font-mono">₹{trade.entry_price}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.entry_price, `${trade.id}-entry`)} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors" title="Copy Entry">
//                           {copiedField === `${trade.id}-entry` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Take Profit</p>
//                           <p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.take_profit, `${trade.id}-tp`)} className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 rounded transition-colors" title="Copy Take Profit">
//                           {copiedField === `${trade.id}-tp` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Stop Loss</p>
//                           <p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.stop_loss, `${trade.id}-sl`)} className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-700 rounded transition-colors" title="Copy Stop Loss">
//                           {copiedField === `${trade.id}-sl` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex flex-col justify-center p-2 rounded bg-slate-900 border border-slate-800">
//                         <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Size</p>
//                         <p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p>
//                       </div>
//                     </div>
//                   </div>
                  
//                   <div className="flex gap-3 xl:ml-6 mt-4 xl:mt-0 w-full xl:w-auto">
//                     <button onClick={() => handleAction(trade.id, 'approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-3 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/20">
//                       <Check className="w-5 h-5" /> Deploy
//                     </button>
//                     <button 
//                       onClick={() => handleAction(trade.id, 'reject')} 
//                       title="Mark as Not Executed"
//                       className="bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white px-4 py-3 rounded-lg font-bold transition-all border border-transparent"
//                     >
//                       <X className="w-5 h-5" />
//                     </button>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//         {/* SECTION 2: ACTIVE PORTFOLIO VIA RISK MANAGER */}
//         <div>
//           <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
//             <Brain className="text-blue-400 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Active Risk Engine Watch</h2>
//           </div>

//           {activeTrades.length === 0 ? (
//             <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
//               No live active allocations in inventory.
//             </div>
//           ) : (
//             <div className="grid gap-4">
//               {activeTrades.map(trade => (
//                 <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors shadow-lg relative overflow-hidden">
                  
//                   {/* FORCE STOP BUTTON */}
//                   <div className="absolute top-4 right-4">
//                      <button 
//                         onClick={() => handleAction(trade.id, 'emergency_stop')}
//                         className="bg-rose-500/10 hover:bg-rose-600 text-rose-400 hover:text-white px-3 py-1.5 rounded text-xs font-bold transition-all flex items-center gap-1.5 border border-rose-500/20 hover:border-transparent shadow-lg"
//                       >
//                         <Octagon className="w-3.5 h-3.5" /> Force Kill
//                       </button>
//                   </div>

//                   <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-800 pb-3 pr-24">
//                     <div className="flex flex-wrap items-center gap-3">
//                       <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
//                         {trade.action}
//                       </span>
//                       <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                      
//                       <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded font-semibold animate-pulse border border-blue-500/20 uppercase tracking-wider">
//                         🛡️ AI Protected
//                       </span>
                      
//                       <span className="text-[11px] flex items-center gap-1 text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700">
//                         <Clock className="w-3 h-3 text-slate-400" />
//                         Held: <LiveTimer startTime={trade.activated_at || trade.created_at} />
//                       </span>
//                     </div>

//                     <p className={`text-lg font-black mt-2 md:mt-0 ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
//                       {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
//                     </p>
//                   </div>

//                   <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm mb-4">
//                     <div><p className="text-slate-500 text-xs">Size</p><p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p></div>
//                     <div><p className="text-slate-500 text-xs">Bought At</p><p className="font-semibold font-mono">₹{trade.entry_price}</p></div>
//                     <div><p className="text-slate-500 text-xs">Live Price</p><p className="font-semibold text-blue-400 font-mono">₹{trade.live_price || trade.entry_price}</p></div>
//                     <div><p className="text-slate-500 text-xs">Target</p><p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p></div>
//                     <div><p className="text-slate-500 text-xs">Active Stop</p><p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p></div>
//                     <div><p className="text-slate-500 text-xs">RSI / MACD</p><p className="font-mono text-[10px] text-amber-400 mt-0.5">{trade.live_rsi || '--'} | {trade.live_macd || '--'}</p></div>
//                   </div>

//                   <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs flex items-start gap-2 text-slate-400">
//                     <span className="font-bold text-blue-400 uppercase tracking-wider text-[10px] bg-blue-500/10 px-1.5 py-0.5 rounded mt-0.5 shrink-0">AI Reasoning</span>
//                     <p className="leading-relaxed">
//                       {trade.risk_reasoning || "Risk manager analyzing current market structural alignment. Maintaining stop parameters unchanged."}
//                     </p>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//         {/* --- SECTION 3: NEW TIMELINE TRADING LOG --- */}
//         <div>
//           <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-2 mt-4">
//             <History className="text-purple-400 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Today's Closed Trades</h2>
//           </div>

//           {sortedClosedTrades.length === 0 ? (
//             <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
//               No trades finalized today. Let the AI work!
//             </div>
//           ) : (
//             <div className="relative ml-20 md:ml-24 border-l-2 border-slate-800/60 pb-4">
//               {sortedClosedTrades.map((trade, index) => (
//                 <div key={trade.id} className="relative mb-6 last:mb-0 pl-6 md:pl-8">
                  
//                   {/* Timeline Dot */}
//                   <div className="absolute -left-[9px] top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-slate-950 border-2 border-slate-700 flex items-center justify-center z-10">
//                     <div className={`w-1.5 h-1.5 rounded-full ${(trade.current_pnl || 0) >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`} />
//                   </div>

//                   {/* Bought Time (Extreme Left) */}
//                   <div className="absolute -left-[85px] md:-left-[95px] top-1/2 -translate-y-1/2 w-16 md:w-20 text-right">
//                     <div className="text-xs font-bold text-slate-300">
//                       {formatTime(trade.activated_at || trade.created_at)}
//                     </div>
//                     <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mt-0.5">Entry</div>
//                   </div>

//                   {/* Trade Card */}
//                   <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 flex flex-col xl:flex-row items-center justify-between opacity-80 hover:opacity-100 transition-opacity shadow-sm hover:shadow-md">
                    
//                     {/* Left Side of Card */}
//                     <div className="flex flex-col md:flex-row items-start md:items-center gap-3 w-full xl:w-auto mb-4 xl:mb-0">
//                       <div className="flex items-center gap-3">
//                         <span className={`px-2 py-1 rounded text-[10px] font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/10 text-rose-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
//                           {trade.action}
//                         </span>
//                         <span className="text-lg font-bold text-white">{trade.ticker}</span>
//                         <span className="text-[10px] text-slate-400 uppercase font-bold border border-slate-700 px-2 py-0.5 rounded bg-slate-950">
//                           {trade.status.replace('CLOSED_', '')}
//                         </span>
//                       </div>
                      
//                       {/* Hold Time */}
//                       <div className="text-[11px] text-slate-500 flex items-center gap-1.5 md:ml-2">
//                         <Clock className="w-3 h-3" />
//                         Hold: <span className="text-slate-400 font-mono">{formatHoldTime(trade.activated_at || trade.created_at, trade.closed_at)}</span>
//                       </div>
//                     </div>

//                     {/* Right Side of Card (Financials & Exit Time) */}
//                     <div className="flex items-center gap-6 w-full xl:w-auto justify-between xl:justify-end">
                      
//                       <div className="flex items-center gap-6">
//                         <div className="flex flex-col text-right hidden sm:flex">
//                           <span className="text-slate-500 text-[10px] uppercase">Entry Px</span>
//                           <span className="font-mono text-slate-300 text-sm">₹{trade.entry_price}</span>
//                         </div>
//                         <div className="flex flex-col text-right hidden sm:flex">
//                           <span className="text-slate-500 text-[10px] uppercase">Exit Px</span>
//                           <span className="font-mono text-slate-300 text-sm">₹{trade.live_price || trade.entry_price}</span>
//                         </div>
//                         <div className="flex flex-col text-right min-w-[80px]">
//                           <span className="text-slate-500 text-[10px] uppercase">Final PnL</span>
//                           <span className={`font-black text-lg ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}>
//                             {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
//                           </span>
//                         </div>
//                       </div>

//                       {/* Extreme Right: Sold Time */}
//                       <div className="flex flex-col text-right border-l border-slate-800 pl-4 ml-2 min-w-[65px]">
//                         <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mb-0.5">Exit</div>
//                         <div className="text-xs font-bold text-slate-300">
//                           {formatTime(trade.closed_at)}
//                         </div>
//                       </div>

//                     </div>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//       </div>
//     </div>
//   );
// }

// import React, { useState, useEffect } from 'react';
// import { Activity, Check, X, ShieldAlert, Zap, Wallet, TrendingUp, ArrowUpRight, Brain, Copy, CheckCheck, Clock, History, Octagon, Settings } from 'lucide-react';

// // --- DIAGNOSTIC LiveTimer Component ---
// const LiveTimer = ({ startTime }) => {
//   const [elapsed, setElapsed] = useState('Loading...');

//   useEffect(() => {
//     if (!startTime) {
//        setElapsed('API Data Missing');
//        return;
//     }

//     const updateTimer = () => {
//       const now = Date.now();
//       const safeString = String(startTime).split('.')[0].replace(' ', 'T');
//       let startMs = new Date(safeString + 'Z').getTime();

//       if (startMs > now) {
//         startMs = new Date(safeString).getTime(); 
//       }

//       let diffInSeconds = Math.floor((now - startMs) / 1000);

//       if (isNaN(diffInSeconds)) {
//         setElapsed('Format Error');
//         return;
//       }

//       if (diffInSeconds < 0) {
//         setElapsed('Time Desync');
//         return;
//       }

//       const h = Math.floor(diffInSeconds / 3600);
//       const m = Math.floor((diffInSeconds % 3600) / 60);
//       const s = diffInSeconds % 60;
      
//       if (h > 0) {
//         setElapsed(`${h}h ${m}m ${s}s`);
//       } else {
//         setElapsed(`${m}m ${s}s`);
//       }
//     };

//     updateTimer();
//     const intervalId = setInterval(updateTimer, 1000);
//     return () => clearInterval(intervalId);
//   }, [startTime]);

//   return <span className="font-mono tracking-wider text-amber-400 font-bold">{elapsed}</span>;
// };

// // --- Helper for Closed Trades Hold Time (Fixed NaN issue) ---
// const formatHoldTime = (start, end) => {
//   if (!start || !end) return "--";
//   const safeStart = String(start).endsWith('Z') ? start : start + 'Z';
//   const safeEnd = String(end).endsWith('Z') ? end : end + 'Z';
  
//   const startMs = new Date(safeStart).getTime();
//   const endMs = new Date(safeEnd).getTime();
  
//   if (isNaN(startMs) || isNaN(endMs)) return "--";

//   const diffSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000));
  
//   const h = Math.floor(diffSeconds / 3600);
//   const m = Math.floor((diffSeconds % 3600) / 60);
  
//   if (h > 0) return `${h}h ${m}m`;
//   return `${m}m`;
// };

// // --- Helper for HH:MM AM/PM Display ---
// const formatTime = (isoString) => {
//   if (!isoString) return "--:--";
//   const safeString = String(isoString).endsWith('Z') ? isoString : isoString + 'Z';
//   const d = new Date(safeString);
//   if (isNaN(d.getTime())) return "--:--";
//   return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
// };

// // --- Helper to Generate 15-Minute Timeline Slots (9:15 AM to 3:30 PM) ---
// const generateMarketSlots = () => {
//   const slots = [];
//   for (let h = 9; h <= 15; h++) {
//     for (let m = 0; m < 60; m += 15) {
//       if (h === 9 && m < 15) continue; // Start at 9:15
//       if (h === 15 && m > 30) continue; // End at 15:30
      
//       const hour = h.toString().padStart(2, '0');
//       const min = m.toString().padStart(2, '0');
      
//       const isPM = h >= 12;
//       const displayH = h > 12 ? (h === 12 ? 12 : h - 12) : h;
//       const displayTime = `${displayH.toString().padStart(2, '0')}:${min} ${isPM ? 'PM' : 'AM'}`;
      
//       slots.push({ key: `${hour}:${min}`, displayTime, trades: [] });
//     }
//   }
//   return slots;
// };

// export default function App() {
//   const [pendingTrades, setPendingTrades] = useState([]);
//   const [activeTrades, setActiveTrades] = useState([]);
//   const [closedTrades, setClosedTrades] = useState([]);
  
//   const [autoDeploy, setAutoDeploy] = useState(false);

//   // --- THE FIX 1: Simplify initial state ---
//   const [startingCapital, setStartingCapital] = useState(10000);
//   const [loading, setLoading] = useState(true);
//   const [copiedField, setCopiedField] = useState(null);

//   // --- THE FIX 2: Update database when you type a new capital amount ---
//   const handleCapitalChange = async (e) => {
//     const val = parseFloat(e.target.value) || 0;
//     setStartingCapital(val); 
    
//     try {
//       await fetch('/api/account/capital', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ current_capital: val })
//       });
//     } catch (error) {
//       console.error("Failed to update capital in database", error);
//     }
//   };

//   const handleCopy = (text, fieldId) => {
//     navigator.clipboard.writeText(text);
//     setCopiedField(fieldId);
//     setTimeout(() => setCopiedField(null), 2000);
//   };

//   const fetchDashboardData = async () => {
//     try {
//       const pendingRes = await fetch('/api/trades/pending');
//       if (pendingRes.ok) setPendingTrades(await pendingRes.json());

//       const activeRes = await fetch('/api/trades/active');
//       if (activeRes.ok) setActiveTrades(await activeRes.json());

//       const closedRes = await fetch('/api/trades/closed');
//       if (closedRes.ok) setClosedTrades(await closedRes.json());

//       const autoDeployRes = await fetch('/api/account/auto_deploy');
//       if (autoDeployRes.ok) {
//         const adData = await autoDeployRes.json();
//         setAutoDeploy(adData.auto_deploy);
//       }

//       // --- THE FIX 3: Fetch live capital from DB continuously ---
//       const capitalRes = await fetch('/api/account/capital');
//       if (capitalRes.ok) {
//         const capData = await capitalRes.json();
//         // Only override the UI state if the user is not actively typing in the box
//         if (document.activeElement.type !== "number") {
//             setStartingCapital(capData.current_capital);
//         }
//       }

//     } catch (error) {
//       console.error("Dashboard connection sync failed:", error);
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchDashboardData();
//     const interval = setInterval(fetchDashboardData, 3000); 
//     return () => clearInterval(interval);
//   }, []);

//   const handleAction = async (id, actionType) => {
//     try {
//       await fetch(`/api/trades/${id}/${actionType}`, { method: 'POST' });
//       fetchDashboardData();
//     } catch (error) {
//       console.error(`Failed to execute ${actionType} on trade #${id}`, error);
//     }
//   };

//   const toggleAutoDeploy = async () => {
//     const newState = !autoDeploy;
//     setAutoDeploy(newState);
//     try {
//       await fetch('/api/account/auto_deploy', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ auto_deploy: newState })
//       });
//     } catch (error) {
//       console.error("Failed to update auto_deploy", error);
//       setAutoDeploy(!newState);
//     }
//   };

//   // --- SORT BY ENTRY TIME (Newest at the top) ---
//   const sortedClosedTrades = [...closedTrades].sort((a, b) => {
//     const timeA = new Date((a.activated_at || a.created_at) + 'Z').getTime();
//     const timeB = new Date((b.activated_at || b.created_at) + 'Z').getTime();
//     return timeB - timeA;
//   });

//   const totalActivePnL = activeTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
//   const totalClosedPnL = closedTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
  
//   const realizedCapital = startingCapital + totalClosedPnL; 
//   const liveValuation = realizedCapital + totalActivePnL; 

//   // --- GROUP ACTIVE TRADES INTO 15-MIN TIMELINE ---
//   const activeTimeline = generateMarketSlots();
  
//   activeTrades.forEach(trade => {
//     const timeStr = trade.activated_at || trade.created_at;
//     if (!timeStr) return;
    
//     // Ensure accurate Date parsing
//     const safeString = String(timeStr).endsWith('Z') ? timeStr : timeStr + 'Z';
//     const d = new Date(safeString);
//     if (isNaN(d.getTime())) return;
    
//     const h = d.getHours();
//     const m = d.getMinutes();
    
//     // Round down to the nearest 15-minute bucket
//     const bucketM = Math.floor(m / 15) * 15;
//     const slotKey = `${h.toString().padStart(2, '0')}:${bucketM.toString().padStart(2, '0')}`;
    
//     const slot = activeTimeline.find(s => s.key === slotKey);
//     if (slot) {
//       slot.trades.push(trade);
//     }
//   });

//   return (
//     <div className="min-h-screen p-8 font-sans bg-slate-950 text-slate-100 pb-20 overflow-x-hidden">
      
//       {/* Top Navigation Bar */}
//       <header className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between border-b border-slate-800 pb-6 mb-8">
//         <div className="flex items-center gap-3">
//           <Zap className="text-amber-400 w-8 h-8 fill-amber-400/20" />
//           <h1 className="text-3xl font-black tracking-wider bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
//             VIBE TRADING
//           </h1>
//         </div>
        
//         <div className="flex items-center gap-4">
//           <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 px-4 py-2 rounded-full shadow-inner">
//             <Settings className={`w-4 h-4 ${autoDeploy ? 'text-amber-400 animate-spin-slow' : 'text-slate-500'}`} style={{ animationDuration: '4s' }} />
//             <span className={`text-xs font-bold tracking-wider ${autoDeploy ? 'text-slate-200' : 'text-slate-500'}`}>
//               AUTO DEPLOY
//             </span>
//             <button 
//               onClick={toggleAutoDeploy}
//               className={`ml-2 w-10 h-5 rounded-full relative transition-colors ${autoDeploy ? 'bg-amber-500' : 'bg-slate-700'}`}
//             >
//               <div className={`w-3.5 h-3.5 bg-white rounded-full absolute top-[3px] transition-all ${autoDeploy ? 'left-[22px]' : 'left-[3px]'}`} />
//             </button>
//           </div>

//           <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full text-sm font-semibold border border-emerald-500/20 shadow-inner hidden md:flex">
//             <Activity className="w-4 h-4 animate-pulse" />
//             Quant Core Active
//           </div>
//         </div>
//       </header>

//       {/* Financial Health Matrix */}
//       <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Starting Account Balance</p>
//             <div className="flex items-center gap-2">
//               <span className="text-slate-500 text-xl font-bold">₹</span>
//               <input 
//                 type="number" 
//                 value={startingCapital} 
//                 onChange={handleCapitalChange}
//                 className="bg-slate-950 border border-slate-700 rounded px-3 py-1 text-2xl font-bold text-white focus:outline-none focus:border-amber-500 w-44 transition-colors"
//               />
//             </div>
//           </div>
//           <Wallet className="w-10 h-10 text-slate-600" />
//         </div>

//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Live Valuation (Inc. Open PnL)</p>
//             <p className={`text-3xl font-black ${liveValuation >= startingCapital ? 'text-emerald-400' : 'text-rose-400'}`}>
//               ₹{liveValuation.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
//             </p>
//           </div>
//           <TrendingUp className={`w-10 h-10 ${liveValuation >= startingCapital ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
//         </div>

//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Today's Realized PnL</p>
//             <p className={`text-3xl font-black ${totalClosedPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
//               {totalClosedPnL >= 0 ? '+' : ''}₹{totalClosedPnL.toFixed(2)}
//             </p>
//           </div>
//           <ArrowUpRight className={`w-10 h-10 ${totalClosedPnL >= 0 ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
//         </div>
//       </div>

//       {/* Workspace Grid */}
//       <div className="grid grid-cols-1 gap-10 max-w-6xl mx-auto">
        
//         {/* SECTION 1: CO PILOT PROPOSALS */}
//         <div>
//           <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
//             <ShieldAlert className="text-amber-500 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Pending Signals</h2>
//           </div>

//           {loading ? (
//             <p className="text-slate-500 animate-pulse text-sm">Decoding transmission...</p>
//           ) : pendingTrades.length === 0 ? (
//             <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
//               {autoDeploy ? "Auto-Deploy is ON. Signals will bypass this queue and activate instantly." : "No active pending signals. Waiting for market setup conditions..."}
//             </div>
//           ) : (
//             <div className="grid gap-4">
//               {pendingTrades.map(trade => (
//                 <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col xl:flex-row items-center justify-between hover:border-slate-700 transition-colors shadow-lg">
//                   <div className="flex-1 w-full">
                    
//                     <div className="flex flex-wrap items-center gap-3 mb-2">
//                       <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
//                         {trade.action}
//                       </span>
//                       <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
//                       <span className="text-[11px] text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800/60">
//                         ⏱️ Signal Received: {formatTime(trade.created_at)}
//                       </span>
//                     </div>
                    
//                     <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 bg-slate-950 p-3 rounded-lg border border-slate-800/50">
                      
//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Entry Target</p>
//                           <p className="font-semibold text-slate-300 font-mono">₹{trade.entry_price}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.entry_price, `${trade.id}-entry`)} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors" title="Copy Entry">
//                           {copiedField === `${trade.id}-entry` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Take Profit</p>
//                           <p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.take_profit, `${trade.id}-tp`)} className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 rounded transition-colors" title="Copy Take Profit">
//                           {copiedField === `${trade.id}-tp` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Stop Loss</p>
//                           <p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.stop_loss, `${trade.id}-sl`)} className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-700 rounded transition-colors" title="Copy Stop Loss">
//                           {copiedField === `${trade.id}-sl` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex flex-col justify-center p-2 rounded bg-slate-900 border border-slate-800">
//                         <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Size</p>
//                         <p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p>
//                       </div>
//                     </div>
//                   </div>
                  
//                   <div className="flex gap-3 xl:ml-6 mt-4 xl:mt-0 w-full xl:w-auto">
//                     <button onClick={() => handleAction(trade.id, 'approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-3 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/20">
//                       <Check className="w-5 h-5" /> Deploy
//                     </button>
//                     <button 
//                       onClick={() => handleAction(trade.id, 'reject')} 
//                       title="Mark as Not Executed"
//                       className="bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white px-4 py-3 rounded-lg font-bold transition-all border border-transparent"
//                     >
//                       <X className="w-5 h-5" />
//                     </button>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//         {/* SECTION 2: ACTIVE PORTFOLIO VIA RISK MANAGER */}
//         <div>
//           <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
//             <Brain className="text-blue-400 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Active Risk Engine Watch</h2>
//           </div>

//           <div className="relative ml-20 md:ml-24 border-l-2 border-slate-800/60 pb-4 mt-6">
//             {activeTimeline.map((slot) => (
//               <div key={slot.key} className="relative mb-8 last:mb-0 pl-6 md:pl-8 min-h-[60px]">
                
//                 {/* Timeline Dot */}
//                 <div className="absolute -left-[9px] top-4 w-4 h-4 rounded-full bg-slate-950 border-2 border-slate-700 flex items-center justify-center z-10">
//                   <div className={`w-1.5 h-1.5 rounded-full ${slot.trades.length > 0 ? 'bg-blue-500 animate-pulse' : 'bg-slate-700'}`} />
//                 </div>

//                 {/* Time Label (Left) */}
//                 <div className="absolute -left-[85px] md:-left-[95px] top-3.5 w-16 md:w-20 text-right">
//                   <div className={`text-xs font-bold ${slot.trades.length > 0 ? 'text-slate-300' : 'text-slate-600'}`}>
//                     {slot.displayTime}
//                   </div>
//                   <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mt-0.5">Bucket</div>
//                 </div>

//                 {/* Slot Content */}
//                 {slot.trades.length === 0 ? (
//                   <div className="h-full border border-dashed border-slate-800/40 rounded-xl bg-slate-900/20 flex items-center px-5 py-4">
//                     <span className="text-slate-600 text-xs font-mono">No active allocations generated in this interval</span>
//                   </div>
//                 ) : (
//                   <div className="grid gap-4">
//                     {slot.trades.map(trade => (
//                       <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors shadow-lg relative overflow-hidden">
                        
//                         {/* FORCE STOP BUTTON */}
//                         <div className="absolute top-4 right-4">
//                             <button 
//                               onClick={() => handleAction(trade.id, 'emergency_stop')}
//                               className="bg-rose-500/10 hover:bg-rose-600 text-rose-400 hover:text-white px-3 py-1.5 rounded text-xs font-bold transition-all flex items-center gap-1.5 border border-rose-500/20 hover:border-transparent shadow-lg"
//                             >
//                               <Octagon className="w-3.5 h-3.5" /> Force Kill
//                             </button>
//                         </div>

//                         <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-800 pb-3 pr-24">
//                           <div className="flex flex-wrap items-center gap-3">
//                             <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
//                               {trade.action}
//                             </span>
//                             <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                            
//                             <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded font-semibold animate-pulse border border-blue-500/20 uppercase tracking-wider">
//                               🛡️ AI Protected
//                             </span>
                            
//                             <span className="text-[11px] flex items-center gap-1 text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700">
//                               <Clock className="w-3 h-3 text-slate-400" />
//                               Held: <LiveTimer startTime={trade.activated_at || trade.created_at} />
//                             </span>
//                           </div>

//                           <p className={`text-lg font-black mt-2 md:mt-0 ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
//                             {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
//                           </p>
//                         </div>

//                         <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm mb-4">
//                           <div><p className="text-slate-500 text-xs">Size</p><p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p></div>
//                           <div><p className="text-slate-500 text-xs">Bought At</p><p className="font-semibold font-mono">₹{trade.entry_price}</p></div>
//                           <div><p className="text-slate-500 text-xs">Live Price</p><p className="font-semibold text-blue-400 font-mono">₹{trade.live_price || trade.entry_price}</p></div>
//                           <div><p className="text-slate-500 text-xs">Target</p><p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p></div>
//                           <div><p className="text-slate-500 text-xs">Active Stop</p><p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p></div>
//                           <div><p className="text-slate-500 text-xs">RSI / MACD</p><p className="font-mono text-[10px] text-amber-400 mt-0.5">{trade.live_rsi || '--'} | {trade.live_macd || '--'}</p></div>
//                         </div>

//                         <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs flex items-start gap-2 text-slate-400">
//                           <span className="font-bold text-blue-400 uppercase tracking-wider text-[10px] bg-blue-500/10 px-1.5 py-0.5 rounded mt-0.5 shrink-0">AI Reasoning</span>
//                           <p className="leading-relaxed">
//                             {trade.risk_reasoning || "Risk manager analyzing current market structural alignment. Maintaining stop parameters unchanged."}
//                           </p>
//                         </div>
//                       </div>
//                     ))}
//                   </div>
//                 )}
//               </div>
//             ))}
//           </div>
//         </div>

//         {/* --- SECTION 3: NEW TIMELINE TRADING LOG --- */}
//         <div>
//           <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-2 mt-4">
//             <History className="text-purple-400 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Today's Closed Trades</h2>
//           </div>

//           {sortedClosedTrades.length === 0 ? (
//             <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
//               No trades finalized today. Let the AI work!
//             </div>
//           ) : (
//             <div className="relative ml-20 md:ml-24 border-l-2 border-slate-800/60 pb-4">
//               {sortedClosedTrades.map((trade, index) => (
//                 <div key={trade.id} className="relative mb-6 last:mb-0 pl-6 md:pl-8">
                  
//                   {/* Timeline Dot */}
//                   <div className="absolute -left-[9px] top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-slate-950 border-2 border-slate-700 flex items-center justify-center z-10">
//                     <div className={`w-1.5 h-1.5 rounded-full ${(trade.current_pnl || 0) >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`} />
//                   </div>

//                   {/* Bought Time (Extreme Left) */}
//                   <div className="absolute -left-[85px] md:-left-[95px] top-1/2 -translate-y-1/2 w-16 md:w-20 text-right">
//                     <div className="text-xs font-bold text-slate-300">
//                       {formatTime(trade.activated_at || trade.created_at)}
//                     </div>
//                     <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mt-0.5">Entry</div>
//                   </div>

//                   {/* Trade Card */}
//                   <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 flex flex-col xl:flex-row items-center justify-between opacity-80 hover:opacity-100 transition-opacity shadow-sm hover:shadow-md">
                    
//                     {/* Left Side of Card */}
//                     <div className="flex flex-col md:flex-row items-start md:items-center gap-3 w-full xl:w-auto mb-4 xl:mb-0">
//                       <div className="flex items-center gap-3">
//                         <span className={`px-2 py-1 rounded text-[10px] font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/10 text-rose-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
//                           {trade.action}
//                         </span>
//                         <span className="text-lg font-bold text-white">{trade.ticker}</span>
//                         <span className="text-[10px] text-slate-400 uppercase font-bold border border-slate-700 px-2 py-0.5 rounded bg-slate-950">
//                           {trade.status.replace('CLOSED_', '')}
//                         </span>
//                       </div>
                      
//                       {/* Hold Time */}
//                       <div className="text-[11px] text-slate-500 flex items-center gap-1.5 md:ml-2">
//                         <Clock className="w-3 h-3" />
//                         Hold: <span className="text-slate-400 font-mono">{formatHoldTime(trade.activated_at || trade.created_at, trade.closed_at)}</span>
//                       </div>
//                     </div>

//                     {/* Right Side of Card (Financials & Exit Time) */}
//                     <div className="flex items-center gap-6 w-full xl:w-auto justify-between xl:justify-end">
                      
//                       <div className="flex items-center gap-6">
//                         <div className="flex flex-col text-right hidden sm:flex">
//                           <span className="text-slate-500 text-[10px] uppercase">Entry Px</span>
//                           <span className="font-mono text-slate-300 text-sm">₹{trade.entry_price}</span>
//                         </div>
//                         <div className="flex flex-col text-right hidden sm:flex">
//                           <span className="text-slate-500 text-[10px] uppercase">Exit Px</span>
//                           <span className="font-mono text-slate-300 text-sm">₹{trade.live_price || trade.entry_price}</span>
//                         </div>
//                         <div className="flex flex-col text-right min-w-[80px]">
//                           <span className="text-slate-500 text-[10px] uppercase">Final PnL</span>
//                           <span className={`font-black text-lg ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}>
//                             {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
//                           </span>
//                         </div>
//                       </div>

//                       {/* Extreme Right: Sold Time */}
//                       <div className="flex flex-col text-right border-l border-slate-800 pl-4 ml-2 min-w-[65px]">
//                         <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mb-0.5">Exit</div>
//                         <div className="text-xs font-bold text-slate-300">
//                           {formatTime(trade.closed_at)}
//                         </div>
//                       </div>

//                     </div>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//       </div>
//     </div>
//   );
// }

// import React, { useState, useEffect } from 'react';
// import { Activity, Check, X, ShieldAlert, Zap, Wallet, TrendingUp, ArrowUpRight, Brain, Copy, CheckCheck, Clock, History, Octagon, Settings } from 'lucide-react';

// // --- DIAGNOSTIC LiveTimer Component ---
// const LiveTimer = ({ startTime }) => {
//   const [elapsed, setElapsed] = useState('Loading...');

//   useEffect(() => {
//     if (!startTime) {
//        setElapsed('API Data Missing');
//        return;
//     }

//     const updateTimer = () => {
//       const now = Date.now();
//       const safeString = String(startTime).split('.')[0].replace(' ', 'T');
//       let startMs = new Date(safeString + 'Z').getTime();

//       if (startMs > now) {
//         startMs = new Date(safeString).getTime(); 
//       }

//       let diffInSeconds = Math.floor((now - startMs) / 1000);

//       if (isNaN(diffInSeconds)) {
//         setElapsed('Format Error');
//         return;
//       }

//       if (diffInSeconds < 0) {
//         setElapsed('Time Desync');
//         return;
//       }

//       const h = Math.floor(diffInSeconds / 3600);
//       const m = Math.floor((diffInSeconds % 3600) / 60);
//       const s = diffInSeconds % 60;
      
//       if (h > 0) {
//         setElapsed(`${h}h ${m}m ${s}s`);
//       } else {
//         setElapsed(`${m}m ${s}s`);
//       }
//     };

//     updateTimer();
//     const intervalId = setInterval(updateTimer, 1000);
//     return () => clearInterval(intervalId);
//   }, [startTime]);

//   return <span className="font-mono tracking-wider text-amber-400 font-bold">{elapsed}</span>;
// };

// // --- Helper for Closed Trades Hold Time (Fixed NaN issue) ---
// const formatHoldTime = (start, end) => {
//   if (!start || !end) return "--";
//   const safeStart = String(start).endsWith('Z') ? start : start + 'Z';
//   const safeEnd = String(end).endsWith('Z') ? end : end + 'Z';
  
//   const startMs = new Date(safeStart).getTime();
//   const endMs = new Date(safeEnd).getTime();
  
//   if (isNaN(startMs) || isNaN(endMs)) return "--";

//   const diffSeconds = Math.max(0, Math.floor((endMs - startMs) / 1000));
  
//   const h = Math.floor(diffSeconds / 3600);
//   const m = Math.floor((diffSeconds % 3600) / 60);
  
//   if (h > 0) return `${h}h ${m}m`;
//   return `${m}m`;
// };

// // --- Helper for HH:MM AM/PM Display ---
// const formatTime = (isoString) => {
//   if (!isoString) return "--:--";
//   const safeString = String(isoString).endsWith('Z') ? isoString : isoString + 'Z';
//   const d = new Date(safeString);
//   if (isNaN(d.getTime())) return "--:--";
//   return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
// };

// // --- Helper to Generate 15-Minute Timeline Slots (9:15 AM to 3:30 PM) ---
// const generateMarketSlots = () => {
//   const slots = [];
//   for (let h = 9; h <= 15; h++) {
//     for (let m = 0; m < 60; m += 15) {
//       if (h === 9 && m < 15) continue; // Start at 9:15
//       if (h === 15 && m > 30) continue; // End at 15:30
      
//       const hour = h.toString().padStart(2, '0');
//       const min = m.toString().padStart(2, '0');
      
//       const isPM = h >= 12;
//       const displayH = h > 12 ? (h === 12 ? 12 : h - 12) : h;
//       const displayTime = `${displayH.toString().padStart(2, '0')}:${min} ${isPM ? 'PM' : 'AM'}`;
      
//       slots.push({ key: `${hour}:${min}`, displayTime, trades: [] });
//     }
//   }
//   return slots;
// };

// export default function App() {
//   const [pendingTrades, setPendingTrades] = useState([]);
//   const [activeTrades, setActiveTrades] = useState([]);
//   const [closedTrades, setClosedTrades] = useState([]);
  
//   const [autoDeploy, setAutoDeploy] = useState(false);
//   const [startingCapital, setStartingCapital] = useState(10000);
//   const [loading, setLoading] = useState(true);
//   const [copiedField, setCopiedField] = useState(null);

//   // --- NEW: Real-time clock for the Progress Bar logic ---
//   const [now, setNow] = useState(new Date());

//   useEffect(() => {
//     // Tick every second to drive the loading bar smoothly
//     const timer = setInterval(() => setNow(new Date()), 1000);
//     return () => clearInterval(timer);
//   }, []);

//   const handleCapitalChange = async (e) => {
//     const val = parseFloat(e.target.value) || 0;
//     setStartingCapital(val); 
    
//     try {
//       await fetch('/api/account/capital', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ current_capital: val })
//       });
//     } catch (error) {
//       console.error("Failed to update capital in database", error);
//     }
//   };

//   const handleCopy = (text, fieldId) => {
//     navigator.clipboard.writeText(text);
//     setCopiedField(fieldId);
//     setTimeout(() => setCopiedField(null), 2000);
//   };

//   const fetchDashboardData = async () => {
//     try {
//       const pendingRes = await fetch('/api/trades/pending');
//       if (pendingRes.ok) setPendingTrades(await pendingRes.json());

//       const activeRes = await fetch('/api/trades/active');
//       if (activeRes.ok) setActiveTrades(await activeRes.json());

//       const closedRes = await fetch('/api/trades/closed');
//       if (closedRes.ok) setClosedTrades(await closedRes.json());

//       const autoDeployRes = await fetch('/api/account/auto_deploy');
//       if (autoDeployRes.ok) {
//         const adData = await autoDeployRes.json();
//         setAutoDeploy(adData.auto_deploy);
//       }

//       const capitalRes = await fetch('/api/account/capital');
//       if (capitalRes.ok) {
//         const capData = await capitalRes.json();
//         if (document.activeElement.type !== "number") {
//             setStartingCapital(capData.current_capital);
//         }
//       }

//     } catch (error) {
//       console.error("Dashboard connection sync failed:", error);
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     fetchDashboardData();
//     const interval = setInterval(fetchDashboardData, 3000); 
//     return () => clearInterval(interval);
//   }, []);

//   const handleAction = async (id, actionType) => {
//     try {
//       await fetch(`/api/trades/${id}/${actionType}`, { method: 'POST' });
//       fetchDashboardData();
//     } catch (error) {
//       console.error(`Failed to execute ${actionType} on trade #${id}`, error);
//     }
//   };

//   const toggleAutoDeploy = async () => {
//     const newState = !autoDeploy;
//     setAutoDeploy(newState);
//     try {
//       await fetch('/api/account/auto_deploy', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ auto_deploy: newState })
//       });
//     } catch (error) {
//       console.error("Failed to update auto_deploy", error);
//       setAutoDeploy(!newState);
//     }
//   };

//   const sortedClosedTrades = [...closedTrades].sort((a, b) => {
//     const timeA = new Date((a.activated_at || a.created_at) + 'Z').getTime();
//     const timeB = new Date((b.activated_at || b.created_at) + 'Z').getTime();
//     return timeB - timeA;
//   });

//   const totalActivePnL = activeTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
//   const totalClosedPnL = closedTrades.reduce((acc, trade) => acc + (trade.current_pnl || 0), 0);
  
//   const realizedCapital = startingCapital + totalClosedPnL; 
//   const liveValuation = realizedCapital + totalActivePnL; 

//   // --- GROUP ACTIVE TRADES INTO 15-MIN TIMELINE ---
//   const activeTimeline = generateMarketSlots();
  
//   activeTrades.forEach(trade => {
//     const timeStr = trade.activated_at || trade.created_at;
//     if (!timeStr) return;
    
//     const safeString = String(timeStr).endsWith('Z') ? timeStr : timeStr + 'Z';
//     const d = new Date(safeString);
//     if (isNaN(d.getTime())) return;
    
//     const h = d.getHours();
//     const m = d.getMinutes();
    
//     const bucketM = Math.floor(m / 15) * 15;
//     const slotKey = `${h.toString().padStart(2, '0')}:${bucketM.toString().padStart(2, '0')}`;
    
//     const slot = activeTimeline.find(s => s.key === slotKey);
//     if (slot) {
//       slot.trades.push(trade);
//     }
//   });

//   return (
//     <div className="min-h-screen p-8 font-sans bg-slate-950 text-slate-100 pb-20 overflow-x-hidden">
      
//       {/* Top Navigation Bar */}
//       <header className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between border-b border-slate-800 pb-6 mb-8">
//         <div className="flex items-center gap-3">
//           <Zap className="text-amber-400 w-8 h-8 fill-amber-400/20" />
//           <h1 className="text-3xl font-black tracking-wider bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
//             VIBE TRADING
//           </h1>
//         </div>
        
//         <div className="flex items-center gap-4">
//           <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 px-4 py-2 rounded-full shadow-inner">
//             <Settings className={`w-4 h-4 ${autoDeploy ? 'text-amber-400 animate-spin-slow' : 'text-slate-500'}`} style={{ animationDuration: '4s' }} />
//             <span className={`text-xs font-bold tracking-wider ${autoDeploy ? 'text-slate-200' : 'text-slate-500'}`}>
//               AUTO DEPLOY
//             </span>
//             <button 
//               onClick={toggleAutoDeploy}
//               className={`ml-2 w-10 h-5 rounded-full relative transition-colors ${autoDeploy ? 'bg-amber-500' : 'bg-slate-700'}`}
//             >
//               <div className={`w-3.5 h-3.5 bg-white rounded-full absolute top-[3px] transition-all ${autoDeploy ? 'left-[22px]' : 'left-[3px]'}`} />
//             </button>
//           </div>

//           <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full text-sm font-semibold border border-emerald-500/20 shadow-inner hidden md:flex">
//             <Activity className="w-4 h-4 animate-pulse" />
//             Quant Core Active
//           </div>
//         </div>
//       </header>

//       {/* Financial Health Matrix */}
//       <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Starting Account Balance</p>
//             <div className="flex items-center gap-2">
//               <span className="text-slate-500 text-xl font-bold">₹</span>
//               <input 
//                 type="number" 
//                 value={startingCapital} 
//                 onChange={handleCapitalChange}
//                 className="bg-slate-950 border border-slate-700 rounded px-3 py-1 text-2xl font-bold text-white focus:outline-none focus:border-amber-500 w-44 transition-colors"
//               />
//             </div>
//           </div>
//           <Wallet className="w-10 h-10 text-slate-600" />
//         </div>

//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Live Valuation (Inc. Open PnL)</p>
//             <p className={`text-3xl font-black ${liveValuation >= startingCapital ? 'text-emerald-400' : 'text-rose-400'}`}>
//               ₹{liveValuation.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
//             </p>
//           </div>
//           <TrendingUp className={`w-10 h-10 ${liveValuation >= startingCapital ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
//         </div>

//         <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex items-center justify-between">
//           <div>
//             <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">Today's Realized PnL</p>
//             <p className={`text-3xl font-black ${totalClosedPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
//               {totalClosedPnL >= 0 ? '+' : ''}₹{totalClosedPnL.toFixed(2)}
//             </p>
//           </div>
//           <ArrowUpRight className={`w-10 h-10 ${totalClosedPnL >= 0 ? 'text-emerald-500/40' : 'text-rose-500/40'}`} />
//         </div>
//       </div>

//       {/* Workspace Grid */}
//       <div className="grid grid-cols-1 gap-10 max-w-6xl mx-auto">
        
//         {/* SECTION 1: PENDING SIGNALS */}
//         <div>
//           <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
//             <ShieldAlert className="text-amber-500 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Pending Signals</h2>
//           </div>

//           {loading ? (
//             <p className="text-slate-500 animate-pulse text-sm">Decoding transmission...</p>
//           ) : pendingTrades.length === 0 ? (
//             <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
//               {autoDeploy ? "Auto-Deploy is ON. Signals will bypass this queue and activate instantly." : "No active pending signals. Waiting for market setup conditions..."}
//             </div>
//           ) : (
//             <div className="grid gap-4">
//               {pendingTrades.map(trade => (
//                 <div key={trade.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col xl:flex-row items-center justify-between hover:border-slate-700 transition-colors shadow-lg">
//                   <div className="flex-1 w-full">
                    
//                     <div className="flex flex-wrap items-center gap-3 mb-2">
//                       <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
//                         {trade.action}
//                       </span>
//                       <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
//                       <span className="text-[11px] text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800/60">
//                         ⏱️ Signal Received: {formatTime(trade.created_at)}
//                       </span>
//                     </div>
                    
//                     <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 bg-slate-950 p-3 rounded-lg border border-slate-800/50">
//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Entry Target</p>
//                           <p className="font-semibold text-slate-300 font-mono">₹{trade.entry_price}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.entry_price, `${trade.id}-entry`)} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors" title="Copy Entry">
//                           {copiedField === `${trade.id}-entry` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Take Profit</p>
//                           <p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.take_profit, `${trade.id}-tp`)} className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-700 rounded transition-colors" title="Copy Take Profit">
//                           {copiedField === `${trade.id}-tp` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 group">
//                         <div>
//                           <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Stop Loss</p>
//                           <p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p>
//                         </div>
//                         <button onClick={() => handleCopy(trade.stop_loss, `${trade.id}-sl`)} className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-700 rounded transition-colors" title="Copy Stop Loss">
//                           {copiedField === `${trade.id}-sl` ? <CheckCheck className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4 opacity-50 group-hover:opacity-100" />}
//                         </button>
//                       </div>

//                       <div className="flex flex-col justify-center p-2 rounded bg-slate-900 border border-slate-800">
//                         <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Size</p>
//                         <p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p>
//                       </div>
//                     </div>
//                   </div>
                  
//                   <div className="flex gap-3 xl:ml-6 mt-4 xl:mt-0 w-full xl:w-auto">
//                     <button onClick={() => handleAction(trade.id, 'approve')} className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-3 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-900/20">
//                       <Check className="w-5 h-5" /> Deploy
//                     </button>
//                     <button 
//                       onClick={() => handleAction(trade.id, 'reject')} 
//                       title="Mark as Not Executed"
//                       className="bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white px-4 py-3 rounded-lg font-bold transition-all border border-transparent"
//                     >
//                       <X className="w-5 h-5" />
//                     </button>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//         {/* SECTION 2: LIVE PROGRESS TIMELINE */}
//         <div>
//           <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-2">
//             <Brain className="text-blue-400 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Active Risk Engine Watch</h2>
//           </div>

//           <div className="relative ml-20 md:ml-24 pb-4 mt-6">
//             {activeTimeline.map((slot, index) => {
//               // --- CALCULATE REAL-TIME PROGRESS ---
//               const [hourStr, minStr] = slot.key.split(':');
//               const slotStart = new Date(now);
//               slotStart.setHours(parseInt(hourStr), parseInt(minStr), 0, 0);

//               const slotEnd = new Date(slotStart);
//               slotEnd.setMinutes(slotStart.getMinutes() + 15);

//               const nowMs = now.getTime();
//               const startMs = slotStart.getTime();
//               const endMs = slotEnd.getTime();

//               let status = 'future';
//               let progress = 0;

//               if (nowMs >= endMs) {
//                 status = 'past';
//                 progress = 100;
//               } else if (nowMs >= startMs && nowMs < endMs) {
//                 status = 'present';
//                 // Calculate percentage elapsed within the 15m window
//                 progress = ((nowMs - startMs) / (endMs - startMs)) * 100;
//               }

//               // Styling logic based on time status
//               const isPast = status === 'past';
//               const isPresent = status === 'present';

//               return (
//                 <div key={slot.key} className="relative mb-8 last:mb-0 pl-6 md:pl-8 min-h-[60px]">
                  
//                   {/* Background Track Line (Gray) - Only draw if not the last item */}
//                   {index < activeTimeline.length - 1 && (
//                     <div 
//                       className="absolute w-[2px] bg-slate-800/60 z-0" 
//                       style={{ left: '-2px', top: '24px', height: 'calc(100% + 32px)' }} 
//                     />
//                   )}

//                   {/* Foreground Animated Loading Bar (Blue) */}
//                   {index < activeTimeline.length - 1 && progress > 0 && (
//                     <div
//                       className="absolute w-[2px] bg-blue-500 z-10 transition-all duration-1000 ease-linear shadow-[0_0_8px_rgba(59,130,246,0.6)]"
//                       style={{ left: '-2px', top: '24px', height: `calc((100% + 32px) * ${progress / 100})` }}
//                     />
//                   )}

//                   {/* Timeline Dot (Changes color based on time state) */}
//                   <div className={`absolute -left-[9px] top-4 w-4 h-4 rounded-full bg-slate-950 border-2 flex items-center justify-center z-20 transition-colors duration-500 ${isPast ? 'border-blue-600' : isPresent ? 'border-blue-400 shadow-[0_0_12px_rgba(96,165,250,0.4)]' : 'border-slate-800'}`}>
//                     <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${isPast ? 'bg-blue-600' : isPresent ? 'bg-blue-400 animate-pulse' : 'bg-slate-800'}`} />
//                   </div>

//                   {/* Time Label (Left) */}
//                   <div className="absolute -left-[85px] md:-left-[95px] top-3.5 w-16 md:w-20 text-right">
//                     <div className={`text-xs transition-colors duration-500 ${isPresent ? 'text-blue-400 font-black tracking-wide' : isPast ? 'text-slate-400 font-bold' : 'text-slate-600 font-medium'}`}>
//                       {slot.displayTime}
//                     </div>
//                     <div className={`text-[9px] uppercase tracking-wider font-semibold mt-0.5 ${isPresent ? 'text-blue-500/70' : 'text-slate-600'}`}>
//                       Bucket
//                     </div>
//                   </div>

//                   {/* Slot Content */}
//                   {slot.trades.length === 0 ? (
//                     <div className={`h-full border border-dashed rounded-xl flex items-center px-5 py-4 transition-colors duration-500 ${isPresent ? 'bg-blue-900/10 border-blue-500/30' : 'bg-slate-900/20 border-slate-800/40'}`}>
//                       <span className={`text-xs font-mono ${isPresent ? 'text-blue-400/80' : 'text-slate-600'}`}>
//                         {isPresent ? "Scanning for active allocations..." : "No active allocations generated in this interval"}
//                       </span>
//                     </div>
//                   ) : (
//                     <div className="grid gap-4 z-30 relative">
//                       {slot.trades.map(trade => (
//                         <div key={trade.id} className={`bg-slate-900 border rounded-xl p-5 hover:border-slate-600 transition-colors shadow-lg relative overflow-hidden ${isPresent ? 'border-blue-500/30' : 'border-slate-800'}`}>
                          
//                           {/* FORCE STOP BUTTON */}
//                           <div className="absolute top-4 right-4">
//                               <button 
//                                 onClick={() => handleAction(trade.id, 'emergency_stop')}
//                                 className="bg-rose-500/10 hover:bg-rose-600 text-rose-400 hover:text-white px-3 py-1.5 rounded text-xs font-bold transition-all flex items-center gap-1.5 border border-rose-500/20 hover:border-transparent shadow-lg"
//                               >
//                                 <Octagon className="w-3.5 h-3.5" /> Force Kill
//                               </button>
//                           </div>

//                           <div className="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-800 pb-3 pr-24">
//                             <div className="flex flex-wrap items-center gap-3">
//                               <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
//                                 {trade.action}
//                               </span>
//                               <span className="text-xl font-extrabold text-white tracking-wide">{trade.ticker}</span>
                              
//                               <span className="text-[10px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded font-semibold animate-pulse border border-blue-500/20 uppercase tracking-wider">
//                                 🛡️ AI Protected
//                               </span>
                              
//                               <span className="text-[11px] flex items-center gap-1 text-slate-300 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700">
//                                 <Clock className="w-3 h-3 text-slate-400" />
//                                 Held: <LiveTimer startTime={trade.activated_at || trade.created_at} />
//                               </span>
//                             </div>

//                             <p className={`text-lg font-black mt-2 md:mt-0 ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
//                               {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
//                             </p>
//                           </div>

//                           <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm mb-4">
//                             <div><p className="text-slate-500 text-xs">Size</p><p className="font-semibold text-slate-300 font-mono">{trade.sizing} Units</p></div>
//                             <div><p className="text-slate-500 text-xs">Bought At</p><p className="font-semibold font-mono">₹{trade.entry_price}</p></div>
//                             <div><p className="text-slate-500 text-xs">Live Price</p><p className="font-semibold text-blue-400 font-mono">₹{trade.live_price || trade.entry_price}</p></div>
//                             <div><p className="text-slate-500 text-xs">Target</p><p className="font-semibold text-emerald-400 font-mono">₹{trade.take_profit}</p></div>
//                             <div><p className="text-slate-500 text-xs">Active Stop</p><p className="font-semibold text-rose-400 font-mono">₹{trade.stop_loss}</p></div>
//                             <div><p className="text-slate-500 text-xs">RSI / MACD</p><p className="font-mono text-[10px] text-amber-400 mt-0.5">{trade.live_rsi || '--'} | {trade.live_macd || '--'}</p></div>
//                           </div>

//                           <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs flex items-start gap-2 text-slate-400">
//                             <span className="font-bold text-blue-400 uppercase tracking-wider text-[10px] bg-blue-500/10 px-1.5 py-0.5 rounded mt-0.5 shrink-0">AI Reasoning</span>
//                             <p className="leading-relaxed">
//                               {trade.risk_reasoning || "Risk manager analyzing current market structural alignment. Maintaining stop parameters unchanged."}
//                             </p>
//                           </div>
//                         </div>
//                       ))}
//                     </div>
//                   )}
//                 </div>
//               );
//             })}
//           </div>
//         </div>

//         {/* --- SECTION 3: CLOSED TRADES LOG --- */}
//         <div>
//           <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-2 mt-4">
//             <History className="text-purple-400 w-5 h-5" />
//             <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Today's Closed Trades</h2>
//           </div>

//           {sortedClosedTrades.length === 0 ? (
//             <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
//               No trades finalized today. Let the AI work!
//             </div>
//           ) : (
//             <div className="relative ml-20 md:ml-24 border-l-2 border-slate-800/60 pb-4">
//               {sortedClosedTrades.map((trade, index) => (
//                 <div key={trade.id} className="relative mb-6 last:mb-0 pl-6 md:pl-8">
                  
//                   <div className="absolute -left-[9px] top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-slate-950 border-2 border-slate-700 flex items-center justify-center z-10">
//                     <div className={`w-1.5 h-1.5 rounded-full ${(trade.current_pnl || 0) >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`} />
//                   </div>

//                   <div className="absolute -left-[85px] md:-left-[95px] top-1/2 -translate-y-1/2 w-16 md:w-20 text-right">
//                     <div className="text-xs font-bold text-slate-300">
//                       {formatTime(trade.activated_at || trade.created_at)}
//                     </div>
//                     <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mt-0.5">Entry</div>
//                   </div>

//                   <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 flex flex-col xl:flex-row items-center justify-between opacity-80 hover:opacity-100 transition-opacity shadow-sm hover:shadow-md">
//                     <div className="flex flex-col md:flex-row items-start md:items-center gap-3 w-full xl:w-auto mb-4 xl:mb-0">
//                       <div className="flex items-center gap-3">
//                         <span className={`px-2 py-1 rounded text-[10px] font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/10 text-rose-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
//                           {trade.action}
//                         </span>
//                         <span className="text-lg font-bold text-white">{trade.ticker}</span>
//                         <span className="text-[10px] text-slate-400 uppercase font-bold border border-slate-700 px-2 py-0.5 rounded bg-slate-950">
//                           {trade.status.replace('CLOSED_', '')}
//                         </span>
//                       </div>
                      
//                       <div className="text-[11px] text-slate-500 flex items-center gap-1.5 md:ml-2">
//                         <Clock className="w-3 h-3" />
//                         Hold: <span className="text-slate-400 font-mono">{formatHoldTime(trade.activated_at || trade.created_at, trade.closed_at)}</span>
//                       </div>
//                     </div>

//                     <div className="flex items-center gap-6 w-full xl:w-auto justify-between xl:justify-end">
//                       <div className="flex items-center gap-6">
//                         <div className="flex flex-col text-right hidden sm:flex">
//                           <span className="text-slate-500 text-[10px] uppercase">Entry Px</span>
//                           <span className="font-mono text-slate-300 text-sm">₹{trade.entry_price}</span>
//                         </div>
//                         <div className="flex flex-col text-right hidden sm:flex">
//                           <span className="text-slate-500 text-[10px] uppercase">Exit Px</span>
//                           <span className="font-mono text-slate-300 text-sm">₹{trade.live_price || trade.entry_price}</span>
//                         </div>
//                         <div className="flex flex-col text-right min-w-[80px]">
//                           <span className="text-slate-500 text-[10px] uppercase">Final PnL</span>
//                           <span className={`font-black text-lg ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}>
//                             {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
//                           </span>
//                         </div>
//                       </div>

//                       <div className="flex flex-col text-right border-l border-slate-800 pl-4 ml-2 min-w-[65px]">
//                         <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mb-0.5">Exit</div>
//                         <div className="text-xs font-bold text-slate-300">
//                           {formatTime(trade.closed_at)}
//                         </div>
//                       </div>

//                     </div>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           )}
//         </div>

//       </div>
//     </div>
//   );
// }

import React, { useState, useEffect } from 'react';
import { Activity, Check, X, ShieldAlert, Zap, Wallet, TrendingUp, ArrowUpRight, Brain, Copy, CheckCheck, Clock, History, Octagon, Settings } from 'lucide-react';

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

// --- NEW: Risk Scan Circular Loader ---
// Calculates time until the next 5-minute server cron cycle
const RiskScanLoader = ({ now }) => {
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  
  // Total seconds elapsed in the current 5-minute block
  const elapsedSeconds = (minutes % 5) * 60 + seconds;
  const totalSeconds = 5 * 60; // 300 seconds
  const progress = (elapsedSeconds / totalSeconds) * 100;
  
  // SVG Math for the circle stroke
  const radius = 6.5;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  return (
    <div className="flex items-center gap-1.5 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20" title="Next Risk Scan in 5 min interval">
      <span className="text-[10px] text-blue-400 font-semibold uppercase tracking-wider mt-px">
        🛡️ AI Protected
      </span>
      <div className="relative flex items-center justify-center">
        <svg width="16" height="16" className="transform -rotate-90">
          <circle cx="8" cy="8" r={radius} stroke="currentColor" strokeWidth="2" fill="none" className="text-blue-900/40" />
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

// --- Helper for Closed Trades Hold Time (Fixed NaN issue) ---
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
  
  const [autoDeploy, setAutoDeploy] = useState(false);
  const [startingCapital, setStartingCapital] = useState(10000);
  const [loading, setLoading] = useState(true);
  const [copiedField, setCopiedField] = useState(null);

  // --- Real-time clock for the Progress Bar & Loader logic ---
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
                      className="absolute w-[2px] bg-slate-800/60 z-0" 
                      style={{ left: '-2px', top: '24px', height: 'calc(100% + 32px)' }} 
                    />
                  )}

                  {index < activeTimeline.length - 1 && progress > 0 && (
                    <div
                      className="absolute w-[2px] bg-blue-500 z-10 transition-all duration-1000 ease-linear shadow-[0_0_8px_rgba(59,130,246,0.6)]"
                      style={{ left: '-2px', top: '24px', height: `calc((100% + 32px) * ${progress / 100})` }}
                    />
                  )}

                  <div className={`absolute -left-[9px] top-4 w-4 h-4 rounded-full bg-slate-950 border-2 flex items-center justify-center z-20 transition-colors duration-500 ${isPast ? 'border-blue-600' : isPresent ? 'border-blue-400 shadow-[0_0_12px_rgba(96,165,250,0.4)]' : 'border-slate-800'}`}>
                    <div className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${isPast ? 'bg-blue-600' : isPresent ? 'bg-blue-400 animate-pulse' : 'bg-slate-800'}`} />
                  </div>

                  <div className="absolute -left-[85px] md:-left-[95px] top-3.5 w-16 md:w-20 text-right">
                    <div className={`text-xs transition-colors duration-500 ${isPresent ? 'text-blue-400 font-black tracking-wide' : isPast ? 'text-slate-400 font-bold' : 'text-slate-600 font-medium'}`}>
                      {slot.displayTime}
                    </div>
                    <div className={`text-[9px] uppercase tracking-wider font-semibold mt-0.5 ${isPresent ? 'text-blue-500/70' : 'text-slate-600'}`}>
                      Bucket
                    </div>
                  </div>

                  {slot.trades.length === 0 ? (
                    <div className={`h-full border border-dashed rounded-xl flex items-center px-5 py-4 transition-colors duration-500 ${isPresent ? 'bg-blue-900/10 border-blue-500/30' : 'bg-slate-900/20 border-slate-800/40'}`}>
                      <span className={`text-xs font-mono ${isPresent ? 'text-blue-400/80' : 'text-slate-600'}`}>
                        {isPresent ? "Scanning for active allocations..." : "No active allocations generated in this interval"}
                      </span>
                    </div>
                  ) : (
                    <div className="grid gap-4 z-30 relative">
                      {slot.trades.map(trade => (
                        <div key={trade.id} className={`bg-slate-900 border rounded-xl p-5 hover:border-slate-600 transition-colors shadow-lg relative overflow-hidden ${isPresent ? 'border-blue-500/30' : 'border-slate-800'}`}>
                          
                          {/* FORCE STOP BUTTON */}
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
                              
                              {/* --- THE NEW 5 MINUTE RISK MANAGER LOADER --- */}
                              <RiskScanLoader now={now} />
                              
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
              );
            })}
          </div>
        </div>

        {/* --- SECTION 3: CLOSED TRADES LOG --- */}
        <div>
          <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-2 mt-4">
            <History className="text-purple-400 w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-300 uppercase tracking-widest">Today's Closed Trades</h2>
          </div>

          {sortedClosedTrades.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-500 text-sm">
              No trades finalized today. Let the AI work!
            </div>
          ) : (
            <div className="relative ml-20 md:ml-24 border-l-2 border-slate-800/60 pb-4">
              {sortedClosedTrades.map((trade, index) => (
                <div key={trade.id} className="relative mb-6 last:mb-0 pl-6 md:pl-8">
                  
                  <div className="absolute -left-[9px] top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-slate-950 border-2 border-slate-700 flex items-center justify-center z-10">
                    <div className={`w-1.5 h-1.5 rounded-full ${(trade.current_pnl || 0) >= 0 ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                  </div>

                  <div className="absolute -left-[85px] md:-left-[95px] top-1/2 -translate-y-1/2 w-16 md:w-20 text-right">
                    <div className="text-xs font-bold text-slate-300">
                      {formatTime(trade.activated_at || trade.created_at)}
                    </div>
                    <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mt-0.5">Entry</div>
                  </div>

                  <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 flex flex-col xl:flex-row items-center justify-between opacity-80 hover:opacity-100 transition-opacity shadow-sm hover:shadow-md">
                    <div className="flex flex-col md:flex-row items-start md:items-center gap-3 w-full xl:w-auto mb-4 xl:mb-0">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 rounded text-[10px] font-black tracking-wider ${trade.action.includes('SHORT') ? 'bg-rose-500/10 text-rose-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
                          {trade.action}
                        </span>
                        <span className="text-lg font-bold text-white">{trade.ticker}</span>
                        <span className="text-[10px] text-slate-400 uppercase font-bold border border-slate-700 px-2 py-0.5 rounded bg-slate-950">
                          {trade.status.replace('CLOSED_', '')}
                        </span>
                      </div>
                      
                      <div className="text-[11px] text-slate-500 flex items-center gap-1.5 md:ml-2">
                        <Clock className="w-3 h-3" />
                        Hold: <span className="text-slate-400 font-mono">{formatHoldTime(trade.activated_at || trade.created_at, trade.closed_at)}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-6 w-full xl:w-auto justify-between xl:justify-end">
                      <div className="flex items-center gap-6">
                        <div className="flex flex-col text-right hidden sm:flex">
                          <span className="text-slate-500 text-[10px] uppercase">Entry Px</span>
                          <span className="font-mono text-slate-300 text-sm">₹{trade.entry_price}</span>
                        </div>
                        <div className="flex flex-col text-right hidden sm:flex">
                          <span className="text-slate-500 text-[10px] uppercase">Exit Px</span>
                          <span className="font-mono text-slate-300 text-sm">₹{trade.live_price || trade.entry_price}</span>
                        </div>
                        <div className="flex flex-col text-right min-w-[80px]">
                          <span className="text-slate-500 text-[10px] uppercase">Final PnL</span>
                          <span className={`font-black text-lg ${(trade.current_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-500'}`}>
                            {(trade.current_pnl || 0) >= 0 ? '+' : ''}₹{(trade.current_pnl || 0).toFixed(2)}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-col text-right border-l border-slate-800 pl-4 ml-2 min-w-[65px]">
                        <div className="text-[9px] text-slate-500 uppercase tracking-wider font-semibold mb-0.5">Exit</div>
                        <div className="text-xs font-bold text-slate-300">
                          {formatTime(trade.closed_at)}
                        </div>
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