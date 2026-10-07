---
name: agent-prompt-yaml-format
description: Convención de FORMATO para system prompts de agentes — YAML con metadata + bloque `system_prompt` estructurado con tags estilo XML. El formato es obligatorio; el contenido y el conjunto de tags se adaptan al negocio. Use whenever creating, editing, rewriting, or reviewing an LLM agent system prompt (LangChain, LlamaIndex, or any framework) — including when the user mentions "prompt", "system prompt", "prompt.yaml", "persona del agente", or asks to adapt an agent to a new use case or business domain. Apply this format by default unless the user explicitly asks otherwise.
---

# Formato de system prompts de agente (YAML + tags XML)

Esta skill define **cómo se estructura** el prompt, no qué dice. El contenido —persona, tono, flujos, reglas de negocio— es decisión del usuario y cambia con cada proyecto. Lo que no cambia es el formato.

## Invariantes (no negociables)

1. **El prompt vive en un YAML, nunca hardcodeado en `.py`.** Normalmente `prompt/system_prompt.yaml` (ver skill `agent-project-structure`). El nombre puede variar, pero debe coincidir con lo que carga el código.
2. **Va como bloque literal `|` bajo la clave `system_prompt`.** Así se preservan los saltos de línea y no hay que escapar nada.
3. **Cada sección va delimitada por un tag estilo XML**, abierto y cerrado. Nunca títulos en MAYÚSCULAS sueltos ni secciones sin delimitar.
4. **Una sola convención de nombres de tag por archivo.** Elige un estilo y aplícalo a todos:
   - `<Identidad>`, `<Fuentes_De_Datos>` — capitalizado con guión bajo
   - `<identidad>`, `<fuentes_de_datos>` — minúscula con guión bajo

   Las dos son válidas. **Mezclarlas no.**
5. **Todo tag abierto se cierra.** Un `<Reglas>` sin `</Reglas>` degrada la separación de secciones y el modelo empieza a fundirlas.
6. **Metadata del prompt en el mismo YAML, fuera del bloque.** `name`, `version`, `description`, `language`, `author`, `tags`, `variables`. Es lo que permite saber qué prompt está corriendo en producción.
   - **`author` siempre es `kevin.inofuente.colque.27@gmail.com`.** No uses el correo de la cuenta de Claude ni un placeholder.

## Esqueleto del archivo

```yaml
name: <proyecto>-system-prompt
version: 1.0.0
description: >
  Qué agente es, para qué negocio, con qué fuentes de datos y sobre qué CRM
  o canal opera.
language: es
author: kevin.inofuente.colque.27@gmail.com
created_at: YYYY-MM-DD
tags: [rag, tool-calling, <rubro>]

# Los placeholders que el loader inyecta en runtime.
variables:
  - bot_name

system_prompt: |
  <Identidad>
  ...
  </Identidad>

  <Herramientas_Disponibles>
  ...
  </Herramientas_Disponibles>

  ...
```

### Placeholders

Se inyectan desde el código, típicamente con `.replace()`:

```python
prompt_cfg["system_prompt"].replace("{bot_name}", bot_name)
```

Declara cada uno en `variables:`. Si el prompt pasara por `str.format()` en algún punto, toda llave `{}` literal rompería con `KeyError` — con `.replace()` no hay ese riesgo, pero conviene saber cuál de los dos usa tu loader.

## Conjunto base de tags

Un **punto de partida**, no una lista cerrada. Cubre las seis funciones que todo prompt de agente necesita. Añade, quita, renombra o divide según el negocio.

| Función | Tag sugerido | Qué va dentro |
|---|---|---|
| Quién es | `<Identidad>` | Nombre del bot, empresa, rubro, zona, idioma |
| Cómo habla | `<Personalidad>` | Tono, registro, nivel de formalidad |
| Qué puede hacer | `<Habilidades>` | Capacidades en vocabulario del dominio |
| Para qué existe | `<Objetivo_Principal>` | El resultado que persigue cada conversación |
| De dónde saca la verdad | `<Fuentes_De_Datos>` | Qué tool es autoritativa para qué tema |
| Con qué actúa | `<Herramientas_Disponibles>` | Nombre EXACTO de cada tool + cuándo usarla |
| Reglas transversales | `<Instrucciones_Generales>` | Idioma, qué nunca inventar, qué no revelar |
| Cómo elige tools | `<Reglas_De_Uso_De_Tools>` | Exclusiones mutuas, combinaciones válidas |
| Qué quiere el cliente | `<Deteccion_Intenciones>` | Tabla intención → señales → ejemplos → acción |
| Qué hace en cada caso | `<Flujos_Por_Intencion>` | Un sub-bloque por intención |
| Cómo responde | `<Formato_De_Respuesta>` | Longitud, moneda, viñetas, emojis o no |
| Lo que no puede fallar | `<IMPORTANTE>` | Los 4-6 guardrails críticos, repetidos al final |

