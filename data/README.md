# Diccionario de datos sintéticos

Todos los tickets son ficticios y se generan con `generate_data.py`. La
ejecución por defecto usa la semilla `7` y produce 480 tickets fechados a lo
largo de 2025. No se incluyen usuarios, agentes, clientes ni acuerdos de nivel
de servicio reales.

## tickets.csv

| Columna | Tipo | Descripción |
| --- | --- | --- |
| `ticket_id` | texto | Clave primaria, formato `HD-2025-0001` |
| `created_at` | fecha y hora ISO | Fecha y hora de creación del ticket |
| `first_response_at` | fecha y hora ISO | Primera respuesta del agente; vacío en algunos tickets abiertos |
| `resolved_at` | fecha y hora ISO | Fecha y hora de resolución; vacío salvo que el estado sea `Closed` |
| `priority` | texto | `Low`, `Medium`, `High` o `Critical` |
| `category` | texto | Hardware, Software, Network, Access, Email u Other |
| `channel` | texto | Email, Portal, Phone o Chat |
| `agent` | texto | Agente de soporte ficticio |
| `status` | texto | `Closed`, `Pending` o `Open` |
| `reopened` | entero | 1 cuando un ticket cerrado fue reabierto; 0 en caso contrario |
| `satisfaction` | entero | Puntuación CSAT de 1 a 5; vacío cuando no se respondió |

## Objetivos de SLA ilustrativos

| Prioridad | Primera respuesta (minutos) | Resolución (minutos) |
| --- | ---: | ---: |
| Critical | 15 | 240 |
| High | 60 | 480 |
| Medium | 240 | 1,440 |
| Low | 480 | 2,880 |

Estos objetivos son parámetros de demo, no un contrato real. Viven en
`analyze_tickets.py` para poder cambiarlos y volver a ejecutar las pruebas.

## Campos derivados

| Campo | Definición |
| --- | --- |
| `response_minutes` | `first_response_at - created_at` en minutos |
| `resolution_minutes` | `resolved_at - created_at` en minutos |
| `response_met` | Duración de respuesta <= objetivo de respuesta; una respuesta ausente es incumplimiento |
| `resolution_met` | Duración de resolución <= objetivo de resolución; `NA` cuando no está resuelto |
| `sla_met` | Respuesta y resolución cumplidas; `NA` cuando no está resuelto |
| `resolution_hours` | Duración de resolución en horas |
| `month` | Mes de creación en formato `YYYY-MM` |

## Notas metodológicas

- Un ticket es `Closed` si tiene una marca de tiempo de resolución.
- Los tickets `Pending` y `Open` cuentan como backlog y no se incluyen en el
  denominador del SLA de resolución.
- CSAT es la media de las respuestas 1-5 disponibles, no un porcentaje.
- Las duraciones usan tiempo calendario (24/7), no horario laboral.
