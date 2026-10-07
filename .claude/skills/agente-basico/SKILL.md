---
name: agente-basico
description: Patrón de un agente básico de punta a punta — agente LangChain v1 (create_agent) con prompt en YAML por tags, configuración del modelo en YAML, carpeta tools/ con function calling, memoria por sesión con checkpointer, API FastAPI y un chat en React + Vite que la consume. Use when creating a new basic agent from scratch, adding a tool to it, exposing it through an API, building a chat frontend for it, or when the user says "crea un agente", "agente básico", "agrega una tool", "conecta el agente al frontend", "chat para probar el agente", or types /agente-basico. Es el patrón de este proyecto (Alcaldía de Girardota); repúntalo a otro negocio cambiando el prompt y las tools.
---

# Agente básico: agente + API + chat

Patrón mínimo y completo para un agente conversacional que se pueda probar desde un navegador. Es lo que hay en este repositorio; úsalo como referencia viva.

Skills que lo complementan (también están en este proyecto):

- `agent-prompt-yaml-format` — **cómo** se escribe el prompt (YAML + tags).
- `python-module-structure` — orden de la cabecera de cada `.py`.

## Estructura

```
.
├── Backend/
│   ├── agent.py                   # construye el agente (+ chat por terminal)
│   ├── api.py                     # FastAPI: /api/chat, /api/health
│   ├── prompt/system_prompt.yaml  # prompt en tags (sin datos que cambien)
│   ├── model_config/model_config.yaml
│   ├── tools/
│   │   ├── __init__.py            # TOOLS = [...]
│   │   └── <tool>.py              # una tool por archivo
│   ├── requirements.txt
│   ├── .env.example               # .env real NUNCA en git
│   └── .venv/
└── Frontend/                      # React + Vite
    ├── vite.config.js             # proxy /api → :8000
    └── src/App.jsx
```

## Decisiones fijas

| Tema | Decisión | Por qué |
|---|---|---|
| Framework | LangChain **v1**: `create_agent` + `system_prompt=` | `create_react_agent`, `AgentExecutor`, `prompt=` son v0 |
| Modelo | `gpt-4.1` vía `init_chat_model("openai:gpt-4.1")` | Modelo por defecto del usuario |
| Config del modelo | En `model_config/model_config.yaml`, nunca en el `.py` | Cambiar modelo/temperatura sin tocar código |
| Prompt | En `prompt/system_prompt.yaml`, placeholders con `.replace()` | Ver `agent-prompt-yaml-format` |
| Memoria | `checkpointer=InMemorySaver()` + `thread_id` en **cada** invoke | Sin `thread_id` no recuerda nada |
| Datos que cambian (fecha, hora, precios) | **Tools**, nunca escritos en el prompt | Un dato en el prompt se congela al arrancar el servidor |
| API | FastAPI; `session_id` del cliente = `thread_id` | Una conversación por pestaña |
| Frontend | Vite con proxy `/api` | Sin CORS ni URLs absolutas en desarrollo |

## 1. `model_config/model_config.yaml`

```yaml
name: <proyecto>-model-config
version: 1.0.0
description: Configuración del modelo de lenguaje del agente.

agent:
  bot_name: <Nombre>          # se inyecta como {bot_name}

model:
  provider: openai
  name: gpt-4.1
  temperature: 0.2            # bajo para atención al cliente: poca invención
  max_tokens: 1024
  timeout: 60
  max_retries: 2
```

## 2. `agent.py` — el núcleo

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from tools import TOOLS


def construir_system_prompt(bot_name):
    prompt_cfg = cargar_yaml(RUTA_PROMPT)
    return prompt_cfg["system_prompt"].replace("{bot_name}", bot_name)


def crear_agente():
    cfg = cargar_yaml(RUTA_MODEL_CONFIG)
    m = cfg["model"]
    modelo = init_chat_model(
        f"{m['provider']}:{m['name']}",
        temperature=m["temperature"],
        max_tokens=m["max_tokens"],
        timeout=m["timeout"],
        max_retries=m["max_retries"],
    )
    return create_agent(
        modelo,
        tools=TOOLS,
        system_prompt=construir_system_prompt(cfg["agent"]["bot_name"]),
        checkpointer=InMemorySaver(),
    )


def responder(agente, thread_id, mensaje):
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": mensaje}]},
        {"configurable": {"thread_id": thread_id}},
    )
    return resultado["messages"][-1].content
```

Con checkpointer solo se envía el mensaje **nuevo**; el historial lo recupera el agente por `thread_id`. No mantengas una lista de historial a mano.

Incluye una función `verificar_configuracion()` (falta `OPENAI_API_KEY`, faltan YAML) y llámala antes de crear el agente.

## 3. Tools

Una tool por archivo en `tools/`, registrada en `tools/__init__.py`:

```python
# tools/fecha_hora.py
from langchain.tools import tool

@tool
def obtener_fecha_hora_actual() -> str:
    """Devuelve la fecha, el día de la semana y la hora actuales en <ciudad>.

    Úsala siempre que necesites saber qué día u hora es: ...
    """
    ...
