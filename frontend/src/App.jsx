import React, { useState, useEffect, useRef } from 'react'
import {
  Sparkles,
  Upload,
  ArrowRightLeft,
  Trash2,
  Cpu,
  Layers,
  Activity,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Download,
  Eye,
  Crosshair,
  Maximize2,
  RefreshCw,
  Image as ImageIcon,
  Zap,
  BarChart3
} from 'lucide-react'

// Sub-component: Curtain Wipe Comparison Slider
function CurtainSlider({ origSrc, genSrc }) {
  const [sliderPos, setSliderPos] = useState(50)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef(null)

  const handleMove = (clientX) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width))
    const percent = (x / rect.width) * 100
    setSliderPos(percent)
  }

  const handleTouchMove = (e) => {
    if (e.touches && e.touches[0]) {
      handleMove(e.touches[0].clientX)
    }
  }

  const handleMouseDown = () => setIsDragging(true)
  const handleMouseUp = () => setIsDragging(false)

  useEffect(() => {
    const onMouseMove = (e) => {
      if (isDragging) handleMove(e.clientX)
    }
    const onMouseUp = () => setIsDragging(false)

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [isDragging])

  return (
    <div
      ref={containerRef}
      className="slider-container"
      onMouseDown={handleMouseDown}
      onTouchMove={handleTouchMove}
    >
      {/* Generated image is the base */}
      <img src={genSrc} alt="Generated" className="slider-img" />
      <span className="slider-tag right">Generated</span>

      {/* Original image is clipped to sliderPos % */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: `${sliderPos}%`,
          height: '100%',
          overflow: 'hidden',
          pointerEvents: 'none'
        }}
      >
        <img
          src={origSrc}
          alt="Original"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: containerRef.current ? `${containerRef.current.clientWidth}px` : '100%',
            height: '100%',
            objectFit: 'contain'
          }}
        />
      </div>
      <span className="slider-tag left">Original</span>

      {/* Draggable Divider Line & Handle */}
      <div className="slider-divider" style={{ left: `${sliderPos}%` }}>
        <div className="slider-handle">
          <ArrowRightLeft size={16} />
        </div>
      </div>
    </div>
  )
}

// Sub-component: Radial Matching Gauge
function GaugeMeter({ percentage, color }) {
  const radius = 68
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (percentage / 100) * circumference

  return (
    <div className="gauge-container">
      <svg className="gauge-svg" viewBox="0 0 170 170">
        <circle
          className="gauge-track"
          cx="85"
          cy="85"
          r={radius}
        />
        <circle
          className="gauge-fill"
          cx="85"
          cy="85"
          r={radius}
          stroke={color || '#06b6d4'}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
        />
      </svg>
      <div className="gauge-center-content">
        <span className="gauge-number" style={{ color: color || '#f8fafc' }}>
          {percentage}%
        </span>
        <span className="gauge-label">Match Score</span>
      </div>
    </div>
  )
}

