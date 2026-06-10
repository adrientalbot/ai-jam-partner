import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const DEFAULT_SAMPLE_FILE = 'wrong_ensemble_ensemble_seed.mid'
const DEFAULT_SAMPLES = [
  {
    file: 'wrong_ensemble_ensemble_seed.mid',
    name: 'Wrong Ensemble Seed',
    description: 'A compact ensemble opening with a deliberately mismatched texture.',
  },
  {
    file: 'wrong_ensemble_takeover_seed.mid',
    name: 'Wrong Ensemble Takeover',
    description: 'A more aggressive cue built around a takeover-style gesture.',
  },
  {
    file: 'mvp_minimalist_input.mid',
    name: 'Minimalist MVP',
    description: 'Sparse material with lots of space and clear rhythmic cells.',
  },
  {
    file: 'mvp_minimalist_input_variant.mid',
    name: 'Minimalist Variant',
    description: 'Alternate cut of the minimalist MVP with denser phrasing.',
  },
  {
    file: 'in_c_inspired_input.mid',
    name: 'In C Inspired',
    description: 'Repetitive modular patterns with a steady forward pulse.',
  },
  {
    file: 'in_c_inspired_input_variant.mid',
    name: 'In C Variant',
    description: 'A variation with slightly different harmonic movement and pacing.',
  },
  {
    file: 'max_piano.mid',
    name: 'Max Piano',
    description: 'Piano-forward material with broader gestures and register jumps.',
  },
  {
    file: 'mvp_test_input.mid',
    name: 'MVP Test Input',
    description: 'Short test fixture for verifying the generation pipeline.',
  },
  {
    file: 'example_01.mid',
    name: 'Example 01',
    description: 'General-purpose example clip for quick experimentation.',
  },
]

function apiUrl(path) {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path
}

function formatValue(value) {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toFixed(2)
  }
  return String(value)
}

function normalizeSample(sample) {
  if (typeof sample === 'string') {
    const base = sample.replace(/\.mid$/i, '')
    const pretty = base
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase())

    return {
      file: sample,
      name: pretty,
      description: 'Sample input MIDI file.',
    }
  }

  return sample
}

function App() {
  const [samples, setSamples] = useState(DEFAULT_SAMPLES)
  const [sample, setSample] = useState(DEFAULT_SAMPLE_FILE)
  const [outputName, setOutputName] = useState('wrong_ensemble_response.mid')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadDownloadUrl, setUploadDownloadUrl] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(apiUrl('/api/samples'))
      .then((response) => response.json())
      .then((data) => {
        const nextSamples = (data.samples || []).map(normalizeSample)
        if (nextSamples.length > 0) {
          setSamples(nextSamples)
          setSample((currentSample) =>
            nextSamples.some((item) => item.file === currentSample) ? currentSample : nextSamples[0].file
          )
        }
      })
      .catch(() => {
        setSamples(DEFAULT_SAMPLES)
      })
  }, [])

  useEffect(() => {
    if (!uploadFile) {
      setUploadDownloadUrl('')
      return undefined
    }

    const objectUrl = URL.createObjectURL(uploadFile)
    setUploadDownloadUrl(objectUrl)

    return () => URL.revokeObjectURL(objectUrl)
  }, [uploadFile])

  const titleFragments = useMemo(
    () => [
      { text: 'We Are All', tone: 'black' },
      { text: 'John Henry', tone: 'red' },
    ],
    []
  )

  const selectedSample = useMemo(
    () => samples.find((item) => item.file === sample) ?? samples[0] ?? null,
    [sample, samples]
  )

  const inputDownloadUrl = uploadDownloadUrl || (selectedSample ? apiUrl(`/inputs/${selectedSample.file}`) : '')
  const inputDownloadName = uploadFile?.name || selectedSample?.file || 'input.mid'

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
        {result ? (
          <div className="hero-actions" aria-label="Download generated and input MIDI">
            <div className="hero-actions__meta">
              <span className="hero-actions__label">Main result</span>
              <span className="hero-actions__value">{result.output_file}</span>
            </div>
            <div className="hero-actions__buttons">
              <a className="download download--primary" href={apiUrl(result.download_url)}>
                Download response
              </a>
              {inputDownloadUrl ? (
                <a className="download download--secondary" href={inputDownloadUrl} download={inputDownloadName}>
                  Download input
                </a>
              ) : null}
            </div>
          </div>
        ) : null}
      </section>

      <section className="layout">
        <form className="panel panel--form" onSubmit={handleSubmit}>
          <div className="panel__head">
            <span>Input</span>
            <span className="panel__hint">MIDI in, MIDI out</span>
          </div>

          <label className="field">
            <span>Upload MIDI</span>
            <input
              type="file"
              accept=".mid,.midi,audio/midi"
              onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
            />
          </label>

          <div className="field">
            <span>Choose sample</span>
            <div className="sample-grid" role="radiogroup" aria-label="Input sample library">
              {samples.map((item) => (
                <label key={item.file} className={`sample-card${sample === item.file ? ' sample-card--selected' : ''}`}>
                  <input
                    type="radio"
                    name="sample"
                    value={item.file}
                    checked={sample === item.file}
                    onChange={(event) => setSample(event.target.value)}
                  />
                  <div className="sample-card__body">
                    <strong>{item.name}</strong>
                    <span>{item.description}</span>
                    <small>{item.file}</small>
                  </div>
                </label>
              ))}
            </div>
          </div>

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
            <div className="panel">
              <div className="panel__head">
                <span>Output</span>
                <span className="panel__hint">Generated MIDI is ready</span>
              </div>
              <div className="output-meta">
                <div>
                  <span className="output-meta__label">Generated file</span>
                  <strong>{result.output_file}</strong>
                </div>
                <div>
                  <span className="output-meta__label">Input source</span>
                  <strong>{result.input_file}</strong>
                </div>
                <div>
                  <span className="output-meta__label">Duration</span>
                  <strong>{formatValue(result.duration_seconds)} sec</strong>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      </section>
    </main>
  )
}

createRoot(document.getElementById('root')).render(<App />)
