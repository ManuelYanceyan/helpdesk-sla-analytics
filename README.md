# Análisis de SLA para Helpdesk de TI con Python

Un proyecto de análisis de service desk reproducible, construido con **Python,
pandas y matplotlib**. Analiza 480 tickets de soporte sintéticos, mide los SLA
de primera respuesta y resolución, identifica patrones de backlog y categorías,
y exporta reportes y gráficos.

> **Aviso sobre los datos:** todos los tickets, agentes y respuestas de
> satisfacción son ficticios y se generan localmente. Esto no es trabajo para
> clientes, experiencia en producción ni un acuerdo de nivel de servicio real.

## Qué demuestra este proyecto

- Generación de datos sintéticos con una semilla fija y marcas de tiempo realistas.
- Modelado de SLA por prioridad con objetivos explícitos de respuesta y resolución.
- Transformaciones con pandas: aritmética de fechas, booleanos anulables,
  agrupaciones y agregación mensual.
- Diseño de KPI para service desks: cumplimiento de SLA, backlog, MTTR, tasa de
  reapertura y CSAT.
- Visualización clara de datos con matplotlib usando un backend no interactivo.
- Pruebas automatizadas para la lógica de SLA, la agregación y la reproducibilidad.

## Conjunto de datos

`data/tickets.csv` contiene **480 tickets sintéticos** creados durante 2025:

| Campo | Descripción |
| --- | --- |
| `ticket_id` | Identificador con formato `HD-2025-0001` |
| `created_at` | Fecha y hora de creación del ticket |
| `first_response_at` | Primera respuesta del agente (vacío en algunos tickets abiertos) |
| `resolved_at` | Fecha y hora de resolución (vacío en tickets abiertos/pendientes) |
| `priority` | Low, Medium, High o Critical |
| `category` | Hardware, Software, Network, Access, Email u Other |
| `channel` | Email, Portal, Phone o Chat |
| `agent` | Agente de soporte ficticio |
| `status` | Closed, Pending o Open |
| `reopened` | 1 si el ticket fue reabierto |
| `satisfaction` | CSAT de 1 a 5 cuando está disponible |

La muestra generada tiene 396 tickets cerrados, 84 abiertos/pendientes y 308
respuestas de satisfacción. Consulta `data/README.md` para ver el diccionario
completo y los objetivos de SLA.

## Herramientas

- Python 3.12
- pandas
- matplotlib
- pytest

## Estructura del proyecto

```text
helpdesk-sla-analytics/
├── data/                    # tickets.csv sintético
├── results/                 # reportes CSV, summary.md y gráficos PNG
├── tests/                   # pruebas de generación y análisis
├── generate_data.py         # generador de tickets sintéticos con semilla
├── analyze_tickets.py       # enriquecimiento, KPI, desgloses y gráficos
├── requirements.txt
└── conftest.py
```

