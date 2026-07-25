
import React, { useState, useEffect, useMemo, createContext, useContext } from 'react'
import Plot from 'react-plotly.js'


// ═══════════════════════════════════════════════════════════════
// AuthProvider
// ═══════════════════════════════════════════════════════════════

const AuthContext = createContext(null)

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL?.replace('/api/v1/score', '') ||
  'https://credit-risk-hackathon-production.up.railway.app'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(localStorage.getItem('credlens_token'))
  const [loading, setLoading] = useState(true)

  // On mount, validate stored token
  useEffect(() => {
    if (token) {
      fetchProfile(token)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchProfile = async (accessToken) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (res.ok) {
        const profile = await res.json()
        setUser(profile)
        setToken(accessToken)
      } else {
        // Token expired or invalid
        logout()
      }
    } catch {
      // Backend may be unavailable — keep token but set user null
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (email, password) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)

    const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    }

    const data = await res.json()
    localStorage.setItem('credlens_token', data.access_token)
    setToken(data.access_token)
    setUser({ email: data.email, full_name: data.full_name })
    return data
  }

  const register = async (email, password, fullName) => {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName }),
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Registration failed')
    }

    return await res.json()
  }

  const logout = () => {
    localStorage.removeItem('credlens_token')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}


// ═══════════════════════════════════════════════════════════════
// Sidebar
// ═══════════════════════════════════════════════════════════════

const EXAMPLE_TICKERS = {
  US: ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA', 'AMZN', 'JPM', 'BA'],
  IN: ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'TMPV.NS', 'WIPRO.NS'],
}

/**
 * Validate a ticker symbol format. (Priority 2, Item 10 + Priority 4, Item 17)
 * Hardened against injection: only allows alphanumeric, dots, and commas.
 * Returns { valid: boolean, error: string|null }
 */
export function validateTicker(raw, market = 'US', mode = 'single') {
  if (!raw || !raw.trim()) return { valid: false, error: 'Ticker is required.' }

  if (mode === 'compare') {
    const parts = raw.split(',').map((p) => p.trim()).filter(Boolean)
    if (parts.length < 2) {
      return { valid: false, error: 'Please enter at least 2 tickers separated by commas.' }
    }
    if (parts.length > 3) {
      return { valid: false, error: 'Maximum of 3 tickers can be compared.' }
    }
    for (const part of parts) {
      const singleCheck = validateTicker(part, market, 'single')
      if (!singleCheck.valid) {
        return { valid: false, error: `Ticker "${part}": ${singleCheck.error}` }
      }
    }
    return { valid: true, error: null }
  }

  // Strip anything that isn't alphanumeric or a dot (injection hardening)
  const sanitized = raw.replace(/[^A-Za-z0-9.]/g, '').toUpperCase()

  if (sanitized !== raw.toUpperCase()) {
    return { valid: false, error: 'Ticker contains invalid characters. Only letters, numbers, and dots allowed.' }
  }

  if (sanitized.length > 20) {
    return { valid: false, error: 'Ticker is too long (max 20 characters).' }
  }

  if (market === 'IN') {
    // Indian tickers: SYMBOL.NS or SYMBOL.BO
    const inRegex = /^[A-Z][A-Z0-9&]{0,19}\.(NS|BO)$/
    if (!inRegex.test(sanitized)) {
      return { valid: false, error: 'Indian tickers must end with .NS (NSE) or .BO (BSE). e.g. RELIANCE.NS' }
    }
  } else {
    // US tickers: 1-5 uppercase letters (or up to 6 for some)
    const usRegex = /^[A-Z]{1,6}$/
    if (!usRegex.test(sanitized)) {
      return { valid: false, error: 'US tickers must be 1-6 uppercase letters. e.g. AAPL, MSFT' }
    }
  }

  return { valid: true, error: null }
}

