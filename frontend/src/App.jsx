import React, { useState } from 'react'
import {
  AuthProvider, useAuth,
  Sidebar, MetricCard, ScoreStatus,
  DriversChart, StockChart, NewsSection,
  MarketBadge, Footer, AlertManager, NotificationBell,
  ScoreHistoryChart,
  SkeletonLoader, ErrorStateDisplay, SectorBenchmark,
  ErrorBoundary, DownloadPDFButton, SourceAttribution
} from './components/components'
import Login from './pages/Login'
import Register from './pages/Register'

// -------------------------
// Configuration
// -------------------------
const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ||
  (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api/v1/score'
    : 'https://credlens-api.onrender.com/api/v1/score')

// -------------------------
// Helpers
// -------------------------
function formatMarketCap(mc, currency = 'USD') {
  if (mc == null) return 'N/A'
  const symbol = currency === 'INR' ? '₹' : '$'

  if (currency === 'INR') {
    if (mc >= 1e12) return `${symbol}${(mc / 1e12).toFixed(2)} T`
    if (mc >= 1e7) return `${symbol}${(mc / 1e7).toFixed(2)} Cr`
    if (mc >= 1e5) return `${symbol}${(mc / 1e5).toFixed(2)} L`
    return `${symbol}${mc.toLocaleString('en-IN')}`
  }

  if (mc >= 1e12) return `${symbol}${(mc / 1e12).toFixed(2)} T`
  if (mc >= 1e9) return `${symbol}${(mc / 1e9).toFixed(2)} B`
  if (mc >= 1e6) return `${symbol}${(mc / 1e6).toFixed(2)} M`
  return `${symbol}${mc}`
}

// -------------------------
// User Header
// -------------------------
function UserHeader() {
  const { user, isAuthenticated, logout } = useAuth()

  if (!isAuthenticated) return null

  return (
    <div className="user-header">
      <div className="user-info">
        <i className="fa-solid fa-circle-user"></i>
        <span className="user-name">{user?.full_name || user?.email}</span>
      </div>
      <button className="user-logout" onClick={logout} title="Sign out">
        <i className="fa-solid fa-right-from-bracket"></i>
      </button>
    </div>
  )
}

function DashboardHeader({ onOpenAlerts, onOpenAuth }) {
  return (
    <div className="app-header">
      <div className="app-title">
        <i className="fa-solid fa-arrow-trend-up"></i> CredLens
      </div>
      <div className="app-header-right">
        <div className="app-subtitle">Credit Scorecard</div>
        <NotificationBell onOpenAlerts={onOpenAlerts} onOpenAuth={onOpenAuth} />
        <UserHeader onOpenAuth={onOpenAuth} />
      </div>
    </div>
  )
}

// Helper for automatic silent retry on momentary server blips/reloads
async function fetchWithAutoRetry(url, options, maxRetries = 2, delayMs = 1200) {
  let lastError
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fetch(url, options)
    } catch (err) {
      lastError = err
      if (err.name === 'AbortError' || attempt === maxRetries) {
        throw err
      }
      await new Promise((res) => setTimeout(res, delayMs))
    }
  }
  throw lastError
}