export default function App() {
  const [origFile, setOrigFile] = useState(null)
  const [genFile, setGenFile] = useState(null)
  const [origPreview, setOrigPreview] = useState(null)
  const [genPreview, setGenPreview] = useState(null)

  const [origInfo, setOrigInfo] = useState(null)
  const [genInfo, setGenInfo] = useState(null)

  const [samples, setSamples] = useState([])
  const [activeMode, setActiveMode] = useState('balanced')
  const [activeTab, setActiveTab] = useState('slider')

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const [systemInfo, setSystemInfo] = useState({ gpu_available: false, device: 'CPU' })

  const origInputRef = useRef(null)
  const genInputRef = useRef(null)

  // Fetch samples and health on mount
  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setSystemInfo(data))
      .catch(() => {})

    fetch('/api/samples')
      .then(res => res.json())
      .then(data => {
        if (data.samples) setSamples(data.samples)
      })
      .catch(() => {})
  }, [])

  // Helper to extract image dimensions
  const readImageInfo = (file, callback) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      callback({
        width: img.naturalWidth,
        height: img.naturalHeight,
        aspectRatio: (img.naturalWidth / Math.max(1, img.naturalHeight)).toFixed(2),
        sizeKb: (file.size / 1024).toFixed(1),
        type: file.type || 'image/jpeg'
      })
      URL.revokeObjectURL(url)
    }
    img.src = url
  }

  const handleOrigSelect = (file) => {
    if (!file) return
    setOrigFile(file)
    setOrigPreview(URL.createObjectURL(file))
    readImageInfo(file, info => setOrigInfo(info))
    setResult(null)
  }

  const handleGenSelect = (file) => {
    if (!file) return
    setGenFile(file)
    setGenPreview(URL.createObjectURL(file))
    readImageInfo(file, info => setGenInfo(info))
    setResult(null)
  }

  // Load sample pair
  const loadSample = async (sample) => {
    try {
      setLoading(true)
      setErrorMsg(null)

      // Convert base64 data URIs to Files
      const dataUriToFile = async (dataUri, filename) => {
        const res = await fetch(dataUri)
        const blob = await res.blob()
        return new File([blob], filename, { type: blob.type })
      }

      const f1 = await dataUriToFile(sample.original_data_uri, `${sample.id}_orig.jpg`)
      const f2 = await dataUriToFile(sample.generated_data_uri, `${sample.id}_gen.jpg`)

      handleOrigSelect(f1)
      handleGenSelect(f2)
      setLoading(false)
    } catch (err) {
      setLoading(false)
      setErrorMsg('Failed to load sample pair: ' + err.message)
    }
  }

  // Swap images
  const handleSwap = () => {
    const tempFile = origFile
    const tempPrev = origPreview
    const tempInfo = origInfo

    setOrigFile(genFile)
    setOrigPreview(genPreview)
    setOrigInfo(genInfo)

    setGenFile(tempFile)
    setGenPreview(tempPrev)
    setGenInfo(tempInfo)

    setResult(null)
  }

  // Reset all
  const handleReset = () => {
    setOrigFile(null)
    setGenFile(null)
    setOrigPreview(null)
    setGenPreview(null)
    setOrigInfo(null)
    setGenInfo(null)
    setResult(null)
    setErrorMsg(null)
  }

  // Execute comparison
  const runComparison = async () => {
    if (!origFile || !genFile) {
      setErrorMsg('Please upload both the original image and the generated image.')
      return
    }

    setLoading(true)
    setErrorMsg(null)

    try {
      const formData = new FormData()
      formData.append('original_image', origFile)
      formData.append('generated_image', genFile)
      formData.append('mode', activeMode)

      const response = await fetch('/api/compare', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || `Server returned ${response.status}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setErrorMsg(err.message || 'Error occurred while comparing images.')
    } finally {
      setLoading(false)
    }
  }

  // Export report
  const downloadReport = () => {
    if (!result) return
    const exportData = {
      timestamp: new Date().toISOString(),
      overall_matching_percentage: result.matching_percentage,
      grade: result.grade,
      verdict: result.verdict,
      mode: result.mode,
      metadata: result.metadata,
      breakdown: result.breakdown
    }
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `image-match-report-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo-icon">
            <Sparkles size={24} />
          </div>
          <div>
            <h1 className="brand-title">MatchVision AI</h1>
            <p className="brand-subtitle">Generation Fidelity & Image Matching Engine</p>
          </div>
        </div>

        <div className="header-status-badge">
          <div className="pulse-dot"></div>
          <span>
            {systemInfo.gpu_available ? `GPU Accelerated (${systemInfo.device})` : 'Neural Vision Ready'}
          </span>
        </div>
      </header>

      {/* Hero Banner */}
      <section className="hero-banner">
        <div className="hero-pill">
          <Zap size={14} />
          Multi-Metric AI Computer Vision Engine
        </div>
        <h2 className="hero-title">
          Identify the exact <span className="gradient-text">Matching Percentage</span>
        </h2>
        <p className="hero-desc">
          Compare your original reference image against an AI-generated or edited image.
          Calculates perceptual structural coherence (SSIM), keypoint correspondence (ORB), color harmony, and deep neural features.
        </p>
      </section>

      {/* Sample Quick-Load Bar */}
      {samples.length > 0 && (
        <div className="sample-bar">
          <span className="sample-bar-label">Try instant demo samples:</span>
          {samples.map((sample) => (
            <button
              key={sample.id}
              className="sample-chip"
              onClick={() => loadSample(sample)}
              disabled={loading}
            >
              <ImageIcon size={14} />
              {sample.title}
            </button>
          ))}
        </div>
      )}

      {/* Mode Selector */}
      <div className="mode-selector-wrap">
        <div className="mode-selector">
          <button
            className={`mode-btn ${activeMode === 'balanced' ? 'active' : ''}`}
            onClick={() => setActiveMode('balanced')}
          >
            <Activity size={15} />
            Balanced Ensemble
          </button>
          <button
            className={`mode-btn ${activeMode === 'strict_pixel' ? 'active' : ''}`}
            onClick={() => setActiveMode('strict_pixel')}
          >
            <Crosshair size={15} />
            Strict Pixel & Structure
          </button>
          <button
            className={`mode-btn ${activeMode === 'semantic_creative' ? 'active' : ''}`}
            onClick={() => setActiveMode('semantic_creative')}
          >
            <Sparkles size={15} />
            Semantic & Creative
          </button>
        </div>
      </div>

      {/* Upload Cards Grid */}
      <section className="upload-grid">
        {/* Card 1: Original Image */}
        <div className="upload-card">
          <div className="card-header-row">
            <span className="card-badge original">Original Reference</span>
            {origPreview && (
              <button
                className="overlay-btn"
                title="Remove image"
                onClick={() => {
                  setOrigFile(null)
                  setOrigPreview(null)
                  setOrigInfo(null)
                  setResult(null)
                }}
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>

          {!origPreview ? (
            <div
              className="dropzone"
              onClick={() => origInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleOrigSelect(e.dataTransfer.files[0])
                }
              }}
            >
              <div className="dropzone-icon-circle">
                <Upload size={26} />
              </div>
              <p className="dropzone-primary-text">Upload Original Image</p>
              <p className="dropzone-secondary-text">Click or drag & drop PNG, JPG, or WEBP</p>
            </div>
          ) : (
            <div className="preview-wrapper">
              <img src={origPreview} alt="Original Preview" className="preview-img" />
              <div className="preview-overlay-actions">
                <button
                  className="overlay-btn"
                  title="Change image"
                  onClick={() => origInputRef.current?.click()}
                >
                  <RefreshCw size={15} />
                </button>
              </div>
            </div>
          )}

          <input
            ref={origInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleOrigSelect(e.target.files[0])
              }
            }}
          />

          {origInfo && (
            <div className="meta-tags-row">
              <span className="meta-tag">{origInfo.width} × {origInfo.height} px</span>
              <span className="meta-tag">Ratio {origInfo.aspectRatio}</span>
              <span className="meta-tag">{origInfo.sizeKb} KB</span>
            </div>
          )}
        </div>

        {/* Card 2: Generated Image */}
        <div className="upload-card">
          <div className="card-header-row">
            <span className="card-badge generated">Generated Image</span>
            {genPreview && (
              <button
                className="overlay-btn"
                title="Remove image"
                onClick={() => {
                  setGenFile(null)
                  setGenPreview(null)
                  setGenInfo(null)
                  setResult(null)
                }}
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>

          {!genPreview ? (
            <div
              className="dropzone"
              onClick={() => genInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleGenSelect(e.dataTransfer.files[0])
                }
              }}
            >
              <div className="dropzone-icon-circle">
                <Sparkles size={26} />
              </div>
              <p className="dropzone-primary-text">Upload Generated Image</p>
              <p className="dropzone-secondary-text">Click or drag & drop AI output or edit</p>
            </div>
          ) : (
            <div className="preview-wrapper">
              <img src={genPreview} alt="Generated Preview" className="preview-img" />
              <div className="preview-overlay-actions">
                <button
                  className="overlay-btn"
                  title="Change image"
                  onClick={() => genInputRef.current?.click()}
                >
                  <RefreshCw size={15} />
                </button>
              </div>
            </div>
          )}

          <input
            ref={genInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleGenSelect(e.target.files[0])
              }
            }}
          />

          {genInfo && (
            <div className="meta-tags-row">
              <span className="meta-tag">{genInfo.width} × {genInfo.height} px</span>
              <span className="meta-tag">Ratio {genInfo.aspectRatio}</span>
              <span className="meta-tag">{genInfo.sizeKb} KB</span>
            </div>
          )}
        </div>
      </section>

      {/* Action Controls */}
      <div className="action-bar">
        {origPreview && genPreview && (
          <button className="btn-secondary" onClick={handleSwap} disabled={loading}>
            <ArrowRightLeft size={16} />
            Swap Images
          </button>
        )}

        <button
          className="btn-primary"
          onClick={runComparison}
          disabled={!origPreview || !genPreview || loading}
        >
          {loading ? (
            <>
              <div className="spinner"></div>
              Computing Multi-Metric Fidelity...
            </>
          ) : (
            <>
              <Sparkles size={18} />
              Calculate Matching Percentage
            </>
          )}
        </button>

        {(origPreview || genPreview || result) && (
          <button className="btn-secondary" onClick={handleReset} disabled={loading}>
            <Trash2 size={16} />
            Clear
          </button>
        )}
      </div>

      {/* Error Banner */}
      {errorMsg && (
        <div style={{
          padding: '1rem 1.5rem',
          borderRadius: '1rem',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#f87171',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          maxWidth: '800px',
          margin: '0 auto'
        }}>
          <AlertTriangle size={20} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Results Section */}
      {result && (
        <section className="results-dashboard">
          {/* Hero Score Card */}
          <div className="score-hero-card">
            <GaugeMeter
              percentage={result.matching_percentage}
              color={result.status_color}
            />

            <div className="score-details-col">
              <div className="grade-badge-wrap">
                <span
                  className="grade-pill"
                  style={{
                    backgroundColor: `${result.status_color}22`,
                    color: result.status_color,
                    border: `1px solid ${result.status_color}55`
                  }}
                >
                  {result.grade}
                </span>
                <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                  Mode: <strong style={{ color: '#fff', textTransform: 'capitalize' }}>{result.mode}</strong>
                </span>
              </div>
              <p className="verdict-text">{result.verdict}</p>
            </div>

            <div className="stats-summary-col">
              <div className="stat-box">
                <span className="stat-box-title">Execution Time</span>
                <span className="stat-box-value">{result.execution_time_seconds}s</span>
              </div>
              <div className="stat-box">
                <span className="stat-box-title">Overall Score</span>
                <span className="stat-box-value" style={{ color: result.status_color }}>
                  {result.matching_percentage}%
                </span>
              </div>
              <button
                className="btn-secondary"
                style={{ padding: '0.5rem 0.9rem', fontSize: '0.82rem', marginTop: '0.25rem' }}
                onClick={downloadReport}
              >
                <Download size={14} />
                Export JSON
              </button>
            </div>
          </div>

          {/* Interactive Visual Suite */}
          <div className="visual-suite-card">
            <div className="tabs-row">
              <button
                className={`tab-btn ${activeTab === 'slider' ? 'active' : ''}`}
                onClick={() => setActiveTab('slider')}
              >
                <ArrowRightLeft size={16} />
                Interactive Curtain Wipe
              </button>
              <button
                className={`tab-btn ${activeTab === 'heatmap' ? 'active' : ''}`}
                onClick={() => setActiveTab('heatmap')}
              >
                <Layers size={16} />
                Difference Heatmap
              </button>
              <button
                className={`tab-btn ${activeTab === 'keypoints' ? 'active' : ''}`}
                onClick={() => setActiveTab('keypoints')}
              >
                <Crosshair size={16} />
                Keypoint Matches (ORB)
              </button>
              <button
                className={`tab-btn ${activeTab === 'side' ? 'active' : ''}`}
                onClick={() => setActiveTab('side')}
              >
                <Eye size={16} />
                Side by Side
              </button>
            </div>

            <div className="viewer-canvas-box">
              {activeTab === 'slider' && (
                <CurtainSlider origSrc={origPreview} genSrc={genPreview} />
              )}

              {activeTab === 'heatmap' && (
                <div style={{ position: 'relative', width: '100%', height: '520px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img
                    src={result.visualizations.heatmap}
                    alt="Difference Heatmap"
                    style={{ maxWidth: '100%', maxHeight: '520px', objectFit: 'contain' }}
                  />
                  <span className="slider-tag left" style={{ background: 'rgba(0,0,0,0.85)' }}>
                    High Divergence (Warm Red) vs Coherent (Dark Blue)
                  </span>
                </div>
              )}

              {activeTab === 'keypoints' && (
                <div style={{ position: 'relative', width: '100%', height: '520px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img
                    src={result.visualizations.keypoints}
                    alt="Keypoint Correspondence"
                    style={{ maxWidth: '100%', maxHeight: '520px', objectFit: 'contain' }}
                  />
                  <span className="slider-tag left" style={{ background: 'rgba(0,0,0,0.85)' }}>
                    ORB Landmark Correspondences & RANSAC Inliers
                  </span>
                </div>
              )}

              {activeTab === 'side' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', width: '100%', height: '520px', gap: '1rem', padding: '1rem' }}>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#070a12', borderRadius: '1rem', overflow: 'hidden' }}>
                    <img src={origPreview} alt="Original" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                    <span className="slider-tag left">Original</span>
                  </div>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#070a12', borderRadius: '1rem', overflow: 'hidden' }}>
                    <img src={genPreview} alt="Generated" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                    <span className="slider-tag right">Generated</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Metric Breakdown Cards */}
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart3 size={20} color="#06b6d4" />
              Detailed Multi-Metric Breakdown
            </h3>
            <div className="breakdown-grid">
              {result.breakdown.map((metric) => {
                const getMetricColor = (val) => {
                  if (val >= 80) return '#10b981'
                  if (val >= 60) return '#38bdf8'
                  if (val >= 40) return '#f59e0b'
                  return '#f43f5e'
                }
                const mColor = getMetricColor(metric.score)
                return (
                  <div key={metric.key} className="metric-card">
                    <div className="metric-header">
                      <span className="metric-title">{metric.name}</span>
                      <span className="metric-score-text" style={{ color: mColor }}>
                        {metric.score}%
                      </span>
                    </div>

                    <div className="progress-track">
                      <div
                        className="progress-bar"
                        style={{
                          width: `${metric.score}%`,
                          background: `linear-gradient(90deg, ${mColor}aa, ${mColor})`
                        }}
                      ></div>
                    </div>

                    <p className="metric-desc">{metric.description}</p>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Technical Specs Comparison Table */}
          <div className="specs-table-card">
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem' }}>
              Image Technical Specifications
            </h3>
            <table className="specs-table">
              <thead>
                <tr>
                  <th>Property</th>
                  <th>Original Reference</th>
                  <th>Generated Image</th>
                  <th>Delta / Alignment</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Resolution</td>
                  <td className="val-primary">{result.metadata.original.width} × {result.metadata.original.height} px</td>
                  <td className="val-primary">{result.metadata.generated.width} × {result.metadata.generated.height} px</td>
                  <td>
                    {result.metadata.original.width === result.metadata.generated.width &&
                    result.metadata.original.height === result.metadata.generated.height ? (
                      <span style={{ color: '#10b981' }}>Exact Match</span>
                    ) : (
                      <span style={{ color: '#f59e0b' }}>Resolution Rescaled</span>
                    )}
                  </td>
                </tr>
                <tr>
                  <td>Aspect Ratio</td>
                  <td className="val-primary">{result.metadata.original.aspect_ratio}</td>
                  <td className="val-primary">{result.metadata.generated.aspect_ratio}</td>
                  <td>
                    {Math.abs(result.metadata.original.aspect_ratio - result.metadata.generated.aspect_ratio) < 0.05 ? (
                      <span style={{ color: '#10b981' }}>Harmonious Aspect</span>
                    ) : (
                      <span style={{ color: '#f59e0b' }}>Shifted Aspect Ratio</span>
                    )}
                  </td>
                </tr>
                <tr>
                  <td>File Size</td>
                  <td className="val-primary">{result.metadata.original.size_kb} KB</td>
                  <td className="val-primary">{result.metadata.generated.size_kb} KB</td>
                  <td>
                    Δ {Math.abs(result.metadata.original.size_kb - result.metadata.generated.size_kb).toFixed(1)} KB
                  </td>
                </tr>
                <tr>
                  <td>Color Model</td>
                  <td className="val-primary">{result.metadata.original.mode}</td>
                  <td className="val-primary">{result.metadata.generated.mode}</td>
                  <td><span style={{ color: '#10b981' }}>sRGB Standard</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="app-footer">
        MatchVision AI • Enterprise Image Fidelity & Generation Comparison System • Production-Ready
      </footer>
    </div>
  )
}