Tags de dominio frecuentes: `<Contexto_Temporal>` (si se inyecta fecha en runtime), `<Escalamiento>` (cuándo pasar a un humano), `<Cierre_Seguro>` (si el rubro lo exige: salud, legal, financiero), `<Retoma_De_Conversacion>` (si hay clientes que vuelven tras días).

**Orden recomendado:** identidad → contexto → capacidades → ruteo → límites → ejemplos. Lo crítico al principio y repetido al final; el medio es donde el modelo pierde atención.

## Reglas de contenido

Estas sí aplican siempre, aunque el texto sea del usuario:

1. **El prompt NO duplica la base de conocimiento.** Tarifas, políticas, precios y direcciones viven en el RAG y se recuperan con la tool. El prompt solo dice *cuándo* consultarla. Duplicarlos crea dos fuentes de verdad que se desincronizan.
2. **Nombres de tools exactos.** Los que aparecen en el prompt deben coincidir carácter por carácter con los registrados en `tools/`. Si el docstring de una tool contradice al prompt (típico tras un cambio de dominio), avísalo al usuario: **el docstring es el contrato real con el modelo**, el prompt es contexto.
3. **Fechas nunca literales.** Si el agente necesita saber "hoy", se inyecta en runtime. Una fecha escrita en el prompt envejece en silencio.
4. **Idioma de respuesta explícito.**
5. **Las acciones se ejecutan con tools, no con texto.** Prohíbe marcadores del tipo `[MOVER_A_ETAPA]` en la respuesta: el cliente los vería.
6. **Si hay memoria o resumen, el prompt debe decir cómo tratarlos.** Que los use como conocimiento propio y que nunca los mencione ni los cite.

## Anti-patrones

- ❌ Títulos en MAYÚSCULAS sin tags (`INSTRUCCIONES:`) — migrar a tags.
- ❌ Mezclar `<Identidad>` y `<herramientas>` en el mismo archivo.
- ❌ Tags abiertos sin cerrar.
- ❌ Copiar párrafos de la base de conocimiento dentro del prompt.
- ❌ Mencionar tools que no existen, o con nombre distinto al registrado.
- ❌ Prompt monolítico sin secciones.
- ❌ Prompt hardcodeado en un `.py`.
- ❌ Metadata sin `version`: nadie sabe qué prompt está en producción.

## Migrar un prompt existente

Si el proyecto ya tiene un prompt con otra convención: **migra el archivo entero o no lo toques.** Un prompt a medio migrar, con dos juegos de tags conviviendo, es peor que cualquiera de los dos formatos puros.

Tras migrar, comprueba que el código siga leyendo la clave y la ruta correctas (`_render_system_prompt()` o su equivalente).

## Validación

Al terminar, siempre:

```bash
python -c "
import re, yaml
p = yaml.safe_load(open('prompt/system_prompt.yaml'))
sp = p['system_prompt']
print('✅ YAML parsea |', p.get('name'), 'v' + str(p.get('version')))

# Solo cuentan como sección los tags SOLOS en su línea. Un tag citado dentro de
# una frase es una referencia (p. ej. un bloque que el código inyecta en runtime),
# no una sección — si no se ancla a inicio de línea, da falsos positivos.
abiertos = re.findall(r'^[ \t]*<([A-Za-z_]+)>[ \t]*$', sp, re.M)
cerrados = re.findall(r'^[ \t]*</([A-Za-z_]+)>[ \t]*$', sp, re.M)
huerfanos = set(abiertos) ^ set(cerrados)
print('❌ tags sin pareja:', huerfanos) if huerfanos else print('✅ todos los tags cierran')

tags = list(dict.fromkeys(abiertos))
cap = [t for t in tags if t[0].isupper()]
low = [t for t in tags if t[0].islower()]
print(f'⚠️ MEZCLA de convenciones: {cap} vs {low}') if cap and low else print('✅ convención única')
print('   tags:', ', '.join(tags))
"
```

Y verifica a ojo que los nombres de tools del prompt existan en `tools/`.

## Skills relacionadas

- `agent-project-structure` — dónde vive el prompt y el resto del proyecto.
- `agent-domain-swap` — repuntar un agente completo a otro negocio (el prompt es el paso 5).
