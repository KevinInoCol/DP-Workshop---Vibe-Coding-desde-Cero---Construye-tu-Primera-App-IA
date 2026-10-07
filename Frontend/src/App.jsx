import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const CLAVE_SESION = 'girardota.session_id'
const NOMBRE_BOT = 'Giro'

// Trámites reales del Manual de Trámites (códigos del manual), agrupados por dependencia.
const TRAMITES_FRECUENTES = [
  {
    grupo: 'Planeación y urbanismo',
    items: [
      { nombre: 'Certificado de residencia', pregunta: '¿Qué necesito para el certificado de residencia?' },
      { nombre: 'Licencia urbanística', pregunta: '¿Qué documentos necesito para una licencia urbanística de construcción?' },
      { nombre: 'Aprobación de piscinas', pregunta: '¿Qué documentos necesito para la aprobación de una piscina?' },
      { nombre: 'Concepto de uso del suelo', pregunta: '¿Cómo solicito un concepto de uso del suelo?' },
    ],
  },
  {
    grupo: 'Impuestos y pagos',
    items: [
      { nombre: 'Impuesto predial', pregunta: '¿Cómo funciona el pago del impuesto predial unificado?' },
      { nombre: 'Industria y comercio', pregunta: '¿Cómo me registro como contribuyente del impuesto de industria y comercio?' },
      { nombre: 'Paz y salvo', pregunta: '¿Qué necesito para obtener un certificado de paz y salvo?' },
    ],
  },
  {
    grupo: 'Tránsito y otros',
    items: [
      { nombre: 'Traspaso de vehículo', pregunta: '¿Qué requisitos tiene el traspaso de propiedad de un vehículo?' },
      { nombre: 'Marcas de ganado', pregunta: '¿Cómo registro una marca de ganado?' },
      { nombre: 'Espectáculos públicos', pregunta: '¿Qué permiso necesito para hacer un espectáculo público?' },
    ],
  },
]

const SUGERENCIAS = [
  '¿Qué necesito para el certificado de residencia?',
  '¿Cómo pago el impuesto predial?',
  'Quiero construir una piscina, ¿qué documentos piden?',
]

const MENSAJES_ESPERA = [
  'Consultando el Manual de Trámites…',
  'Revisando los requisitos…',
  'Preparando su respuesta…',
]

function leerSesion() {
  try {
    return localStorage.getItem(CLAVE_SESION)
  } catch {
    return null
  }
}

function guardarSesion(id) {
  try {
    localStorage.setItem(CLAVE_SESION, id)
  } catch {
    // Sin almacenamiento (modo privado): la conversación no se retomará al recargar.
  }
}

function nuevaSesion() {
  const id = crypto.randomUUID()
  guardarSesion(id)
  return id
}

function IconoEnviar() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path fill="currentColor" d="M3.4 20.4 20.85 12.9a1 1 0 0 0 0-1.8L3.4 3.6a.99.99 0 0 0-1.39 1.21L4.5 12l-2.49 7.19a.99.99 0 0 0 1.39 1.21Z" />
    </svg>
  )
}

function Mensaje({ role, content }) {
  if (role === 'user') {
    return <div className="mensaje usuario">{content}</div>
  }
  return (
    <div className="fila-asistente">
      <span className="avatar" aria-hidden="true">G</span>
      <div className="mensaje asistente">
        <Markdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: (props) => <a {...props} target="_blank" rel="noopener noreferrer" />,
          }}
        >
          {content}
        </Markdown>
      </div>
    </div>
  )
}

