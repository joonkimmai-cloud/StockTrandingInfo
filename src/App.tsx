import { useState, useEffect } from 'react'
import './App.css'
import { fetchTopStocks, StockData } from './services/stockApi'
import { analyzeNews, NewsSummary } from './services/geminiService'

function App() {
  const [market, setMarket] = useState<'US' | 'KR'>('US')
  const [stocks, setStocks] = useState<StockData[]>([])
  const [summaries, setSummaries] = useState<NewsSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [emailStatus, setEmailStatus] = useState<string>('')

  const loadData = async () => {
    setLoading(true)
    const data = await fetchTopStocks(market)
    setStocks(data)
    setLoading(false)
  }

  const runAnalysis = async () => {
    setAnalyzing(true)
    const result = await analyzeNews(stocks)
    setSummaries(result)
    setAnalyzing(false)
  }

  const sendEmail = async () => {
    setEmailStatus('Sending...')
    try {
      const resp = await fetch(`/api/report?market=${market}`)
      const data = await resp.json()
      if (data.status === 'done') {
        setEmailStatus(`Sent! (${data.summaryCount} summaries)`)
      } else {
        setEmailStatus('Error: ' + data.error)
      }
    } catch (e: any) {
      setEmailStatus('Failed: ' + e.message)
    }
  }

  useEffect(() => {
    loadData()
  }, [market])

  const formatVolume = (vol: number) => {
    if (vol >= 1000000000) return (vol / 1000000000).toFixed(2) + 'B'
    if (vol >= 1000000) return (vol / 1000000).toFixed(2) + 'M'
    return vol.toLocaleString()
  }

  return (
    <div className="container">
      <header className="header">
        <h1>Daily <span className="highlight">Stock Reporter</span></h1>
        <p className="subtitle">AI-Driven Financial Market Analysis</p>
      </header>

      <nav className="tabs">
        <button 
          className={market === 'US' ? 'active' : ''} 
          onClick={() => setMarket('US')}
        >
          🇺🇸 US Market
        </button>
        <button 
          className={market === 'KR' ? 'active' : ''} 
          onClick={() => setMarket('KR')}
        >
          🇰🇷 Korea Market
        </button>
      </nav>

      <main className="main-content">
        <section className="summary-section">
          <div className="section-header">
            <h2>AI Today's Forecast</h2>
            <div className="controls">
              <button className="btn-ai" onClick={runAnalysis} disabled={analyzing || stocks.length === 0}>
                {analyzing ? 'Analyzing...' : '⚡ Generate AI Analysis'}
              </button>
            </div>
          </div>
          
          {summaries.length > 0 ? (
            <div className="summary-grid">
              {summaries.map((s, idx) => (
                <div key={idx} className={`summary-card ${s.sentiment}`}>
                  <div className="card-badge">{s.ticker}</div>
                  <h3>{s.title}</h3>
                  <p>{s.summary}</p>
                  <div className="card-footer">
                    <span className="impact">Impact: {s.impactScale}/10</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>Top 10 종목 정보를 불러온 후 AI 분석을 실행해 주세요.</p>
            </div>
          )}
        </section>

        <section className="stocks-section">
          <h2>Top 10 High-Volume Companies</h2>
          {loading ? (
            <div className="loader">Loading Market Data...</div>
          ) : (
            <div className="table-container">
              <table className="stock-table">
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Price</th>
                    <th>Change</th>
                    <th>Volume</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((stock) => (
                    <tr key={stock.symbol}>
                      <td>
                        <span className="stock-name">{stock.shortName}</span>
                        <span className="stock-symbol">{stock.symbol}</span>
                      </td>
                      <td>${stock.regularMarketPrice.toFixed(2)}</td>
                      <td className={stock.regularMarketChangePercent >= 0 ? 'positive' : 'negative'}>
                        {stock.regularMarketChangePercent.toFixed(2)}%
                      </td>
                      <td>{formatVolume(stock.regularMarketVolume)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        <p>This report is generated daily at 06:00 KST.</p>
        <button className="btn-secondary" onClick={sendEmail} disabled={emailStatus === 'Sending...'}>
          {emailStatus || '📧 Manual Email Dispatch'}
        </button>
      </footer>
    </div>
  )
}

export default App