## Inicio rápido

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python generate_data.py
python analyze_tickets.py
python -m pytest -q tests
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python generate_data.py
python analyze_tickets.py
python -m pytest -q tests
```

`analyze_tickets.py` usa el modelo de tiempo calendario 24/7 descrito abajo. Usa
`--no-charts` si solo necesitas las salidas CSV y Markdown.

## Modelo de SLA

Los niveles de servicio son objetivos ilustrativos creados para esta demo:

| Prioridad | Primera respuesta | Resolución |
| --- | ---: | ---: |
| Critical | 15 minutos | 4 horas |
| High | 60 minutos | 8 horas |
| Medium | 4 horas | 24 horas |
| Low | 8 horas | 48 horas |

El cumplimiento se calcula así:

```text
response_met   = first_response_at - created_at <= objetivo de respuesta
resolution_met = resolved_at - created_at <= objetivo de resolución
```

Los tickets abiertos sin primera respuesta cuentan como incumplimiento de
respuesta porque el objetivo ya venció. El cumplimiento de resolución se evalúa
solo en tickets que tienen una marca de tiempo de resolución. Las duraciones usan
tiempo calendario 24/7.

## Resultados observados (semilla 7, 480 tickets)

Estos son los valores producidos por los scripts de este repositorio:

| Métrica | Valor |
| --- | ---: |
| Tickets | 480 |
| Cerrados / abiertos-pendientes | 396 / 84 |
| Backlog crítico | 8 |
| SLA de primera respuesta | 82.5% |
| SLA de resolución | 77.5% |
| Primera respuesta media | 182 minutos |
| Mediana del tiempo de resolución | 15.3 horas |
| Tasa de reapertura entre cerrados | 8.6% |
| CSAT medio | 3.68 / 5 (308 respuestas) |

Patrones seleccionados:

- **El cumplimiento de resolución es más bajo en tickets Medium (73.5%)**,
  mientras que Critical alcanza 84.8%. El cumplimiento es relativo al objetivo
  de cada ticket, por lo que un ticket Critical puede cumplir a las 3 horas
  mientras uno Medium incumple al superar las 24 horas.
- **Software tiene el cumplimiento de resolución más bajo entre las categorías
  con al menos 30 tickets (72.1%)**, seguido de Access (72.2%). La categoría
  pequeña "Other" (19 tickets) se excluye de esa comparación porque es demasiado
  ruidosa.
- La vista mensual no muestra una tendencia sostenida; la muestra sintética
  varía aproximadamente entre 77% y 90% de cumplimiento de primera respuesta.

Las salidas completas están en [`results/summary.md`](results/summary.md), y los
gráficos son `results/*.png`.

## Metodología

1. `generate_data.py` crea marcas de tiempo, prioridades, estados y asignaciones
   de agentes con `random.Random(seed)`.
2. Las duraciones de respuesta y resolución se muestrean alrededor de los
   objetivos de cada prioridad; una proporción configurable se convierte en
   incumplimiento.
3. `analyze_tickets.py` deriva duraciones y banderas de SLA, luego calcula KPI,
   desgloses por prioridad/categoría/agente/canal y una tendencia mensual.
4. Los resultados se exportan como CSV, un resumen en Markdown y cinco gráficos PNG.

El generador conserva intencionalmente los tickets abiertos y pendientes en la
misma tabla: excluirlos ocultaría el backlog e inflaría el rendimiento de SLA.

## Pruebas

```text
python -m pytest -q tests
10 passed
```

La suite cubre:

- generación determinista y volumen de filas esperado;
- coherencia de marcas de tiempo (respuesta antes de resolución, sin resolución en abiertos);
- lógica de SLA sobre una muestra construida a mano con valores esperados conocidos;
- cálculos de KPI, particiones de agrupación y totales mensuales;
- creación de todas las salidas CSV, Markdown y PNG;
- salida CSV idéntica byte a byte entre ejecuciones repetidas del análisis;
- un error claro cuando falta el archivo de entrada.

## Limitaciones

- Datos sintéticos y objetivos ilustrativos; no representan a ningún cliente,
  contrato ni personal real.
- Las duraciones son de calendario; no se modelan horarios laborales, feriados
  ni turnos de guardia.
- Una primera respuesta ausente se trata como incumplimiento; el generador no
  modela tickets "todavía dentro del objetivo" que siguen esperando.
- CSAT solo está disponible para un subconjunto de tickets cerrados y en un
  service desk real podría verse afectado por el sesgo de respuesta.
- La tasa de reapertura se calcula solo entre tickets cerrados.
- El análisis es descriptivo; no afirma causalidad entre prioridad, agente o
  categoría y los resultados de SLA.

## Preguntas de entrevista para las que prepara este proyecto

1. **¿Por qué Critical puede tener mejor porcentaje de SLA que Medium?**
   El cumplimiento compara cada ticket contra su propio objetivo. Critical
   permite 4 horas para resolver, mientras que Medium permite 24 horas. Los
   tickets Critical tienen un objetivo más exigente pero también reciben una
   atención más rápida en este conjunto de datos; el porcentaje por sí solo no
   significa que los tickets Critical se resuelvan más rápido en términos
   absolutos.

2. **¿Cómo deberían afectar los tickets abiertos sin respuesta a la métrica de SLA?**
   No deberían excluirse silenciosamente, porque eso infla el rendimiento. Una
   vez que venció el objetivo de respuesta, un ticket sin responder es un
   incumplimiento. El proyecto cuenta estos tickets en el denominador del SLA de
   respuesta y reporta el backlog por separado.

3. **¿Por qué reportar tanto el SLA de respuesta como el de resolución?**
   Miden partes diferentes de la experiencia del cliente. Una primera respuesta
   rápida no garantiza una solución rápida, y un buen tiempo de resolución puede
   ocultar una larga espera sin comunicación. Reportar ambos evita que una
   métrica tape a la otra.