```

```python
# tools/__init__.py
from tools.fecha_hora import obtener_fecha_hora_actual

TOOLS = [obtener_fecha_hora_actual]
```

Reglas:

1. **El docstring es el contrato con el modelo.** Di qué devuelve y *cuándo* usarla. Un docstring vago = la tool no se llama.
2. **El nombre de la función es el nombre de la tool.** Debe aparecer idéntico en `<Herramientas_Disponibles>` del prompt.
3. **Devuelve texto que el modelo pueda leer** (frases o JSON), no objetos.
4. **Zona horaria explícita** en todo lo temporal: `ZoneInfo("America/Bogota")`, nunca `date.today()` a secas. Añade `tzdata` a `requirements.txt` (Windows no trae la base de zonas horarias).
5. **Sin efectos secundarios ocultos.** Si la tool escribe (crea un registro, envía algo), su nombre y docstring deben decirlo.

Para añadir una tool: archivo en `tools/` → añadir a `TOOLS` → describirla en el prompt → probar que se llama (ver Verificación).

## 4. `api.py` — FastAPI

```python
verificar_configuracion()
agente = crear_agente()          # una vez, al arrancar

app = FastAPI(title="...")
app.add_middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS, ...)

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=4000)

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        reply = await run_in_threadpool(responder, agente, req.session_id, req.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="El agente no pudo responder.") from exc
    return ChatResponse(reply=reply)
```

- `agent.invoke` es bloqueante → `run_in_threadpool` para no congelar el servidor.
- No devuelvas el texto de la excepción al cliente: puede contener detalles internos.
- Todo lo que se cree al arrancar (agente, prompt) queda **fijo** mientras el servidor viva. Por eso lo que cambia va en tools.

Ejecutar: `.venv/bin/uvicorn api:app --reload --port 8000`

## 5. Frontend (React + Vite)

```bash
npm create vite@latest Frontend -- --template react --no-interactive
```

```js
// vite.config.js
server: { proxy: { '/api': 'http://localhost:8000' } }
```

En `App.jsx`:

- `session_id` con `crypto.randomUUID()` al cargar; "Nueva conversación" genera otro.
- `fetch('/api/chat', { method: 'POST', body: JSON.stringify({ session_id, message }) })` → `data.reply`.
- Estado de carga (indicador "escribiendo"), error visible si el Backend no responde, Enter envía / Shift+Enter salto de línea.
- Si el mensaje de bienvenida repite el `bot_name`, avisa al usuario de que vive en dos sitios.

## Verificación (siempre, antes de dar por terminado)

```bash
cd Backend
# 1. Prompt: YAML válido, tags cerrados (script de agent-prompt-yaml-format)
# 2. Tools: nombre en el prompt == nombre registrado
.venv/bin/python -c "
import yaml; from tools import TOOLS
sp = yaml.safe_load(open('prompt/system_prompt.yaml'))['system_prompt']
print({t.name: t.name in sp for t in TOOLS})"

# 3. El agente llama a la tool cuando debe (y no cuando no)
.venv/bin/python -c "
import agent; ag = agent.crear_agente()
r = ag.invoke({'messages':[{'role':'user','content':'¿Qué día es hoy?'}]}, {'configurable':{'thread_id':'t'}})
print([tc['name'] for m in r['messages'] for tc in (getattr(m,'tool_calls',None) or [])])"

# 4. De punta a punta, por el proxy del Frontend (ambos servidores arriba)
curl -s -X POST localhost:5173/api/chat -H 'Content-Type: application/json' \
  -d '{"session_id":"p1","message":"Hola, me llamo Ana"}'
curl -s -X POST localhost:5173/api/chat -H 'Content-Type: application/json' \
  -d '{"session_id":"p1","message":"¿Cómo me llamo?"}'   # debe recordar "Ana"
```

## Errores típicos

- ❌ Fecha u hora escrita en el prompt → se congela; usa una tool.
- ❌ `invoke` sin `thread_id` → el agente no recuerda nada (o falla con checkpointer).
- ❌ Lista de historial manual **y** checkpointer → mensajes duplicados.
- ❌ Tool en `TOOLS` pero no en el prompt (o con otro nombre) → el modelo la ignora o la confunde.
- ❌ Mover `.venv` de carpeta → se rompe (rutas absolutas); recrearlo con `uv venv`.
- ❌ `.env` en el repo. Sube solo `.env.example` con las variables vacías.
- ❌ Leer o imprimir el valor de `OPENAI_API_KEY` para "comprobarlo": verifica solo que existe.

## Limitaciones conocidas del patrón

- `InMemorySaver` es volátil: reiniciar el Backend borra las conversaciones. Para persistir, `PostgresSaver` (Supabase: puerto 5432, no 6543).
- Sin RAG el agente responde con conocimiento general: el prompt debe prohibirle inventar costos, plazos, direcciones y teléfonos.