export default function App() {
  const [sessionId, setSessionId] = useState(() => leerSesion() || nuevaSesion())
  const [mensajes, setMensajes] = useState([])
  const [cargandoHistorial, setCargandoHistorial] = useState(true)
  const [texto, setTexto] = useState('')
  const [cargando, setCargando] = useState(false)
  const [espera, setEspera] = useState(0)
  const [error, setError] = useState(null)
  const finRef = useRef(null)
  const entradaRef = useRef(null)

  // Retoma la conversación guardada en el Backend (Postgres) al abrir o recargar.
  useEffect(() => {
    let cancelado = false
    fetch(`/api/historial/${encodeURIComponent(sessionId)}`)
      .then((res) => (res.ok ? res.json() : { messages: [] }))
      .then((data) => {
        if (!cancelado) setMensajes(data.messages || [])
      })
      .catch(() => {
        if (!cancelado) setMensajes([])
      })
      .finally(() => {
        if (!cancelado) setCargandoHistorial(false)
      })
    return () => {
      cancelado = true
    }
  }, [sessionId])

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [mensajes, cargando])

  // Rota el texto de espera mientras el agente trabaja.
  useEffect(() => {
    if (!cargando) return
    const intervalo = setInterval(() => setEspera((n) => (n + 1) % MENSAJES_ESPERA.length), 2500)
    return () => clearInterval(intervalo)
  }, [cargando])

  // La caja de texto crece con el contenido, hasta un máximo.
  useEffect(() => {
    const el = entradaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [texto])

  async function enviar(contenido) {
    const mensaje = contenido.trim()
    if (!mensaje || cargando) return

    setMensajes((prev) => [...prev, { role: 'user', content: mensaje }])
    setTexto('')
    setError(null)
    setEspera(0)
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
      setError('No se pudo contactar al asistente. Verifique que el Backend esté en ejecución e intente de nuevo.')
    } finally {
      setCargando(false)
      entradaRef.current?.focus()
    }
  }

  function reiniciar() {
    setSessionId(nuevaSesion())
    setCargandoHistorial(true)
    setMensajes([])
    setError(null)
    entradaRef.current?.focus()
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar(texto)
    }
  }

  const vacio = !cargandoHistorial && mensajes.length === 0

  return (
    <div className="pagina">
      <div className="franja-superior">
        <div className="contenedor">Asistente virtual de trámites · Versión de demostración</div>
      </div>

      <header className="cabecera">
        <div className="contenedor cabecera-interior">
          <div className="marca">
            <span className="emblema" aria-hidden="true">G</span>
            <div>
              <h1>Alcaldía Municipal de Girardota</h1>
              <p>Asistente virtual de atención ciudadana</p>
            </div>
          </div>
          <button className="btn-contorno" onClick={reiniciar} disabled={cargando}>
            Nueva conversación
          </button>
        </div>
      </header>

      <section className="banda">
        <div className="contenedor">
          <p>
            Pregúntele a <strong>{NOMBRE_BOT}</strong> por los requisitos, documentos y pasos de los
            trámites del municipio.
          </p>
        </div>
      </section>

      <main className="contenedor cuerpo">
        <aside className="lateral" aria-label="Trámites frecuentes">
          <h2>Trámites frecuentes</h2>
          {TRAMITES_FRECUENTES.map(({ grupo, items }) => (
            <div key={grupo} className="grupo">
              <h3>{grupo}</h3>
              <ul>
                {items.map((t) => (
                  <li key={t.nombre}>
                    <button onClick={() => enviar(t.pregunta)} disabled={cargando}>
                      {t.nombre}
                      <span aria-hidden="true">›</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div className="aviso-emergencia">
            <strong>¿Una emergencia?</strong>
            <span>Comuníquese de inmediato con la línea</span>
            <a href="tel:123" className="linea-123">123</a>
          </div>
        </aside>

        <section className="chat" aria-label={`Conversación con ${NOMBRE_BOT}`}>
          <div className="mensajes" aria-live="polite">
            {cargandoHistorial && <p className="estado">Cargando conversación…</p>}

            {vacio && (
              <div className="bienvenida">
                <span className="avatar grande" aria-hidden="true">G</span>
                <h2>Hola, soy {NOMBRE_BOT}</h2>
                <p>
                  Le ayudo a encontrar qué trámite necesita, qué documentos debe llevar y ante qué
                  dependencia de la Alcaldía se realiza.
                </p>
                <div className="sugerencias">
                  {SUGERENCIAS.map((s) => (
                    <button key={s} onClick={() => enviar(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {mensajes.map((m, i) => (
              <Mensaje key={i} role={m.role} content={m.content} />
            ))}

            {cargando && (
              <div className="fila-asistente">
                <span className="avatar" aria-hidden="true">G</span>
                <div className="mensaje asistente escribiendo">
                  <span className="puntos" aria-hidden="true"><i /><i /><i /></span>
                  {MENSAJES_ESPERA[espera]}
                </div>
              </div>
            )}

            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <div ref={finRef} />
          </div>

          <form
            className="entrada"
            onSubmit={(e) => {
              e.preventDefault()
              enviar(texto)
            }}
          >
            <label htmlFor="consulta" className="solo-lectores">
              Escriba su consulta
            </label>
            <textarea
              id="consulta"
              ref={entradaRef}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Escriba su consulta sobre un trámite…"
              rows={1}
              maxLength={4000}
            />
            <button type="submit" className="btn-enviar" disabled={cargando || !texto.trim()} aria-label="Enviar">
              <IconoEnviar />
            </button>
          </form>
        </section>
      </main>

      <footer className="pie">
        <div className="contenedor">
          Las respuestas se basan en el Manual de Trámites del municipio y en fuentes de internet, y
          pueden no estar actualizadas. Confirme siempre requisitos y costos con la Alcaldía de
          Girardota. Este asistente no es un canal oficial de radicación.
        </div>
      </footer>
    </div>
  )
}
