import { useEffect, useRef, useState } from 'react'

const SUGERENCIAS = [
  '¿Cómo pago el impuesto predial?',
  '¿Qué necesito para un certificado de residencia?',
  '¿Cómo radico un derecho de petición?',
]

const BIENVENIDA = {
  role: 'assistant',
  content:
    'Hola, soy Giro, el asistente virtual de la Alcaldía de Girardota. ¿En qué trámite o consulta le puedo ayudar hoy?',
}

function nuevaSesion() {
  return crypto.randomUUID()
}

export default function App() {
  const [sessionId, setSessionId] = useState(nuevaSesion)
  const [mensajes, setMensajes] = useState([BIENVENIDA])
  const [texto, setTexto] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const finRef = useRef(null)

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes, cargando])

  async function enviar(contenido) {
    const mensaje = contenido.trim()
    if (!mensaje || cargando) return

    setMensajes((prev) => [...prev, { role: 'user', content: mensaje }])
    setTexto('')
    setError(null)
    setCargando(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: mensaje }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setMensajes((prev) => [...prev, { role: 'assistant', content: data.reply }])
    } catch {
      setError('No se pudo contactar al asistente. Verifique que el Backend esté en ejecución.')
    } finally {
      setCargando(false)
    }
  }

  function reiniciar() {
    setSessionId(nuevaSesion())
    setMensajes([BIENVENIDA])
    setError(null)
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar(texto)
    }
  }

  return (
    <div className="app">
      <header className="cabecera">
        <div className="marca">
          <span className="logo" aria-hidden="true">G</span>
          <div>
            <h1>Alcaldía de Girardota</h1>
            <p>Asistente virtual de atención ciudadana</p>
          </div>
        </div>
        <button className="btn-secundario" onClick={reiniciar} disabled={cargando}>
          Nueva conversación
        </button>
      </header>

      <main className="chat" aria-live="polite">
        {mensajes.map((m, i) => (
          <div key={i} className={`burbuja ${m.role}`}>
            {m.content}
          </div>
        ))}

        {mensajes.length === 1 && (
          <div className="sugerencias">
            {SUGERENCIAS.map((s) => (
              <button key={s} onClick={() => enviar(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        {cargando && (
          <div className="burbuja assistant escribiendo" aria-label="El asistente está escribiendo">
            <span /><span /><span />
          </div>
        )}
        {error && <div className="error">{error}</div>}
        <div ref={finRef} />
      </main>

      <form
        className="entrada"
        onSubmit={(e) => {
          e.preventDefault()
          enviar(texto)
        }}
      >
        <textarea
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Escriba su consulta…"
          rows={1}
          maxLength={4000}
        />
        <button type="submit" disabled={cargando || !texto.trim()}>
          Enviar
        </button>
      </form>
    </div>
  )
}
