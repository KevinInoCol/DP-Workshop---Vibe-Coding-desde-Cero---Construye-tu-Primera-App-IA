# 💬 Prompts del workshop

Estos son, **tal cual se escribieron**, los prompts con los que se construyó este proyecto usando Claude Code (vibe coding). Están agrupados por fase; el número indica el orden en que se escribieron. Debajo de cada uno hay una línea con lo que se obtuvo.

> El system prompt **del agente** (lo que el agente lee, no lo que le pedimos a Claude Code) vive en [`Backend/prompt/system_prompt.yaml`](Backend/prompt/system_prompt.yaml).

## Índice

| Fase | Prompts |
|---|---|
| 1. Preparación del entorno | [1](#1) · [2](#2) |
| 2. Agente básico | [3](#3) |
| 3. Backend + Frontend + API | [4](#4) · [5](#5) |
| 4. Repositorio y documentación | [6](#6) · [7](#7) |
| 5. Tools | [8](#8) · [9](#9) · [12](#12) |
| 6. Skills del proyecto | [10](#10) · [11](#11) |
| 7. RAG con Qdrant | [13](#13) · [14](#14) · [15](#15) · [16](#16) · [17](#17) · [18](#18) |
| 8. Memoria persistente | [19](#19) · [20](#20) |
| 9. Frontend institucional | [21](#21) · [22](#22) |
| 10. Cambio de modelo | [23](#23) · [24](#24) · [25](#25) |
| 11. Este archivo | [26](#26) |

---

## 1. Preparación del entorno

### 1

```text
Tenemos las MCP's de la documentación de langchain instaladas ?
```

→ Se confirmó que los MCP `docs-langchain` y `reference-langchain` estaban conectados.

### 2

```text
Estas MCP's instalalas de forma global, no solo para esta sesión.
```

→ Ya estaban a nivel de usuario; se quitaron las copias locales duplicadas del proyecto.

## 2. Agente básico

### 3

```text
Vamos a crear un agente básico con un prompt instruction y una configuración de modelo.

El Modelo de Lenguaje que vamos a usar es el GPT 4.1.
El prompt instruction me lo vas a colocar en un archivo YAML. Este prompt debe estar en formato de TAGS.
La configuración el modelo también me lo vas a colocar en un archivo YAML.

El agente lo vas a colocar dentro de un agent.py

Este agente, es una agente para la minucipalidad de girardota. Por lo tanto él debe ser capaz de responder consultas de la población de dicha ciudad, tramites sobretodo.
```

→ `agent.py` con LangChain v1 (`create_agent`), `prompt/system_prompt.yaml` en tags y `model_config/model_config.yaml`.

## 3. Backend + Frontend + API

### 4

```text
Todo lo generado hasta el momento correspondiente al agente, vas a colocarlo en una carpeta llamada "Backend".

Posteriormente vas a generar una carpeta "Frontend" la cual la trabajaras con ReactJS. Si falta instalar alguna de las dependencias como: node, etc, instalalas.
Este Frontend, debe tener un chat en él, para poder probar aquel agente.

El agente debe ser consumido por el Frontend media api. Usa FastAPI. Ese script debe estar en "Backend".
```

→ Carpetas `Backend/` (con `api.py` en FastAPI) y `Frontend/` (React + Vite con proxy `/api`).

### 5

```text
Killea lo que esté corriendo en el puerto 8000
```

→ Se detuvo el proceso de uvicorn que ocupaba el puerto.

## 4. Repositorio y documentación

### 6

```text
hAS UN PUSH DE ESTE PROYECTO AUQI: https://github.com/KevinInoCol/DP-Workshop---Vibe-Coding-desde-Cero---Construye-tu-Primera-App-IA

Está con mi cuenta personal, kevininocol, no uses la inside, no uses la corporativa
```

→ Primer push con la cuenta personal, verificando que el `.env` no se subiera.

### 7

```text
Hazte un readme está feo
```

→ `README.md` con arquitectura, puesta en marcha, API y configuración.

## 5. Tools

### 8

```text
Le has dado la fecha de hoy ? cómo sabe la fecha?
```

→ Se explicó que la fecha iba en el prompt y quedaba congelada al arrancar el servidor.

### 9

```text
Crea una carpeta "tools" y dentro una tool de hora y fecha, cada que el agente laa necesite, irá a ejecutará dicha tool, de esta forma no tendrá que estar incluida en el prompt.
```

→ `tools/fecha_hora.py` con `obtener_fecha_hora_actual` (zona `America/Bogota`).

### 12

```text
Generame una tool de conexión a internet. Para eso vamos a usar Tavily.
```

→ `tools/busqueda_web.py` con `buscar_en_internet` (`langchain-tavily`) y reglas de uso en el prompt.

## 6. Skills del proyecto

### 10

```text
Vamos a colocar las skills en el proyecto. La Skill de agente básico y la del formato de prompt, tal vez incluimos la de estructura.
```

→ Ante la pregunta de cuáles, se eligió **python-module-structure** + **crear una skill nueva `agente-basico`**. Quedaron en `.claude/skills/` junto a `agent-prompt-yaml-format`.

### 11

```text
has un push al repo
```

→ Push de la tool de fecha, las skills y el README.

## 7. RAG con Qdrant

### 13

```text
En la carpeta "rag" del backend, vas a crear un Pipeline básico de RAG, de 4 steps. La información que vamos a cargar, va a estar dentro de una subcarpeta llamada "Base de Conocimiento". Que va a tener un archivo PDF, el cual deberá ser cargado a una base de datos vectorial, Qdrant.

Vamos a levantar ese "Qdrant" en local. Por ende deberás crear un archivo docker-compose que permita levantar aquel servicio. Este docker-compose no tiene por qué estar dentro de Backend.
```

→ `rag/ingesta.py` (cargar → dividir → embeddings → guardar) y `docker-compose.yml` con Qdrant.

### 14

```text
Levanta por favor la base de datos vectorial y dame la direccion
```

→ Qdrant arriba en http://localhost:6333/dashboard.

### 15

```text
Realiza la ingesta sobre el Qdrant con el rag que construimos, ya te puse allí el PDF.
```

→ Manual de Trámites (95 páginas) cargado en la colección `tenant_id_alcaldia_girardota`.

### 16

```text
has un push
```

→ Push de Tavily, el pipeline RAG, el PDF y el docker-compose.

### 17

```text
Ahora que tenemos la colección, necesito una tool de RETRIEVAL, que el agnte la use para poder tener conocimiento de los requisitos y tramites que realiza la municipalidad. Deberíamos afinar el Promtp Instruction para que esté acorde a lo que estamos implementando.
```

→ `tools/base_conocimiento.py` (`buscar_en_base_de_conocimiento`), `rag/retriever.py`, `rag/config.py` y prompt v2.0.0 con el manual como fuente principal.

### 18

```text
Para empezar, necesito LOGS en la terminal, para saber cuando se está haciendo uso de alguna tool.

Por otro lado el agente está respondiendo de forma incompleta los documentos requeridos para algun tramite en específico. Date una vuelta por el PDF, analizalo, e implementa mejoras dentro de nuestra pipeline de RAG. De tal forma que el performance de respuesta mejora.

Aquí unos ejemplos de lo incompleto que fue la respuesta:
[Imagen 1: respuesta del chat sobre "Aprobación de piscinas" con la lista de documentos incompleta]
[Imagen 2: seguimiento "¿Esos son los documentos requeridos completos?" con requisitos mezclados de otro trámite]
```

→ Middleware de logs (`@wrap_tool_call`), chunking **por trámite** (102 trámites), reconstrucción de trámites largos en el retriever, prompt v2.1.0 sin límite de puntos en las listas y `max_tokens` a 2048.

## 8. Memoria persistente

### 19

```text
Este agente tiene memoria ?
```

→ Se explicó la memoria de corto plazo en RAM (`InMemorySaver` por `thread_id`) y cuándo se pierde.

### 20

```text
Dentro del mismo docker-compose.yaml vamos a levantar un postgres para el histórico de conversación. De tal forma que deje de ser efímero.
```

→ Postgres 18 en el `docker-compose.yml`, `memoria/checkpointer.py` con `PostgresSaver` + pool en el esquema `alcaldia_girardota`. Probado: el agente recuerda tras reiniciar el servidor.

## 9. Frontend institucional

### 21

```text
Mejoremos ese Frontend. Aquí te paso la site de la muni, la site oficial: [Imagen 3: captura del sitio web oficial de la Alcaldía Municipal de Girardota]

Ahí te lo dejo a tu criterio.
```

→ Diseño con la paleta del sitio, panel de trámites frecuentes del manual, respuestas en Markdown, aviso de la línea 123 y retoma de la conversación al recargar (endpoint `/api/historial`).

### 22

```text
has un push
```

→ Push del RAG por trámite, logs, memoria en Postgres y el nuevo Frontend.

## 10. Cambio de modelo

### 23

```text
usemos el modelo gpt 5.4 mini, pruebalo si es que lo tengo disponible
```

→ Se verificó la disponibilidad en la API key y se probó el agente completo con `gpt-5.4-mini`.

### 24

```text
mandalo al gpt 5.1 por favor
```

→ Modelo cambiado a `gpt-5.1` y comparado con 5.4 mini (más completo, más lento).

### 25

```text
has un push
```

→ Push del cambio de modelo.

## 11. Este archivo

### 26

```text
Coloca todos los prompts que usamos dentro de un archivo MD y luego pushea al repo
```

→ Este `PROMPTS.md`.
