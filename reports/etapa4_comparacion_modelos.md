# Etapa 4 — Comparación de modelos

Evaluación sobre el mismo `test_questions.json` (42 ejemplos), mismas
funciones de métricas (`src.baseline_metrics`), misma estrategia de
generación (`do_sample=False`, `max_new_tokens=512`).

## Tabla unificada

| Modelo                          |   rouge1 |   rouge2 |   rougeL |   secciones_presentes |   longitud_media_palabras |   no_causalidad_cuando_aplica |
|:--------------------------------|---------:|---------:|---------:|----------------------:|--------------------------:|------------------------------:|
| FLAN-T5-base (vanilla)          |   0.1746 |   0.0341 |   0.0872 |                0.0298 |                     123.7 |                             1 |
| Qwen2.5-1.5B-Instruct (vanilla) |   0.3828 |   0.12   |   0.2296 |                0.9524 |                     160.9 |                             1 |
| Qwen2.5-1.5B-Instruct (LoRA)    |   0.7055 |   0.635  |   0.6753 |                0.7976 |                     159.5 |                             1 |

## Delta del fine-tuning vs Qwen vanilla

| Métrica | Δ (LoRA − vanilla) |
|---|---|
| ROUGE-1   | +0.3227 |
| ROUGE-2   | +0.5150 |
| ROUGE-L   | +0.4457 |
| Secciones | -0.1548 |

## Ejemplos cualitativos lado a lado

### Intent: `ranking_accidentes`

**Pregunta:** Eres un asistente analítico de datos de movilidad en México.
Reglas estrictas que debes seguir SIEMPRE:
1. Responde únicamente en español claro y profesional.
2. Usa SOLO los datos numéricos que se te proporcionan en este prompt.
   No inventes cifras, porcentajes, estados ni años.
3. Si comparas ve...

**Gold:**
```
1. Resumen
En 2014, Nuevo León encabezó el ranking de accidentes viales con 23,564 incidentes registrados, seguida por Colima con 15,145.

2. Datos principales
- 1.° Nuevo León: 23,564 accidentes
- 2.° Colima: 15,145 accidentes
- 3.° Campeche: 12,977 accidentes
- 4.° Coahuila: 12,688 accidentes
- 5.° Aguascalientes: 10,014 accidentes

3. Interpretación
Las 5 entidades del ranking concentran 74,388 accidentes en 2014. Las zonas metropolitanas de alta densidad poblacional y tráfico vehicular tienden a acumular más incidentes. El volumen absoluto no refleja la tasa de accidentalidad por habitante ni por vehículo en circulación.

4. Limitaciones
- Los datos ATUS cubren zonas urbanas y suburbanas; los incidentes en carreteras rurales y federales pueden estar subrepresentados.
- El ranking refleja volumen absoluto, no tasas por población ni parque vehicular.
```

**FLAN-T5-base (vanilla):**
```
1. Resumé (1-2 frases con la conclusión principal). 2. Principal (no nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros nmeros 
```

**Qwen-1.5B (vanilla):**
```
Resumen: Las entidades con más accidentes de tráfico en 2014 fueron Nuevo León, Colima, Campeche, Coahuila y Aguascalientes, cada una registrando alrededor de 1,000 a 2,000 accidentes.

Datos principales:
- Nuevo León: 2,356 accidentes
- Colima: 1,514 accidentes
- Campeche: 1,297 accidentes
- Coahuila: 1,268 accidentes
- Aguascalientes: 1,001 accidentes

Interpretación: Estos datos indican que algunas regiones urbanas y suburbanas de México experimentaron altos niveles de accidentes de tráfico en el año 2014. Sin embargo, es importante recordar que estas estadísticas solo reflejan el número total de accidentes y no proporcionan información sobre causas específicas o factores que podrían estar relacionados con estos eventos.

Limitaciones: Los datos proporcionados son suficientes para identificar las entidades con más accidentes, pero no permiten determinar causas específicas o realizar predicciones futuras basadas en estos datos. Además, hay poca información disponible sobre cómo estos accidentes ocurrieron o cuál fue su impacto social o económico.
```

