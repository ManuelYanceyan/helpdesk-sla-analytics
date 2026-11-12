# Guía de entrevista — IT Helpdesk SLA Analytics

> Proyecto de portafolio con 480 tickets 100 % sintéticos. No representa trabajo
> para un cliente, un service desk real ni un SLA contractual.

## Explicación de 20–30 segundos

"Este proyecto analiza 480 tickets sintéticos de soporte TI de todo el año 2025.
Genero los datos con una semilla fija y calculo dos SLAs: primera respuesta y
resolución, cada uno con objetivos distintos según prioridad. Con pandas derivo
duraciones, cumplimiento, backlog, tasa de reapertura y CSAT. Luego produzco
reportes CSV, un resumen en Markdown y gráficos con matplotlib. Las pruebas
verifican la lógica de SLA con casos calculados a mano y que dos ejecuciones
generen los mismos resultados."

## Puntos que conviene saber explicar

1. **Dos SLAs separados:** el cliente espera una respuesta rápida y también una
   solución. Un promedio de resolución bueno puede esconder una primera respuesta
   lenta; por eso se reportan ambos.
2. **Objetivos por prioridad:** Crítico tiene 15 minutos para respuesta y 4 horas
   para resolución; Bajo tiene 8 horas y 48 horas. El cumplimiento es relativo al
   objetivo de cada ticket.
3. **Tickets abiertos sin respuesta:** cuentan como incumplimiento de respuesta
   porque el plazo ya venció. Excluirlos inflaría artificialmente el SLA.
4. **Backlog separado:** 84 tickets abiertos o pendientes se reportan aparte; la
   resolución solo se evalúa sobre tickets resueltos.
5. **CSAT no es SLA:** el CSAT es un promedio 1–5 de encuestas disponibles, no un
   porcentaje. Solo 308 de 396 cerrados tienen respuesta.
6. **Pruebas:** hay un caso pequeño con valores esperados calculados a mano y una
   prueba de reproducibilidad que compara los CSV de dos ejecuciones.

## Preguntas probables y respuestas breves

**¿Por qué Crítico tiene mejor cumplimiento de resolución que Medio?**
Porque el porcentaje es contra el objetivo de cada prioridad. Crítico permite
4 horas y Medio 24 horas. En los datos, Crítico promedia 3 horas y Medio 20.9
horas. Crítico sigue siendo más rápido en tiempo absoluto, aunque su meta sea más
exigente.

**¿Cómo tratas los tickets que siguen abiertos?**
Se cuentan como backlog. Si no tienen primera respuesta, cuentan como breach de
respuesta porque el objetivo ya pasó. No entran en el denominador de resolución
porque no están resueltos.

**¿Qué mejorarías con datos reales?**
Modelaría horario laboral y feriados, agregaría pausas o estados de espera del
cliente, separaría tiempo de negocio de tiempo calendario y analizaría la
distribución completa en lugar de solo promedios. También validaría la calidad
de las encuestas CSAT y el sesgo de respuesta.

**¿Qué no puedes concluir con este análisis?**
No puedo afirmar causalidad entre agente, categoría o prioridad y el SLA. Es un
análisis descriptivo sobre datos sintéticos, no una evaluación de desempeño real.

## Comandos para demostrar en vivo

```powershell
python generate_data.py
python analyze_tickets.py
python -m pytest -q tests
```

Mostrar `results/summary.md`, el gráfico `results/sla_by_priority.png` y explicar
la diferencia entre respuesta y resolución.