// -------------------------
// Dashboard (Main App Content)
// -------------------------
export function Dashboard({ onOpenAuth }) {
  const { isAuthenticated } = useAuth()
  const [data, setData] = useState(null)
  const [compareData, setCompareData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [currentTicker, setCurrentTicker] = useState('')
  const [alertsOpen, setAlertsOpen] = useState(false)
  const [mode, setMode] = useState('single') // 'single' | 'compare'
  
  // Frontend caching layer (Priority 4, Item 14)
  const [frontendCache, setFrontendCache] = useState({})
  const [fetchTime, setFetchTime] = useState(null)

  const handleAnalyze = async (tickerInput) => {
    setLoading(true)
    setError(null)
    setData(null)
    setCompareData([])
    setCurrentTicker(tickerInput)

    const now = new Date().toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })

    if (mode === 'compare') {
      const tickers = tickerInput
        .split(',')
        .map((t) => t.trim().toUpperCase())
        .filter(Boolean)

      // Caching check for compare mode
      const cachedResults = []
      const tickersToFetch = []

      tickers.forEach((t) => {
        if (frontendCache[t]) {
          cachedResults.push(frontendCache[t].data)
        } else {
          tickersToFetch.push(t)
        }
      })

      try {
        const fetchedResults = await Promise.all(
          tickersToFetch.map(async (t) => {
            const controller = new AbortController()
            const id = setTimeout(() => controller.abort(), 45000)

            try {
              const res = await fetchWithAutoRetry(`${BACKEND_URL}/${t}`, { signal: controller.signal })
              clearTimeout(id)

              if (!res.ok) {
                if (res.status === 429) {
                  throw { ticker: t, type: 'RATE_LIMIT', message: 'API rate limit hit' }
                }
                const errBody = await res.json().catch(() => ({}))
                throw {
                  ticker: t,
                  type: errBody.type || 'SERVER_ERROR',
                  message: errBody.detail || `Failed to fetch data for ${t}`,
                }
              }
              const resultData = await res.json()
              
              // Cache single result
              setFrontendCache((prev) => ({
                ...prev,
                [t]: { data: resultData, time: now },
              }))
              
              return resultData
            } catch (err) {
              clearTimeout(id)
              if (err.name === 'AbortError') {
                throw { ticker: t, type: 'TIMEOUT', message: 'API request timed out' }
              }
              throw err
            }
          })
        )

        const finalResults = [...cachedResults, ...fetchedResults]
        setCompareData(finalResults)
        setFetchTime(now)
      } catch (err) {
        setError({
          type: err.type || 'TIMEOUT',
          message: err.message || 'Error executing batch peer comparison. Please verify your connection.',
        })
      } finally {
        setLoading(false)
      }
    } else {
      // Single Ticker Mode - check cache first
      if (frontendCache[tickerInput]) {
        setData(frontendCache[tickerInput].data)
        setFetchTime(frontendCache[tickerInput].time)
        setLoading(false)
        return
      }

      const controller = new AbortController()
      const id = setTimeout(() => controller.abort(), 45000) // 45s timeout check

      try {
        const res = await fetchWithAutoRetry(`${BACKEND_URL}/${tickerInput}`, { signal: controller.signal })
        clearTimeout(id)

        if (!res.ok) {
          if (res.status === 429) {
            setError({
              type: 'RATE_LIMIT',
              message: 'Rate limit hit. Please wait a moment before trying again.',
            })
            setLoading(false)
            return
          }
          const errBody = await res.json().catch(() => ({}))
          if (errBody.type === 'INVALID_TICKER') {
            setError({
              type: 'INVALID_TICKER',
              message: `Ticker '${tickerInput}' not found. Verify ticker name and suffix for Indian stocks (.NS / .BO).`,
            })
          } else {
            setError({
              type: 'SERVER_ERROR',
              message: 'An unexpected backend database error occurred.',
            })
          }
          setLoading(false)
          return
        }

        const apiData = await res.json()
        
        // Save to cache
        setFrontendCache((prev) => ({
          ...prev,
          [tickerInput]: { data: apiData, time: now },
        }))

        setData(apiData)
        setFetchTime(now)
      } catch (err) {
        clearTimeout(id)
        if (err.name === 'AbortError') {
          setError({
            type: 'TIMEOUT',
            message: 'Connection timed out. The credit server did not respond within 45 seconds.',
          })
        } else {
          setError({
            type: 'TIMEOUT',
            message: 'Error connecting to the backend API. Please ensure the server is running.',
          })
        }
      } finally {
        setLoading(false)
      }
    }
  }

  // Extract single-mode data
  const scoreResult = data?.score_result
  const info = data?.company_info || {}
  const companyName = data?.company_name || currentTicker
  const score = scoreResult?.stability_score ?? 0
  const assessmentType = scoreResult?.assessment_type
  const rawSentiment = scoreResult?.latest_sentiment ?? 0
  const sentiment = Math.abs(rawSentiment) < 0.005 ? 0 : rawSentiment
  const currency = data?.currency || 'USD'
  const market = data?.market || 'US'
  const exchange = data?.exchange || ''
  const flag = data?.flag || '🇺🇸'
  const agencyRating = data?.agency_rating || 'N/A'
  const modelSource = scoreResult?.model_source || ''

  const sentimentText =
    sentiment > 0.05 ? 'Positive Press (30d)' : sentiment < -0.05 ? 'Negative Press (30d)' : 'Neutral Tone (30d)'
  const sentimentDeltaType =
    sentiment > 0.05 ? 'positive' : sentiment < -0.05 ? 'negative' : 'neutral-outlook'

  const outlookLabel =
    assessmentType === 'Heuristic'
      ? 'Heuristic'
      : score > 75
        ? 'Stable Outlook'
        : score > 50
          ? 'Neutral Outlook'
          : 'Volatile Outlook'

  const outlookDeltaType =
    assessmentType === 'Heuristic'
      ? 'heuristic'
      : score > 75
        ? 'positive'
        : score > 50
          ? 'neutral-outlook'
          : 'negative'

  const ratingLabel = market === 'IN' ? 'CRISIL/ICRA Rating' : 'S&P Rating'

  // Market Cap classification for Card 3
  const capVal = info.marketCap
  let capTier = 'Public Equity'
  if (capVal) {
    if (market === 'IN') {
      capTier = capVal >= 8e11 ? 'Mega Cap Tier' : capVal >= 1.5e11 ? 'Large Cap Tier' : capVal >= 4e10 ? 'Mid Cap Tier' : 'Small Cap Tier'
    } else {
      capTier = capVal >= 2e11 ? 'Mega Cap Tier' : capVal >= 1e10 ? 'Large Cap Tier' : capVal >= 2e9 ? 'Mid Cap Tier' : 'Small Cap Tier'
    }
  }

  // P/E valuation context for Card 4
  const peVal = info.trailingPE
  let peLabel = 'TTM Multiple'
  let peDeltaType = 'neutral-outlook'
  if (peVal == null || peVal < 0) {
    peLabel = 'Unprofitable (TTM)'
    peDeltaType = 'negative'
  } else if (peVal < 15) {
    peLabel = 'Attractive Valuation'
    peDeltaType = 'positive'
  } else if (peVal <= 28) {
    peLabel = 'Fair Valuation (TTM)'
    peDeltaType = 'neutral-outlook'
  } else {
    peLabel = 'Growth Multiple (TTM)'
    peDeltaType = 'neutral-outlook'
  }

  // Rating grade context for Card 5
  const upperRating = (agencyRating || '').toUpperCase()
  const isInvestmentGrade = upperRating.includes('AAA') || upperRating.includes('AA') || upperRating.includes('A') || upperRating.includes('BBB')
  const ratingGrade = isInvestmentGrade ? 'Investment Grade' : (agencyRating === 'N/A' ? 'Unrated' : 'Speculative Grade')
  const ratingDeltaType = isInvestmentGrade ? 'positive' : 'negative'
  const agencyUrl = market === 'IN'
    ? 'https://www.crisilratings.com'
    : 'https://www.spglobal.com/ratings/'

  return (
    <div className="app-layout">
      <Sidebar 
        onAnalyze={handleAnalyze} 
        isLoading={loading} 
        mode={mode} 
        setMode={setMode} 
        onOpenAuth={onOpenAuth}
      />

      <main className="main-content">
        {/* Header */}
        <DashboardHeader
          onOpenAlerts={() => setAlertsOpen(true)}
          onOpenAuth={onOpenAuth}
        />

        {/* Loading Skeleton Placeholder (Priority 2, Item 7) */}
        {loading && <SkeletonLoader />}

        {/* Detailed Error States (Priority 2, Item 8) */}
        {error && !loading && (
          <ErrorStateDisplay
            errorType={error.type}
            message={error.message}
            onRetry={() => handleAnalyze(currentTicker)}
          />
        )}

        {/* Single Ticker Results */}
        {data && !loading && !error && mode === 'single' && (
          <>
            <div className="analysis-header">
              <h2 className="section-title">Analysis for {companyName}</h2>
              <div className="analysis-badges">
                <MarketBadge
                  market={market}
                  exchange={exchange}
                  flag={flag}
                  currency={currency}
                />
                {modelSource && (
                  <span className="model-source-badge" title="Model source">
                    <i className="fa-solid fa-brain"></i> {modelSource}
                  </span>
                )}
                {fetchTime && (
                  <span className="last-refreshed-badge" title={`Data fetched on ${fetchTime}`}>
                    <i className="fa-regular fa-clock"></i> Last refreshed: {fetchTime}
                  </span>
                )}
                <DownloadPDFButton ticker={currentTicker} companyName={companyName} onOpenAuth={onOpenAuth} />
              </div>
            </div>

            <ScoreStatus score={score} assessmentType={assessmentType} />

            {/* Metric Cards Row */}
            <div className="metrics-row">
              <MetricCard
                label="Stability Score"
                value={score}
                delta={outlookLabel}
                deltaType={outlookDeltaType}
              />

              <MetricCard
                label="News Sentiment"
                value={sentiment.toFixed(2)}
                delta={sentimentText}
                deltaType={sentimentDeltaType}
              />
              
              <MetricCard
                label="Market Cap"
                value={formatMarketCap(info.marketCap, currency)}
                delta={capTier}
                deltaType="tier"
              />
              
              <MetricCard
                label="P/E Ratio"
                value={info.trailingPE != null ? info.trailingPE.toFixed(2) : 'N/A'}
                delta={peLabel}
                deltaType={peDeltaType}
              />
              
              <MetricCard
                label={ratingLabel}
                value={agencyRating}
                delta={ratingGrade}
                deltaType={ratingDeltaType}
                subtext="per internal registry"
                subtextLink={agencyUrl}
              />
            </div>

            <div className="dashboard-grid-widgets">
              {/* Sector Benchmark peer comparison (Priority 3, Item 11) */}
              <ErrorBoundary>
                <SectorBenchmark ticker={currentTicker} companyScore={score} sectorName={info.sector} sectorAverage={data?.sector_average} />
              </ErrorBoundary>
            </div>

            <hr className="divider" />

            {/* Charts Row */}
            <div className="charts-row">
              <ErrorBoundary>
                <DriversChart
                  explanation={scoreResult.explanation}
                  assessmentType={assessmentType}
                />
              </ErrorBoundary>
              <ErrorBoundary>
                <StockChart
                  stockHistory={data.stock_history}
                  ticker={currentTicker}
                  currency={currency}
                />
              </ErrorBoundary>
            </div>

            <hr className="divider" />

            {/* Score History (Priority 1, Item 4) */}
            <ErrorBoundary>
              <ScoreHistoryChart ticker={currentTicker} />
            </ErrorBoundary>

            <hr className="divider" />

            {/* News */}
            <ErrorBoundary>
              <NewsSection news={data.recent_news_for_context} />
            </ErrorBoundary>
          </>
        )}

        {/* Compare Tickers Mode Results (Priority 3, Item 12) */}
        {compareData && compareData.length > 0 && !loading && !error && mode === 'compare' && (
          <div className="compare-dashboard animate-fade-in">
            <div className="analysis-header">
              <h2 className="section-title">Peer Credit Comparison</h2>
              <div className="analysis-badges">
                {fetchTime && (
                  <span className="last-refreshed-badge" title={`Data fetched on ${fetchTime}`}>
                    <i className="fa-regular fa-clock"></i> Last refreshed: {fetchTime}
                  </span>
                )}
                <DownloadPDFButton ticker={currentTicker} companyName="Batch Comparison" onOpenAuth={onOpenAuth} />
              </div>
            </div>

            {/* Grid of scorecard comparison cards */}
            <div className="compare-grid">
              {compareData.map((item, idx) => {
                const itemScoreResult = item.score_result
                const itemScore = itemScoreResult?.stability_score ?? 0
                const isStable = itemScore > 75
                const isNeutral = itemScore > 50
                const cardStatus = isStable ? 'stable' : isNeutral ? 'neutral' : 'volatile'
                const StatusIcon = isStable ? (
                  <i className="fa-solid fa-circle-check"></i>
                ) : isNeutral ? (
                  <i className="fa-solid fa-triangle-exclamation"></i>
                ) : (
                  <i className="fa-solid fa-circle-exclamation"></i>
                )
                const itemInfo = item.company_info || {}
                const itemSentiment = itemScoreResult?.latest_sentiment ?? 0
                
                return (
                  <div key={idx} className={`compare-card ${cardStatus}`}>
                    <div className="compare-card-header">
                      <div className="header-top">
                        <span className="compare-flag">{item.flag || '🇺🇸'}</span>
                        <span className="compare-ticker-badge">{item.ticker}</span>
                      </div>
                      <h3 className="compare-company-title">{item.company_name || item.ticker}</h3>
                    </div>

                    <div className="compare-score-display">
                      <div className="score-main">
                        <span className="score-val">{itemScore}</span>
                        <span className="score-lbl">Stability Score</span>
                      </div>
                      <div className={`status-badge-inline ${cardStatus}`}>
                        {StatusIcon} <span>{itemScore > 75 ? 'Stable' : itemScore > 50 ? 'Neutral' : 'Volatile'}</span>
                      </div>
                    </div>

                    <div className="compare-metrics-list">
                      <div className="compare-row-item">
                        <span className="lbl">S&P/CRISIL Rating</span>
                        <span className="val">{item.agency_rating || 'N/A'}</span>
                      </div>
                      <div className="compare-row-item">
                        <span className="lbl">Sentiment</span>
                        <span className="val">
                          {itemSentiment > 0.05 ? 'Positive' : itemSentiment < -0.05 ? 'Negative' : 'Neutral'} ({itemSentiment.toFixed(2)})
                        </span>
                      </div>
                      <div className="compare-row-item">
                        <span className="lbl">Market Cap</span>
                        <span className="val">{formatMarketCap(itemInfo.marketCap, item.currency)}</span>
                      </div>
                      <div className="compare-row-item">
                        <span className="lbl">P/E Ratio</span>
                        <span className="val">{itemInfo.trailingPE != null ? itemInfo.trailingPE.toFixed(2) : 'N/A'}</span>
                      </div>
                    </div>

                    {/* Benchmark inside card */}
                    <SectorBenchmark 
                      ticker={item.ticker} 
                      companyScore={itemScore} 
                      sectorName={itemInfo.sector} 
                      sectorAverage={item.sector_average}
                    />
                  </div>
                )
              })}
            </div>

            <hr className="divider" />

            {/* Side-by-side Stock History comparison */}
            <div className="compare-charts-grid">
              {compareData.map((item, idx) => (
                <div key={idx} className="compare-chart-card">
                  <ErrorBoundary>
                    <StockChart 
                      stockHistory={item.stock_history} 
                      ticker={item.ticker} 
                      currency={item.currency} 
                    />
                  </ErrorBoundary>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!data && compareData.length === 0 && !loading && !error && (
          <div className="empty-state">
            <div className="empty-state-icon">
              <i className="fa-solid fa-chart-line"></i>
            </div>
            <div className="empty-state-title">
              Ready to Analyze
            </div>
            <div className="empty-state-text">
              Enter {mode === 'compare' ? '2-3 tickers (separated by commas)' : 'a ticker'} in the sidebar and click{' '}
              <strong>'Analyze'</strong> to begin. Supports both
              <strong> US</strong> 🇺🇸 and <strong>Indian</strong> 🇮🇳 markets.
            </div>
          </div>
        )}

        <Footer />
      </main>

      {/* Alert Manager Panel */}
      <AlertManager isOpen={alertsOpen} onClose={() => setAlertsOpen(false)} onOpenAuth={onOpenAuth} />
    </div>
  )
}

// -------------------------
// Auth Modal Component
// -------------------------
function AuthModal({ isOpen, mode, onClose, onSwitchMode }) {
  if (!isOpen) return null

  return (
    <div className="modal-overlay auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close-btn" onClick={onClose} title="Close">
          <i className="fa-solid fa-xmark"></i>
        </button>
        {mode === 'register' ? (
          <Register onSwitchToLogin={() => onSwitchMode('login')} />
        ) : (
          <Login
            onSwitchToRegister={() => onSwitchMode('register')}
            onLoginSuccess={onClose}
          />
        )}
      </div>
    </div>
  )
}

// -------------------------
// Root App with Auth Flow
// -------------------------
export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

function AppContent() {
  const { loading } = useAuth()
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' })

  // Show loading spinner while checking auth state
  if (loading) {
    return (
      <div className="auth-loading">
        <div className="spinner"></div>
      </div>
    )
  }

  return (
    <>
      <Dashboard onOpenAuth={(mode) => setAuthModal({ isOpen: true, mode: mode || 'login' })} />
      <AuthModal
        isOpen={authModal.isOpen}
        mode={authModal.mode}
        onClose={() => setAuthModal({ isOpen: false, mode: 'login' })}
        onSwitchMode={(mode) => setAuthModal({ isOpen: true, mode })}
      />
    </>
  )
}