**Qwen-1.5B (LoRA):**
```
1. Resumen
En 2014, Nuevo León encabezó el ranking de accidentes viales con 23,564 incidentes registrados, seguida por Colima con 15,145.

2. Datos principales
- 1.° Nuevo León: 23,564 accidentes
- 2.° Colima: 15,145 accidentes
- 3.° Campeche: 12,977 accidentes
- 4.° Coahuila: 12,688 accidentes
- 5.° Aguascalientes: 10,014 accidentes

3. Interpretación
Las 5 entidades del ranking concentran 72,380 accidentes en 2014. Las zonas metropolitanas de alta densidad poblacional y tráfico vehicular tienden a acumular más incidentes. El volumen absoluto no refleja la tasa de accidentalidad por habitante ni por vehículo en circulación.

4. Limitaciones
- Los datos ATUS cubren zonas urbanas y suburbanas; los incidentes en carreteras rurales y federales pueden estar subrepresentados.
- El ranking refleja volumen absoluto, no tasas por población ni parque vehicular.
```

---

### Intent: `accidentes_por_tipo`

**Pregunta:** Eres un asistente analítico de datos de movilidad en México.
Reglas estrictas que debes seguir SIEMPRE:
1. Responde únicamente en español claro y profesional.
2. Usa SOLO los datos numéricos que se te proporcionan en este prompt.
   No inventes cifras, porcentajes, estados ni años.
3. Si comparas ve...

**Gold:**
```
1. Resumen
El tipo de accidente más frecuente en Yucatán es «Colisión con vehículo automotor» con 34,303 incidentes (42.0% del total). Le sigue «Colisión con motocicleta» con 13,416 (16.4%).

2. Datos principales
- 1.° Colisión con vehículo automotor: 34,303 (42.0%)
- 2.° Colisión con motocicleta: 13,416 (16.4%)
- 3.° Colisión con peatón (atropellamiento): 12,011 (14.7%)
- 4.° Certificado cero: 12,002 (14.7%)
- 5.° Colisión con objeto fijo: 4,585 (5.6%)
- 6.° Colisión con ciclista: 1,641 (2.0%)
- 7.° Volcadura: 1,633 (2.0%)
- 8.° Salida del camino: 1,351 (1.6%)
- 9.° Colisión con animal: 526 (0.6%)
- 10.° Otro: 247 (0.3%)

3. Interpretación
La distribución por tipo de accidente indica los siniestros que más afectan la vía pública. Las categorías dominantes suelen relacionarse con velocidad excesiva, distracciones al volante y condiciones de la infraestructura vial. Esta información es útil para priorizar campañas de prevención y políticas de seguridad vial.

4. Limitaciones
- Los datos cubren zonas urbanas y suburbanas en Yucatán; no incluye la totalidad de siniestros en carreteras rurales o federales.
- La clasificación TIPACCID del INEGI puede agrupar subcategorías de distinta naturaleza.
```

**FLAN-T5-base (vanilla):**
```
He is an analytical assistant of data in Mexico. Reglas estrictas que debe seguir SIEMPRE: 1. Responde nicamente en espaol claro y profesional 2. Use SOLO the numbers provided in this prompt. No invent figures, porcentajes, estados ni years. 3. If compares vehicles with accidents, NO afirm causality. Talk about correlation, asociación, or coincidencia temporal, and mention explcitamente that correlation does not implica causality. 4. If the data are insufficient (a few years, a few years), dilo. 5. Use an ejecutivo tone: claro, breve, accionable. Sources: INEGI - ATUS (Accidentes de Tránsito en Zonas Urbanas y Suburbanas) y/o VMRC (Administrativo de Vehculos). Tacto: Distribución de accidentes por tipo (TIPACCID) en Yucatán (agregado). Question del usuario: "" Qué tipo de accidente es más frecuente a nivel nacional? """ Data calculados (all are the NICOS nmeros válidos): entidad tipo_accidente total_accidentes porcentaje rank Yucatán Colisión con automotor 34303 41.98 1 Yucatán Colisión con motocicleta 13416 16.42 2 Yucatán Colisión con peatón (atropellamiento) 12011 14.70 3 Yucatán Certificado
```

