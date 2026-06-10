import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

function apiUrl(path) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path
}

function formatValue(value) {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(2)
  }
  return String(value)
}

function App() {
  const [samples, setSamples] = useState([])
  const [sample, setSample] = useState('wrong_ensemble_ensemble_seed.mid')
  const [outputName, setOutputName] = useState('wrong_ensemble_response.mid')
  const [uploadFile, setUploadFile] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(apiUrl('/api/samples'))
      .then((response) => response.json())
      .then((data) => {
        setSamples(data.samples || [])
        if ((data.samples || []).length > 0 && !data.samples.includes(sample)) {
          setSample(data.samples[0])
        }
      })
      .catch(() => {
        setSamples([])
      })
  }, [])

  const titleFragments = useMemo(
    () => [
      { text: 'We Are All', tone: 'black' },
      { text: 'John Henry', tone: 'red' },
    ],
    []
  )

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('sample', sample)
      formData.append('output_name', outputName)
      if (uploadFile) {
        formData.append('midi_file', uploadFile)
      }

      const response = await fetch(apiUrl('/api/generate'), {
        method: 'POST',
        body: formData,
      })

      const responseText = await response.text()
      let data = null
      if (responseText) {
        try {
          data = JSON.parse(responseText)
        } catch {
          data = { detail: responseText }
        }
      }
      if (!response.ok) {
        throw new Error(data?.detail || responseText || 'Generation failed')
      }

      if (!data) {
        throw new Error('Empty response from server')
      }

      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <div className="eyebrow">We Are All John Henry</div>
        <h1 className="title" aria-label="We Are All John Henry">
          {titleFragments.map((fragment, index) => (
            <span key={fragment.text} className={`title__fragment tone-${fragment.tone}`}>
              {fragment.text}
              {index < titleFragments.length - 1 ? <br /> : null}
            </span>
          ))}
        </h1>
        <p className="lede">
          Upload a MIDI file or choose a sample, then generate a reactive response
          for the cello, trombone, drum set, percussion, and robot counterpart
          ensemble. The design keeps the typography quiet and the color system
          close to the score: white space, black text, and sharp red accents.
        </p>
      </section>

      <section className="layout">
        <form className="panel panel--form" onSubmit={handleSubmit}>
          <div className="panel__head">
            <span>Input</span>
            <span className="panel__hint">MIDI in, MIDI out</span>
          </div>

          <label className="field">
            <span>Upload MIDI</span>
            <input type="file" accept=".mid,.midi,audio/midi" onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)} />
          </label>

          <label className="field">
            <span>Choose sample</span>
            <select value={sample} onChange={(event) => setSample(event.target.value)}>
              {samples.length === 0 ? (
                <option value="wrong_ensemble_ensemble_seed.mid">wrong_ensemble_ensemble_seed.mid</option>
              ) : (
                samples.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))
              )}
            </select>
          </label>

          <label className="field">
            <span>Output file name</span>
            <input
              type="text"
              value={outputName}
              onChange={(event) => setOutputName(event.target.value)}
            />
          </label>

          <button className="button" type="submit" disabled={loading}>
            {loading ? 'Generating...' : 'Generate response'}
          </button>

          <div className="chips">
            <span className="chip">fastapi</span>
            <span className="chip">vite</span>
            <span className="chip">react</span>
          </div>
        </form>

        <section className="summary">
          {error ? <div className="error">{error}</div> : null}

          <div className="panel">
            <div className="panel__head">
              <span>Features</span>
              <span className="panel__hint">Detected from the first instrument</span>
            </div>
            <div className="grid">
              {result ? (
                Object.entries({
                  Notes: result.features.note_count,
                  'Avg pitch': result.features.avg_pitch,
                  'Pitch span': result.features.pitch_span,
                  Density: result.features.density,
                  Register: result.features.register,
                  Bars: result.features.bars,
                  'Notes / bar': result.features.notes_per_bar,
                  'Rhythmic variance': result.features.rhythmic_variance,
                }).map(([label, value]) => (
                  <article className="metric" key={label}>
                    <span>{label}</span>
                    <strong>{formatValue(value)}</strong>
                  </article>
                ))
              ) : (
                <div className="placeholder">Run the generator to inspect the extracted features.</div>
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel__head">
              <span>Action</span>
              <span className="panel__hint">Rule-based response plan</span>
            </div>
            <div className="grid">
              {result ? (
                Object.entries({
                  Mode: result.action.mode,
                  'Response density': result.action.response_density,
                  'Latency bars': result.action.latency_bars,
                  'Target notes': result.action.target_notes,
                  'Octave shift': result.action.octave_shift,
                }).map(([label, value]) => (
                  <article className="metric" key={label}>
                    <span>{label}</span>
                    <strong>{formatValue(value)}</strong>
                  </article>
                ))
              ) : (
                <div className="placeholder">Run the generator to inspect the chosen action.</div>
              )}
            </div>
          </div>

          {result ? (
            <div className="panel panel--download">
              <div className="panel__head">
                <span>Output</span>
                <span className="panel__hint">Generated MIDI is ready</span>
              </div>
              <div className="download-row">
                <a className="download" href={apiUrl(result.download_url)}>
                  Download MIDI
                </a>
                <span className="muted">{result.output_file}</span>
              </div>
            </div>
          ) : null}
        </section>
      </section>
    </main>
  )
}

createRoot(document.getElementById('root')).render(<App />)