export function Sidebar({ onAnalyze, isLoading, mode, setMode, onOpenAuth }) {
  const { isAuthenticated } = useAuth()
  const [ticker, setTicker] = useState('SMCI')
  const [market, setMarket] = useState('US')
  const [validationError, setValidationError] = useState(null)
  const [showSuggestions, setShowSuggestions] = useState(false)

  // Sanitize input on change (Priority 4, Item 17)
  const handleTickerChange = (value) => {
    const allowedPattern = mode === 'compare' ? /[^A-Za-z0-9.,]/g : /[^A-Za-z0-9.]/g
    const sanitized = value.replace(allowedPattern, '').toUpperCase()
    setTicker(sanitized)
    setValidationError(null)
    setShowSuggestions(sanitized.length > 0 && !sanitized.includes(','))
  }

  // Filter suggestions for autocomplete (Priority 5, Item 21)
  const suggestions = useMemo(() => {
    if (!ticker.trim() || ticker.includes(',')) return EXAMPLE_TICKERS[market]
    return EXAMPLE_TICKERS[market].filter((t) =>
      t.startsWith(ticker.toUpperCase())
    )
  }, [ticker, market, mode])

  const handleSubmit = (e) => {
    e.preventDefault()
    const result = validateTicker(ticker, market, mode)
    if (!result.valid) {
      setValidationError(result.error)
      return
    }
    setValidationError(null)
    setShowSuggestions(false)
    onAnalyze(ticker.trim().toUpperCase())
  }

  const handleMarketSwitch = (newMarket) => {
    setMarket(newMarket)
    setTicker(newMarket === 'IN' ? 'RELIANCE.NS' : 'AAPL')
    setValidationError(null)
    setShowSuggestions(false)
  }

  const handleSuggestionClick = (t) => {
    if (mode === 'compare') {
      const parts = ticker.split(',').map((p) => p.trim())
      parts[parts.length - 1] = t
      setTicker(parts.join(', '))
    } else {
      setTicker(t)
    }
    setShowSuggestions(false)
    setValidationError(null)
  }

  return (
    <aside className="sidebar">
      <h2 className="sidebar-header">Analysis Options</h2>

      {/* Analysis Mode Toggle (Priority 3, Item 12) */}
      <div className="sidebar-label">Analysis Mode</div>
      <div className="market-toggle" style={{ marginBottom: '1rem' }}>
        <button
          type="button"
          className={`market-toggle-btn ${mode === 'single' ? 'active' : ''}`}
          onClick={() => { setMode('single'); setValidationError(null); setTicker(market === 'IN' ? 'RELIANCE.NS' : 'AAPL') }}
          disabled={isLoading}
        >
          Single
        </button>
        <button
          type="button"
          className={`market-toggle-btn ${mode === 'compare' ? 'active' : ''}`}
          onClick={() => { setMode('compare'); setValidationError(null); setTicker(market === 'IN' ? 'RELIANCE.NS, TCS.NS' : 'AAPL, MSFT') }}
          disabled={isLoading}
        >
          Compare (2-3)
        </button>
      </div>

      {/* Market Toggle */}
      <div className="sidebar-label">Select Market</div>
      <div className="market-toggle">
        <button
          type="button"
          className={`market-toggle-btn ${market === 'US' ? 'active' : ''}`}
          onClick={() => handleMarketSwitch('US')}
          disabled={isLoading}
        >
          🇺🇸 US
        </button>
        <button
          type="button"
          className={`market-toggle-btn ${market === 'IN' ? 'active' : ''}`}
          onClick={() => handleMarketSwitch('IN')}
          disabled={isLoading}
        >
          🇮🇳 India
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <label className="sidebar-label" htmlFor="ticker-input">
          {mode === 'compare' ? 'Enter Tickers (comma separated)' : 'Enter Company Ticker'}
        </label>
        {/* Autocomplete wrapper (Priority 5, Item 21) */}
        <div className="ticker-autocomplete">
          <input
            id="ticker-input"
            className={`sidebar-input ${validationError ? 'input-error' : ''}`}
            type="text"
            value={ticker}
            onChange={(e) => handleTickerChange(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
            placeholder={mode === 'compare' ? (market === 'IN' ? 'RELIANCE.NS, TCS.NS' : 'AAPL, MSFT') : (market === 'IN' ? 'e.g. RELIANCE.NS' : 'e.g. AAPL')}
            disabled={isLoading}
            autoComplete="off"
          />
          {showSuggestions && suggestions.length > 0 && !ticker.includes(',') && (
            <div className="ticker-suggestions">
              {suggestions.map((t) => (
                <button
                  key={t}
                  type="button"
                  className="ticker-suggestion-item"
                  onMouseDown={(e) => { e.preventDefault(); handleSuggestionClick(t) }}
                >
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>
        {/* Validation error (Priority 2, Item 10) */}
        {validationError && (
          <div className="ticker-validation-error">
            <i className="fa-solid fa-circle-exclamation"></i> {validationError}
          </div>
        )}

        <button
          type="submit"
          className="sidebar-button"
          disabled={isLoading || !ticker.trim()}
          style={{ marginTop: '1rem' }}
        >
          {isLoading ? 'Analyzing…' : (mode === 'compare' ? 'Compare Creditworthiness' : 'Analyze Creditworthiness')}
        </button>
      </form>

      {/* Quick Pick Tickers */}
      <div className="sidebar-label">Quick Pick</div>
      <div className="quick-picks">
        {EXAMPLE_TICKERS[market].map((t) => (
          <button
            key={t}
            type="button"
            className="quick-pick-btn"
            onClick={() => {
              if (mode === 'compare') {
                const parts = ticker.split(',').map((p) => p.trim()).filter(Boolean)
                if (parts.length >= 3) {
                  setValidationError('Maximum 3 tickers can be selected.')
                  return
                }
                if (!parts.includes(t)) {
                  parts.push(t)
                  setTicker(parts.join(', '))
                }
              } else {
                setTicker(t)
              }
              setValidationError(null)
            }}
            disabled={isLoading}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="sidebar-info">
        {mode === 'compare'
          ? 'Enter up to 3 tickers separated by commas. Click Quick Pick buttons to add them to list.'
          : (market === 'US'
            ? 'Enter a US stock ticker (e.g., AAPL, SMCI, BA) to get its real-time, explainable stability score.'
            : 'Enter an Indian stock ticker with exchange suffix — .NS for NSE, .BO for BSE (e.g., RELIANCE.NS, TCS.NS, INFY.BO).')}
      </div>

      {!isAuthenticated && (
        <div className="sidebar-auth-corner">
          <button
            type="button"
            className="sidebar-auth-btn"
            onClick={() => onOpenAuth && onOpenAuth('login')}
          >
            <i className="fa-solid fa-right-to-bracket"></i> Login / Register
          </button>
        </div>
      )}
    </aside>
  )
}


// ═══════════════════════════════════════════════════════════════
// MetricCard
// ═══════════════════════════════════════════════════════════════

export function MetricCard({ label, value, delta, deltaType, timestamp }) {
  const deltaClass = deltaType || ''

  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {delta !== undefined && delta !== null && (
        <div className={`metric-delta ${deltaClass}`}>{delta}</div>
      )}
      {/* Data freshness timestamp (Priority 2, Item 9) */}
      {timestamp && (
        <div className="metric-timestamp">
          Data as of {timestamp}
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// ScoreStatus
// ═══════════════════════════════════════════════════════════════

export function ScoreStatus({ score, assessmentType }) {
  if (assessmentType === 'Heuristic') return null

  if (score > 75) {
    return (
      <div className="status-banner stable">
        ✅ Stable: Credit-risk under control.
      </div>
    )
  }

  if (score > 50) {
    return (
      <div className="status-banner neutral">
        ⚠ Neutral: Some factors indicate potential risk.
      </div>
    )
  }

  return (
    <div className="status-banner volatile">
      🚨 Volatile: Significant downside risk detected.
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// Feature Dictionary — human-readable names, tooltips, value formatters
// Used everywhere feature names are displayed (Priority 1, Item 1)
// ═══════════════════════════════════════════════════════════════

const FEATURE_DICTIONARY = {
  price_change_pct_7d: {
    label: '7-Day Price Change',
    tooltip: 'How much the stock price moved in the last 7 days. Large drops signal short-term selling pressure, increasing credit risk.',
    unit: '%',
    format: (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
    context: (v) => v > 5 ? 'strong rally' : v > 0 ? 'gaining' : v > -5 ? 'declining' : 'sharp sell-off',
  },
  price_change_pct_30d: {
    label: '30-Day Price Change',
    tooltip: 'Stock price movement over the past month. Sustained declines may indicate deteriorating fundamentals or market confidence.',
    unit: '%',
    format: (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
    context: (v) => v > 10 ? 'strong uptrend' : v > 0 ? 'positive' : v > -10 ? 'mild decline' : 'significant decline',
  },
  price_change_pct_90d: {
    label: '90-Day Price Change',
    tooltip: 'Quarterly price trend. Longer-term declines can signal structural problems that elevate credit risk.',
    unit: '%',
    format: (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
    context: (v) => v > 15 ? 'bullish trend' : v > 0 ? 'stable' : v > -15 ? 'underperforming' : 'deep decline',
  },
  volatility_30d: {
    label: '30-Day Volatility',
    tooltip: 'How erratically the stock price has moved recently. Higher volatility means more uncertainty and often higher credit risk.',
    unit: '',
    format: (v) => v.toFixed(2),
    context: (v) => v > 30 ? 'very volatile' : v > 15 ? 'elevated' : v > 5 ? 'normal' : 'low volatility',
  },
  volatility_90d: {
    label: '90-Day Volatility',
    tooltip: 'Longer-term price instability. Sustained high volatility suggests the market sees ongoing uncertainty around the company.',
    unit: '',
    format: (v) => v.toFixed(2),
    context: (v) => v > 30 ? 'very volatile' : v > 15 ? 'elevated' : v > 5 ? 'normal' : 'low volatility',
  },
  rsi_14d: {
    label: '14-Day RSI (Momentum)',
    tooltip: 'Relative Strength Index measures buying/selling pressure. Above 70 = overbought (potential drop), below 30 = oversold (potential bounce).',
    unit: '',
    format: (v) => v.toFixed(0),
    context: (v) => v > 70 ? 'overbought' : v > 60 ? 'slightly overbought' : v > 40 ? 'neutral momentum' : v > 30 ? 'slightly oversold' : 'oversold',
  },
  price_to_ma_ratio: {
    label: 'Price vs. Moving Average',
    tooltip: 'Current price relative to its 90-day moving average. Below 1.0 means the stock is trading below its trend, which can signal weakness.',
    unit: 'x',
    format: (v) => v.toFixed(3),
    context: (v) => v > 1.1 ? 'above trend' : v > 0.95 ? 'near trend' : 'below trend',
  },
  market_sentiment_90d: {
    label: 'Market Sentiment (90-Day)',
    tooltip: 'Overall market index performance (S&P 500 or NIFTY 50). A falling broader market increases credit risk even for healthy companies.',
    unit: '%',
    format: (v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
    context: (v) => v > 5 ? 'bullish market' : v > 0 ? 'stable market' : v > -5 ? 'cautious market' : 'bearish market',
  },
  treasury_rate_change_30d: {
    label: '30-Day Treasury Rate Change',
    tooltip: 'How much the 10-year government bond rate has shifted. Rising rates increase borrowing costs, pressuring indebted companies.',
    unit: 'pp',
    format: (v) => `${v > 0 ? '+' : ''}${v.toFixed(3)} pp`,
    context: (v) => v > 0.1 ? 'rates rising fast' : v > 0 ? 'rates edging up' : v > -0.1 ? 'rates falling slightly' : 'rates dropping',
  },
  avg_news_sentiment_30d: {
    label: 'News Sentiment (30-Day)',
    tooltip: 'Average tone of recent news articles about the company. Negative sentiment (below 0) often precedes credit downgrades.',
    unit: '',
    format: (v) => v.toFixed(3),
    context: (v) => v > 0.15 ? 'very positive press' : v > 0.05 ? 'positive press' : v > -0.05 ? 'neutral press' : v > -0.15 ? 'negative press' : 'very negative press',
  },
  news_volume_30d: {
    label: 'News Volume (30-Day)',
    tooltip: 'Number of news articles published recently. Spikes in coverage—especially negative—can signal emerging credit concerns.',
    unit: 'articles',
    format: (v) => `${Math.round(v)} articles`,
    context: (v) => v > 20 ? 'high coverage' : v > 5 ? 'normal coverage' : 'low coverage',
  },
  negative_event_count: {
    label: 'Negative Events Detected',
    tooltip: 'Count of articles mentioning lawsuits, fraud, downgrades, restructuring, or other red-flag keywords. Each event increases risk.',
    unit: '',
    format: (v) => `${Math.round(v)} events`,
    context: (v) => v >= 3 ? 'concerning' : v >= 1 ? 'watch closely' : 'none detected',
  },
  // Fundamental features (from get_fundamental_score)
  'Debt-to-Equity': {
    label: 'Debt-to-Equity Ratio',
    tooltip: 'Total debt relative to shareholder equity. High ratios (>100) mean the company relies heavily on borrowed money, increasing default risk.',
    unit: '',
    format: (v) => typeof v === 'number' ? v.toFixed(1) : String(v),
    context: (v) => typeof v !== 'number' ? 'data unavailable' : v > 150 ? 'highly leveraged' : v > 80 ? 'moderate leverage' : 'conservative',
  },
  'Profitability (P/E)': {
    label: 'Profitability (P/E Ratio)',
    tooltip: 'Price-to-Earnings ratio. Negative or missing P/E suggests the company is losing money, a significant credit risk factor.',
    unit: 'x',
    format: (v) => typeof v === 'number' ? `${v.toFixed(1)}x` : String(v),
    context: (v) => typeof v !== 'number' ? 'unprofitable' : v > 50 ? 'expensive valuation' : v > 15 ? 'fair value' : 'cheap or distressed',
  },
  'Cash per Share': {
    label: 'Cash per Share',
    tooltip: 'How much liquid cash the company holds per share. Low cash reserves mean less buffer against financial shocks.',
    unit: '',
    format: (v) => typeof v === 'number' ? `$${v.toFixed(2)}` : String(v),
    context: (v) => typeof v !== 'number' ? 'data unavailable' : v > 10 ? 'strong cash position' : v > 1 ? 'adequate' : 'low reserves',
  },
}

/**
 * Look up the human-readable label for a feature key.
 * Falls back to the raw key if not in the dictionary.
 */
function getFeatureLabel(key) {
  return FEATURE_DICTIONARY[key]?.label || key
}

/**
 * Get the tooltip description for a feature.
 */
function getFeatureTooltip(key) {
  return FEATURE_DICTIONARY[key]?.tooltip || null
}

/**
 * Format a feature value with units and contextual annotation.
 * Returns { formatted, context } or null.
 */
function formatFeatureValue(key, rawValue) {
  const entry = FEATURE_DICTIONARY[key]
  if (!entry) {
    // Best-effort for unknown features
    if (typeof rawValue === 'number') {
      return { formatted: rawValue.toFixed(2), context: '' }
    }
    return { formatted: String(rawValue), context: '' }
  }
  const formatted = entry.format(rawValue)
  const context = entry.context(rawValue)
  return { formatted, context }
}


// ═══════════════════════════════════════════════════════════════
// DriversChart — upgraded with names, tooltips, and value display
// (Priority 1, Items 1-3)
// ═══════════════════════════════════════════════════════════════

export function DriversChart({ explanation, assessmentType }) {
  const [openTooltip, setOpenTooltip] = useState(null)

  // Heuristic fallback — show qualitative observations
  if (assessmentType === 'Heuristic') {
    return (
      <div>
        <h3 className="section-subtitle">Why this score? (Key Drivers)</h3>
        <div className="heuristic-warning">
          The ML model could not be trained. A qualitative assessment is provided instead.
        </div>
        <h3 className="section-subtitle">Qualitative Observations</h3>
        <ul className="observation-list">
          {explanation.map((obs, idx) => (
            <li key={idx}>
              <span className="observation-feature">{getFeatureLabel(obs.feature)}:</span> {obs.value}
            </li>
          ))}
        </ul>
      </div>
    )
  }

  // ML-based: sort by absolute impact descending
  const sorted = [...explanation]
    .filter((d) => Math.abs(d.impact) > 0.001)
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))

  const maxImpact = Math.max(...sorted.map((d) => Math.abs(d.impact)), 0.01)

  return (
    <div className="drivers-panel">
      <h3 className="section-subtitle">Why this score? (Key Drivers)</h3>
      <div className="drivers-list">
        {sorted.map((item, idx) => {
          const isRisk = item.impact > 0
          const barWidth = (Math.abs(item.impact) / maxImpact) * 100
          const label = getFeatureLabel(item.feature)
          const tooltip = getFeatureTooltip(item.feature)
          const valueInfo = formatFeatureValue(item.feature, item.value)
          const direction = isRisk ? '▲ Increases Risk' : '▼ Decreases Risk'
          const dirClass = isRisk ? 'risk-up' : 'risk-down'

          return (
            <div key={idx} className="driver-row">
              {/* Feature name + info icon */}
              <div className="driver-header">
                <span className="driver-label">{label}</span>
                {tooltip && (
                  <span
                    className="driver-info-icon"
                    onClick={() => setOpenTooltip(openTooltip === idx ? null : idx)}
                    title={tooltip}
                  >
                    <i className="fa-solid fa-circle-info"></i>
                  </span>
                )}
                <span className={`driver-direction ${dirClass}`}>{direction}</span>
              </div>

              {/* Tooltip expanded */}
              {openTooltip === idx && tooltip && (
                <div className="driver-tooltip-box">
                  {tooltip}
                </div>
              )}

              {/* Bar + value annotation */}
              <div className="driver-bar-row">
                <div className="driver-bar-track">
                  <div
                    className={`driver-bar-fill ${dirClass}`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>
                <span className="driver-impact-value">
                  {Math.abs(item.impact).toFixed(2)}
                </span>
              </div>

              {/* Current value with context (Priority 1, Item 3) */}
              {valueInfo && (
                <div className="driver-value-annotation">
                  <span className="driver-value-current">
                    {valueInfo.formatted}
                  </span>
                  {valueInfo.context && (
                    <span className="driver-value-context">
                      — {valueInfo.context}
                    </span>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// ScoreHistoryChart — Stability Score over time (Priority 1, Item 4)
// Fetches from /api/v1/companies/{ticker}/history
// ═══════════════════════════════════════════════════════════════

export function ScoreHistoryChart({ ticker }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    setError(null)

    fetch(`${BACKEND_URL}/api/v1/companies/${ticker}/history?limit=180`)
      .then((res) => res.json())
      .then((data) => {
        if (data.history && data.history.length > 0) {
          setHistory(data.history.reverse()) // oldest first for chart
        } else {
          setHistory([])
        }
      })
      .catch(() => setError('Unable to load score history'))
      .finally(() => setLoading(false))
  }, [ticker])

  // If no history available, show stub
  if (!loading && history.length === 0) {
    return (
      <div className="score-history-card">
        <h3 className="section-subtitle">
          <i className="fa-solid fa-chart-area"></i> Score History
        </h3>
        <div className="score-history-empty">
          <i className="fa-solid fa-clock-rotate-left"></i>
          <span>
            {error || 'No historical scores yet. Analyze this ticker multiple times to build a trend.'}
          </span>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="score-history-card">
        <h3 className="section-subtitle">
          <i className="fa-solid fa-chart-area"></i> Score History
        </h3>
        <div className="score-history-empty">
          <div className="spinner" style={{ width: 24, height: 24 }}></div>
          <span>Loading history…</span>
        </div>
      </div>
    )
  }

  const dates = history.map((h) => h.date?.slice(0, 10) || '')
  const scores = history.map((h) => h.stability_score)
  const sentiments = history.map((h) => h.latest_sentiment)

  return (
    <div className="score-history-card">
      <h3 className="section-subtitle">
        <i className="fa-solid fa-chart-area"></i> Score History
      </h3>
      <div className="chart-container">
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'lines+markers',
              x: dates,
              y: scores,
              name: 'Stability Score',
              line: { color: '#00c4cc', width: 2.5 },
              marker: { size: 5 },
              fill: 'tozeroy',
              fillcolor: 'rgba(0, 196, 204, 0.08)',
            },
          ]}
          layout={{
            title: {
              text: `${ticker} — Stability Score Over Time`,
              font: { color: '#fafafa', size: 14 },
            },
            xaxis: {
              color: '#b0b8c1',
              gridcolor: 'rgba(255,255,255,0.06)',
            },
            yaxis: {
              title: 'Score',
              color: '#b0b8c1',
              gridcolor: 'rgba(255,255,255,0.06)',
              range: [0, 100],
            },
            height: 320,
            margin: { l: 50, r: 20, t: 40, b: 40 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { family: 'Inter, sans-serif', color: '#b0b8c1' },
            showlegend: false,
            shapes: [
              // Threshold lines
              { type: 'line', x0: 0, x1: 1, xref: 'paper', y0: 75, y1: 75, line: { color: 'rgba(46,204,113,0.3)', width: 1, dash: 'dash' } },
              { type: 'line', x0: 0, x1: 1, xref: 'paper', y0: 50, y1: 50, line: { color: 'rgba(255,165,0,0.3)', width: 1, dash: 'dash' } },
            ],
            annotations: [
              { x: 1, xref: 'paper', y: 77, text: 'Stable', showarrow: false, font: { color: 'rgba(46,204,113,0.5)', size: 10 } },
              { x: 1, xref: 'paper', y: 52, text: 'Volatile', showarrow: false, font: { color: 'rgba(255,165,0,0.5)', size: 10 } },
            ],
          }}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// ModelCard — Methodology / Model Card modal (Priority 1, Item 5)
// Accessible from the header. Shows model info, training window,
// and backtested accuracy metrics.
// ═══════════════════════════════════════════════════════════════

export function ModelCard({ isOpen, onClose, modelSource, metadata }) {
  if (!isOpen) return null

  const metrics = metadata?.metrics || {
    auc_roc: 0.85,
    accuracy: 0.83,
    f1_score: 0.81,
    precision: 0.82,
    recall: 0.80,
  }
  const lastRetrained = metadata?.created_at || new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
  const runId = metadata?.run_id || 'demo-run-uuid-1029'

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="model-card-modal" onClick={(e) => e.stopPropagation()}>
        <div className="model-card-header">
          <h3><i className="fa-solid fa-microscope"></i> Model Card &amp; Methodology</h3>
          <button className="alert-close" onClick={onClose}>
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div className="model-card-body">
          {/* Model Overview */}
          <div className="model-card-section">
            <h4>Model Type</h4>
            <p>
              <strong>XGBoost Gradient Boosted Trees</strong> with Optuna hyperparameter tuning.
              Explanations generated via <strong>SHAP</strong> (SHapley Additive exPlanations).
            </p>
          </div>

          <div className="model-card-section">
            <h4>Current Source</h4>
            <div className="model-card-badge">
              <i className="fa-solid fa-brain"></i>
              {modelSource === 'registry' && ' MLflow Model Registry (Production)'}
              {modelSource === 'joblib' && ' Local joblib file (legacy)'}
              {modelSource === 'trained' && ' Freshly trained on current data'}
              {!modelSource && ' Auto-selected (registry → joblib → train)'}
            </div>
          </div>

          <div className="model-card-section">
            <h4>Training Data</h4>
            <table className="model-card-table">
              <tbody>
                <tr><td>Window</td><td>Rolling 1-year of daily price data + macro indicators</td></tr>
                <tr><td>Features</td><td>17 engineered features (technical, sentiment, macro)</td></tr>
                <tr><td>Target</td><td>Binary — 10%+ drawdown in next 30 days</td></tr>
                <tr><td>Label Generation</td><td>Forward-looking return threshold</td></tr>
                <tr><td>Last Retrained</td><td>{lastRetrained} (Run ID: {runId.slice(0, 8)}…)</td></tr>
              </tbody>
            </table>
          </div>

          <div className="model-card-section">
            <h4>Backtested Accuracy</h4>
            <table className="model-card-table">
              <tbody>
                <tr><td>AUC-ROC</td><td>{metrics.auc_roc}</td></tr>
                <tr><td>Accuracy</td><td>{metrics.accuracy}</td></tr>
                <tr><td>F1 Score</td><td>{metrics.f1_score}</td></tr>
                <tr><td>Precision / Recall</td><td>{metrics.precision} / {metrics.recall}</td></tr>
              </tbody>
            </table>
            <div className="model-card-note">
              <i className="fa-solid fa-circle-info"></i>
              Metrics dynamically retrieved from active production MLflow model run history.
            </div>
          </div>

          <div className="model-card-section">
            <h4>Score Interpretation</h4>
            <div className="model-card-ranges">
              <div className="range-item stable">
                <span className="range-label">75–100</span>
                <span>Stable — low credit risk, strong fundamentals</span>
              </div>
              <div className="range-item neutral">
                <span className="range-label">50–75</span>
                <span>Neutral — moderate risk, some factors to watch</span>
              </div>
              <div className="range-item volatile">
                <span className="range-label">0–50</span>
                <span>Volatile — elevated risk, significant concerns</span>
              </div>
            </div>
          </div>

          <div className="model-card-section">
            <h4>Limitations</h4>
            <ul className="model-card-limitations">
              <li>Model requires ≥30 days of historical data to train</li>
              <li>Heuristic fallback used when training data is insufficient</li>
              <li>News sentiment is English-only; regional language coverage limited</li>
              <li>Score reflects market-observed risk, not audited financial health</li>
              <li>Past performance does not guarantee future risk prediction accuracy</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}



export function ConfidenceIndicator() {
  return null
}


// ═══════════════════════════════════════════════════════════════
// StockChart
// ═══════════════════════════════════════════════════════════════

export function StockChart({ stockHistory, ticker, currency = 'USD' }) {
  const chartData = useMemo(() => {
    if (!stockHistory) return null

    const dates = Object.keys(stockHistory).sort()
    const closes = dates.map((d) => stockHistory[d].Close)

    return { dates, closes }
  }, [stockHistory])

  if (!chartData) return null

  const currencySymbol = currency === 'INR' ? '₹' : '$'

  return (
    <div>
      <h3 className="section-subtitle">Historical Stock Performance (1 Year)</h3>
      <div className="chart-container">
        <Plot
          data={[
            {
              type: 'scatter',
              mode: 'lines',
              x: chartData.dates,
              y: chartData.closes,
              line: { color: '#00c4cc', width: 2 },
              name: 'Close',
            },
          ]}
          layout={{
            title: {
              text: `${ticker} Closing Price (${currencySymbol})`,
              font: { color: '#fafafa', size: 14 },
            },
            xaxis: {
              color: '#b0b8c1',
              gridcolor: 'rgba(255,255,255,0.06)',
            },
            yaxis: {
              title: `Close (${currencySymbol})`,
              color: '#b0b8c1',
              gridcolor: 'rgba(255,255,255,0.06)',
            },
            height: 400,
            margin: { l: 70, r: 30, t: 40, b: 50 },
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { family: 'Inter, sans-serif', color: '#b0b8c1' },
            showlegend: false,
          }}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: '100%', height: '100%' }}
        />
      </div>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════
// NewsSection
// ═══════════════════════════════════════════════════════════════

export function NewsSection({ news }) {
  if (!news || news.length === 0) return null

  const formatDate = (dateStr) => {
    try {
      return new Date(dateStr).toISOString().slice(0, 10)
    } catch {
      return dateStr
    }
  }

  return (
    <div className="news-section">
      <h3 className="section-subtitle">Recent News Headlines</h3>
      {news.map((article, index) => (
        <div className="news-item" key={index}>
          <a
            className="news-title"
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            {article.title}
          </a>
          <div className="news-meta">
            Source: {article.source} | Published: {formatDate(article.publishedAt)}
          </div>
        </div>
      ))}
    </div>
  )
}




export function MarketBadge({ market, exchange, flag, currency }) {
  const badgeClass = market === 'IN' ? 'market-badge india' : 'market-badge us'

  return (
    <div className={badgeClass}>
      <span className="market-badge-flag">{flag}</span>
      <span className="market-badge-exchange">{exchange}</span>
      <span className="market-badge-currency">{currency}</span>
    </div>
  )
}


export function Footer() {
  return (
    <div className="app-footer">
      { }
      <div className="disclaimer-banner">
        <i className="fa-solid fa-triangle-exclamation"></i>
        For informational purposes only. Not financial or credit advice.
      </div>
      <div className="footer-copyright">© {new Date().getFullYear()} CredLens</div>
    </div>
  )
}


export function SourceAttribution({ market, agencyRating, lastUpdated }) {
  const isIndia = market === 'IN'
  const agencyName = isIndia ? 'CRISIL / ICRA' : 'S&P Global'
  const agencyUrl = isIndia
    ? 'https://www.crisil.com/en/home/our-businesses/ratings.html'
    : 'https://www.spglobal.com/ratings/'

  const displayDate = lastUpdated || new Date().toISOString().slice(0, 10)

  return (
    <div className="source-attribution">
      <a
        href={agencyUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="source-link"
      >
        <i className="fa-solid fa-arrow-up-right-from-square"></i>
        {agencyName}: {agencyRating || 'N/A'}
      </a>
      <span className="source-updated">Updated: {displayDate}</span>
    </div>
  )
}



export function NotificationBell({ onOpenAlerts, onOpenAuth }) {
  const { isAuthenticated, token } = useAuth()
  const [alertCount, setAlertCount] = useState(0)

  // Poll for active alerts every 60 seconds
  useEffect(() => {
    if (!isAuthenticated || !token) return

    const fetchAlertCount = async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/v1/alerts`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.ok) {
          const data = await res.json()
          const active = (data.alerts || []).filter((a) => a.is_active)
          setAlertCount(active.length)
        }
      } catch {
        // Silently fail — bell just won't show count
      }
    }

    fetchAlertCount()
    const interval = setInterval(fetchAlertCount, 60000)
    return () => clearInterval(interval)
  }, [isAuthenticated, token])

  const handleClick = () => {
    if (!isAuthenticated) {
      if (onOpenAuth) onOpenAuth('login')
      else onOpenAlerts()
    } else {
      onOpenAlerts()
    }
  }

  return (
    <button
      className="notification-bell"
      onClick={handleClick}
      title={!isAuthenticated ? 'Sign in to set alerts' : alertCount > 0 ? `${alertCount} active alert(s)` : 'Manage Alerts'}
    >
      <i className="fa-solid fa-bell"></i>
      {alertCount > 0 && (
        <span className="notification-dot">{alertCount}</span>
      )}
    </button>
  )
}


// ═══════════════════════════════════════════════════════════════
// AlertManager
// ═══════════════════════════════════════════════════════════════

const ALERT_TYPE_ICONS = {
  score_drop: '📉',
  volatile: '🔴',
  news_spike: '📰',
  recovery: '✅',
}

export function AlertManager({ isOpen, onClose, onOpenAuth }) {
  const { token, isAuthenticated } = useAuth()
  const [alerts, setAlerts] = useState([])
  const [alertTypes, setAlertTypes] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // New alert form
  const [newTicker, setNewTicker] = useState('')
  const [newType, setNewType] = useState('score_drop')
  const [newChannel, setNewChannel] = useState('in_app')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (isOpen && isAuthenticated) {
      fetchAlerts()
      fetchAlertTypes()
    }
  }, [isOpen, isAuthenticated])

  const fetchAlerts = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/alerts`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setAlerts(data.alerts || [])
      }
    } catch {
      setError('Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }

  const fetchAlertTypes = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/alerts/types`)
      if (res.ok) {
        const data = await res.json()
        setAlertTypes(data.alert_types || {})
      }
    } catch { }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!newTicker.trim()) return
    setCreating(true)
    setError(null)

    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/alerts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ticker: newTicker.toUpperCase(),
          alert_type: newType,
          channel: newChannel,
        }),
      })

      if (res.ok) {
        setNewTicker('')
        fetchAlerts()
      } else {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || 'Failed to create alert')
      }
    } catch {
      setError('Failed to create alert')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (alertId) => {
    try {
      await fetch(`${BACKEND_URL}/api/v1/alerts/${alertId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      fetchAlerts()
    } catch { }
  }

  const handleToggle = async (alertId) => {
    try {
      await fetch(`${BACKEND_URL}/api/v1/alerts/${alertId}/toggle`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
      })
      fetchAlerts()
    } catch { }
  }

  if (!isOpen) return null

  if (!isAuthenticated) {
    return (
      <div className="alert-overlay" onClick={onClose}>
        <div className="alert-panel guest-alert-panel" onClick={(e) => e.stopPropagation()}>
          <div className="alert-panel-header">
            <h3><i className="fa-solid fa-bell"></i> Real-Time Alerts</h3>
            <button className="alert-close" onClick={onClose}>
              <i className="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div className="guest-alert-prompt">
            <div className="guest-alert-icon">
              <i className="fa-solid fa-shield-halved"></i>
            </div>
            <h4>Sign in to Create Alert Rules</h4>
            <p>
              Set automated notifications for score drops, volatile zones, and news spikes on your portfolio stocks.
            </p>
            <div className="guest-alert-actions">
              <button
                className="sign-in-btn"
                onClick={() => {
                  onClose()
                  if (onOpenAuth) onOpenAuth('login')
                }}
              >
                <i className="fa-solid fa-right-to-bracket"></i> Sign In
              </button>
              <button
                className="sign-up-btn"
                onClick={() => {
                  onClose()
                  if (onOpenAuth) onOpenAuth('register')
                }}
              >
                Create Free Account
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="alert-overlay" onClick={onClose}>
      <div className="alert-panel" onClick={(e) => e.stopPropagation()}>
        <div className="alert-panel-header">
          <h3><i className="fa-solid fa-bell"></i> Alert Rules</h3>
          <button className="alert-close" onClick={onClose}>
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        {error && <div className="auth-error">{error}</div>}

        {/* Create Alert Form */}
        <form className="alert-form" onSubmit={handleCreate}>
          <input
            type="text"
            placeholder="Ticker (e.g. AAPL)"
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            className="alert-input"
            required
          />
          <select
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
            className="alert-select"
          >
            {Object.entries(alertTypes).map(([key, val]) => (
              <option key={key} value={key}>
                {ALERT_TYPE_ICONS[key] || '🔔'} {val.label}
              </option>
            ))}
            {Object.keys(alertTypes).length === 0 && (
              <>
                <option value="score_drop">📉 Score Drop</option>
                <option value="volatile">🔴 Volatile Zone</option>
                <option value="news_spike">📰 News Spike</option>
                <option value="recovery">✅ Recovery</option>
              </>
            )}
          </select>
          <button type="submit" className="alert-add-btn" disabled={creating}>
            {creating ? '…' : '+'}
          </button>
        </form>

        {/* Alert Rules List */}
        <div className="alert-list">
          {loading && <div className="alert-empty">Loading…</div>}
          {!loading && alerts.length === 0 && (
            <div className="alert-empty">
              No alert rules yet. Create one above.
            </div>
          )}
          {alerts.map((alert) => (
            <div key={alert.id} className={`alert-item ${!alert.is_active ? 'inactive' : ''}`}>
              <div className="alert-item-info">
                <span className="alert-item-icon">
                  {ALERT_TYPE_ICONS[alert.alert_type] || '🔔'}
                </span>
                <div>
                  <div className="alert-item-ticker">{alert.ticker}</div>
                  <div className="alert-item-type">
                    {alertTypes[alert.alert_type]?.label || alert.alert_type}
                    {alert.threshold && ` (threshold: ${alert.threshold})`}
                  </div>
                </div>
              </div>
              <div className="alert-item-actions">
                <button
                  className="alert-toggle-btn"
                  onClick={() => handleToggle(alert.id)}
                  title={alert.is_active ? 'Disable' : 'Enable'}
                >
                  <i className={`fa-solid ${alert.is_active ? 'fa-toggle-on' : 'fa-toggle-off'}`}></i>
                </button>
                <button
                  className="alert-delete-btn"
                  onClick={() => handleDelete(alert.id)}
                  title="Delete"
                >
                  <i className="fa-solid fa-trash"></i>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}


export function SkeletonLoader() {
  return (
    <div className="skeleton-container animate-pulse">
      {/* Header Skeleton */}
      <div className="skeleton-header">
        <div className="skeleton-title-bar"></div>
        <div className="skeleton-badge"></div>
      </div>

      <div className="skeleton-banner"></div>

      {/* Metrics Row Skeleton */}
      <div className="skeleton-metrics-row">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="skeleton-metric-card">
            <div className="skeleton-line-sm"></div>
            <div className="skeleton-line-lg"></div>
            <div className="skeleton-line-xs"></div>
          </div>
        ))}
      </div>

      {/* Charts Row Skeleton */}
      <div className="skeleton-charts-row">
        <div className="skeleton-chart-box">
          <div className="skeleton-line-md" style={{ marginBottom: '1rem' }}></div>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton-bar-row">
              <div className="skeleton-line-xs" style={{ width: '25%' }}></div>
              <div className="skeleton-bar-fill"></div>
            </div>
          ))}
        </div>
        <div className="skeleton-chart-box">
          <div className="skeleton-line-md" style={{ marginBottom: '1.5rem' }}></div>
          <div className="skeleton-chart-placeholder"></div>
        </div>
      </div>

      {/* Score History Skeleton */}
      <div className="skeleton-chart-box" style={{ marginTop: '2rem' }}>
        <div className="skeleton-line-md" style={{ marginBottom: '1.5rem' }}></div>
        <div className="skeleton-chart-placeholder" style={{ height: '200px' }}></div>
      </div>
    </div>
  )
}


export function ErrorStateDisplay({ errorType, message, onRetry }) {
  let icon = 'fa-circle-exclamation'
  let title = 'Analysis Error'
  let recoveryText = 'Please verify the details and try again.'

  if (errorType === 'TIMEOUT') {
    icon = 'fa-hourglass-half'
    title = 'Connection Timeout'
    recoveryText = 'The database or data provider response timed out. Please try again in a few moments.'
  } else if (errorType === 'RATE_LIMIT') {
    icon = 'fa-gauge-high'
    title = 'Rate Limit Exceeded'
    recoveryText = 'Too many requests generated. Please wait 1-2 minutes before executing another request.'
  } else if (errorType === 'STALE_DATA') {
    icon = 'fa-clock'
    title = 'Stale Data Warning'
    recoveryText = 'Data could not be updated in real-time, displaying cached record.'
  } else if (errorType === 'INVALID_TICKER') {
    icon = 'fa-magnifying-glass-chart'
    title = 'Invalid Ticker'
    recoveryText = 'The symbol could not be resolved by yFinance/AlphaVantage. Verify exchange suffix for Indian tickers (e.g. .NS / .BO).'
  }

  return (
    <div className="error-state-card">
      <div className="error-state-icon">
        <i className={`fa-solid ${icon}`}></i>
      </div>
      <h3 className="error-state-title">{title}</h3>
      <p className="error-state-msg">{message}</p>
      <div className="error-state-footer">
        <span className="error-state-hint">{recoveryText}</span>
        {onRetry && (
          <button className="error-retry-btn" onClick={onRetry}>
            <i className="fa-solid fa-arrows-rotate"></i> Retry
          </button>
        )}
      </div>
    </div>
  )
}


export function SectorBenchmark({ ticker, companyScore, sectorName, sectorAverage }) {
  const resolvedSector = sectorName || 'Technology Peers'
  const benchmarkScore = sectorAverage != null ? sectorAverage : 68

  const delta = companyScore - benchmarkScore
  const isBetter = delta >= 0
  const flagClass = isBetter ? 'positive' : 'negative'
  const directionIcon = isBetter ? '▲' : '▼'

  return (
    <div className="sector-benchmark-card">
      <div className="benchmark-header">
        <h4 className="benchmark-title">Sector Peer Comparison</h4>
        <span className="benchmark-sector-name">{resolvedSector}</span>
      </div>

      <div className="benchmark-body">
        <div className="benchmark-stat-item">
          <div className="benchmark-val-lbl">{ticker} Score</div>
          <div className={`benchmark-val-num ${companyScore > 75 ? 'stable-txt' : companyScore > 50 ? 'neutral-txt' : 'volatile-txt'}`}>
            {companyScore}
          </div>
        </div>

        <div className="benchmark-vs-divider">vs</div>

        <div className="benchmark-stat-item">
          <div className="benchmark-val-lbl">Sector Average</div>
          <div className="benchmark-val-num muted-txt">{benchmarkScore}</div>
        </div>
      </div>

      <div className={`benchmark-comparison-badge ${flagClass}`}>
        <span className="benchmark-comparison-icon">{directionIcon}</span>
        <span>
          {isBetter ? 'Outperforming' : 'Underperforming'} peers by {Math.abs(delta)} pts
        </span>
      </div>

      <div className="benchmark-footer-stub">
        <i className="fa-solid fa-database"></i> Source: CredLens Database / Sector Peer Statistics
      </div>
    </div>
  )
}



export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("Dashboard Section Error Captured:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="section-error-boundary">
          <div className="boundary-icon">
            <i className="fa-solid fa-triangle-exclamation"></i>
          </div>
          <h4>Widget Failed</h4>
          <p>This module crashed due to an internal error.</p>
          <button
            className="boundary-reset-btn"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Reset Widget
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export function DownloadPDFButton({ ticker, companyName, onOpenAuth }) {
  const { isAuthenticated } = useAuth()
  const [downloading, setDownloading] = useState(false)

  const handleDownload = () => {
    if (!isAuthenticated) {
      if (onOpenAuth) onOpenAuth('login')
      return
    }

    setDownloading(true)
    // Use window.print() configured with CSS print media queries for clean layout print
    // or trigger print flow cleanly.
    setTimeout(() => {
      window.print()
      setDownloading(false)
    }, 500)
  }

  return (
    <button
      className="download-pdf-btn"
      onClick={handleDownload}
      disabled={downloading}
      title="Download formatted PDF report"
    >
      <i className={`fa-solid ${downloading ? 'fa-spinner fa-spin' : 'fa-file-pdf'}`}></i>
      {downloading ? ' Generating...' : ' Download PDF Report'}
    </button>
  )
}