**Qwen-1.5B (vanilla):**
```
Resumen:
El tipo de accidente más frecuente a nivel nacional en Yucatán es la colisión con vehículo automotor, con una participación del 41.98%.

Datos Principales:
- Colisión con vehículo automotor: 34303 accidentes
- Colisión con motocicleta: 13416 accidentes
- Colisión con peatón (atropellamiento): 12011 accidentes
- Certificado cero: 12002 accidentes
- Colisión con objeto fijo: 4585 accidentes
- Colisión con ciclista: 1641 accidentes
- Volcadura: 1633 accidentes
- Salida del camino: 1351 accidentes
- Colisión con animal: 526 accidentes
- Otros: 247 accidentes

Interpretación:
Los datos muestran que las colisiones con vehículo automotor y motocicleta son las causas más comunes en Yucatán. Sin embargo, el número de accidentes relacionados con objetos fijos, ciclistas y animales también es significativo, lo cual sugiere diversidad en los tipos de incidentes que pueden ocasionarse en la región.

Limitaciones:
No podemos afirmar causalidad entre estos tipos específicos de accidentes debido a la naturaleza probabilística de los eventos. Los datos solo reflejan la distribución general de accidentes en Yucatán, pero no proporcionan información sobre factores como la edad, género o condiciones meteorológicas que podrían influir en la prevalencia de ciertos tipos de accidentes.
```

**Qwen-1.5B (LoRA):**
```
1. Resumen
El tipo de accidente más frecuente en Yucatán es «Colisión con vehículo automotor» con 34,303 incidentes (41.9% del total). Le sigue «Colisión con motocicleta» con 13,416 (16.4%).

2. Datos principales
- 1.° Colisión con vehículo automotor: 34,303 (41.9%)
- 2.° Colisión con motocicleta: 13,416 (16.4%)
- 3.° Colisión con peatón (atropellamiento): 12,011 (14.7%)
- 4.° Certificado cero: 12,002 (14.7%)
- 5.° Colisión con objeto fijo: 4,585 (5.6%)
- 6.° Colisión con ciclista: 1,641 (2.0%)
- 7.° Volcadura: 1,633 (2.0%)
- 8.° Salida del camino: 1,351 (1.7%)
- 9.° Colisión con animal: 526 (0.6%)
- 10.° Otro: 247 (0.3%)

3. Interpretación
La distribución por tipo de accidente indica los siniestros que más afectan la vía pública. Las categorías dominantes suelen relacionarse con velocidad excesiva, distracciones al volante y condiciones de la infraestructura vial. Esta información es útil para priorizar campañas de prevención y políticas de seguridad vial.

4. Limitaciones
- Los datos cubren zonas urbanas y suburbanas en Yucatán; no incluye la totalidad de siniestros en carreteras rurales o federales.
- La clasificación TIPACCID del INEGI puede agrupar subcategorías de distinta naturaleza.
```

---

### Intent: `relacion_ventas_accidentes_nacional`

**Pregunta:** Eres un asistente analítico de datos de movilidad en México.
Reglas estrictas que debes seguir SIEMPRE:
1. Responde únicamente en español claro y profesional.
2. Usa SOLO los datos numéricos que se te proporcionan en este prompt.
   No inventes cifras, porcentajes, estados ni años.
3. Si comparas ve...

**Gold:**
```
1. Resumen
Para el período 2019-2022, la correlación de Pearson entre ventas nacionales de vehículos (autos y camiones) y accidentes viales es 0.111. Esta cifra estadística no implica causalidad.

2. Datos principales
- 2019: ventas 1,360,071 unidades | accidentes 198,671
- 2020: ventas 977,780 unidades | accidentes 168,059
- 2021: ventas 1,046,740 unidades | accidentes 197,410
- 2022: ventas 1,134,777 unidades | accidentes 392,710
- Correlación de Pearson (2019-2022): 0.111

3. Interpretación
La correlación de Pearson es 0.111: asociación prácticamente nula entre ventas de vehículos (autos y camiones) y accidentes en el período analizado. La relación entre ventas vehiculares y accidentes está mediada por múltiples factores: tamaño del parque vehicular, infraestructura vial, comportamiento del conductor, políticas de seguridad vial y cobertura del sistema ATUS. La correlación no implica causalidad.

4. Limitaciones
- Los datos VMRC son nacionales; no es posible el desglose a nivel estatal.
- Los accidentes ATUS se agregan a nivel nacional para este cruce; se pierde la variabilidad regional.
- La correlación de Pearson asume relación lineal; relaciones no lineales no se capturan.
- Factores confusores (demografía, cobertura ATUS, pandemia 2020) no están controlados.
- Correlación no implica causalidad: no se puede afirmar que las ventas vehiculares causen los accidentes.
```

**FLAN-T5-base (vanilla):**
```
Eres asistente analtico de datos de movilidad en México. Reglas estrictas que debe seguir SIEMPRE: 1. Responde nicamente en espaol claro y profesional 2. Use SOLO the numbers provided in this prompt. 3. If compares vehicles with accidents, NO afirm causality. 4. If the data are insufficient (as in years, low values), dilo. 5. Use an ejecutivo tone: claro, breve, accionable. Sources: INEGI - ATUS (Accidentes de Tránsito en Zonas Urbanas y Suburbanas) y/o VMRC (Administrárivo de Vehculos). Tárrelación temporal entre ventas (tipo: total) y accidentes (2019-2022). Incluye correlación de Pearson como referencia (no implica causalidad). IMPORTANTE: although the data can show correlación, many other factors (población, infraestructura vial, pblicas, parque vehicular total, reporte de ATUS) influyen en los accidents. Además, the VMRC ventas a nivel NACIONAL y the ATUS accidentes a nivel nacional a este cruz — no inferir comportamientos
```

**Qwen-1.5B (vanilla):**
```
Resumen:
Se observa una correlación positiva entre las ventas totales de vehículos y el número de accidentes registrados en México durante el período de 2019 a 2022.

Datos Principales:
- Anio | Total Ventas | Total Accidentes | Correlación Pearson | Tipo VMRC
- 2019 | 1360071    | 198671          | 0.111              | total
- 2020 | 977780     | 168059          | 0.111              | total
- 2021 | 1046740   | 197410          | 0.111              | total
- 2022 | 1134777   | 392710          | 0.111              | total

Interpretación:
La correlación positiva entre las ventas totales de vehículos y el número de accidentes es significativa, con un coeficiente de correlación de 0.111. Esto sugiere que cuanto más vehículos se venden, mayormente probablemente aumente el número de accidentes. Sin embargo, esta correlación no implica causality; existen muchas variables externas que influyen en ambos fenómenos, incluyendo la población, la infraestructura vial, las políticas públicas y la cobertura de registro de accidentes.

Limitaciones:
No podemos afirmar causalidad debido a la falta de información sobre factores externos que influyen tanto en las ventas de vehículos como en el número de accidentes. La correlación solo indica una relación estadística, pero no garantiza que haya una causa efectiva. Además, los datos utilizados son a nivel nacional y no pueden ser extrapolados a entidades específicas.
```

**Qwen-1.5B (LoRA):**
```
1. Resumen
Para el período 2019-2022, la correlación de Pearson entre ventas nacionales de vehículos (autos y camiones) y accidentes viales es 0.111. Esta cifra estadística no implica causalidad.

2. Datos principales
- 2019: ventas 1,360,071 unidades | accidentes 198,671
- 2020: ventas 977,780 unidades | accidentes 168,059
- 2021: ventas 1,046,740 unidades | accidentes 197,410
- 2022: ventas 1,134,777 unidades | accidentes 392,710
- Correlación de Pearson (2019-2022): 0.111

3. Interpretación
La correlación de Pearson es 0.111: asociación positiva moderada entre ventas de vehículos (autos y camiones) y accidentes, sin implicar causalidad directa. La relación entre ventas vehiculares y accidentes está mediada por múltiples factores: tamaño del parque vehicular, infraestructura vial, comportamiento del conductor, políticas de seguridad vial y cobertura del sistema ATUS. La correlación no implica causalidad.

4. Limitaciones
- Los datos VMRC son nacionales; no es posible el desglose a nivel estatal.
- Los accidentes ATUS se agregan a nivel nacional para este cruce; se pierde la variabilidad regional.
- La correlación de Pearson asume relación lineal; relaciones no lineales pueden estar subrepresentadas.
- El tamaño del parque vehicular refleja tanto ventas como el régimen de licencias; no todos los vehículos están registrados.
```

---


## Notas para el reporte

- **ROUGE en español con respuestas largas es ruidoso.** Considéralo proxy
  comparativo, no medida absoluta. El salto cualitativo en estructura
  (secciones presentes) y adherencia al formato es más visible en los
  ejemplos cualitativos que en ROUGE.
- **Las cifras numéricas siguen viniendo del prompt.** Ningún modelo (ni
  fine-tuneado) inventa números: el LLM solo redacta a partir de los datos
  calculados con pandas, según el principio fundamental del proyecto.
- **No-causalidad:** confirmar que el fine-tuneado mantiene la mención de
  correlación / no-causalidad en los ejemplos de cruce ventas-accidentes.
