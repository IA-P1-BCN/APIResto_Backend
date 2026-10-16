# Evaluación y Selección de Modelos Gratuitos

## 1. Objetivo y Justificación del Requisito
En cumplimiento con el requisito del proyecto de utilizar **soluciones de IA gratuitas**, se ha llevado a cabo un análisis comparativo entre dos de los modelos de lenguaje (LLMs) gratuitos integrados de forma nativa en OpenCode: **MiMo-V2.6-Flash** y **DeepSeek V4.1 Flash**.

El propósito de esta evaluación es determinar cuál de las dos opciones ofrece el mejor equilibrio entre calidad del código, velocidad de respuesta y tasa de errores para el desarrollo de las tareas de nuestro proyecto.

## 2. Metodología de Pruebas
Para garantizar una evaluación justa y objetiva, se sometió a ambos modelos a las mismas condiciones de prueba dentro del entorno de desarrollo OpenCode:

* **Casos de prueba:** Se ejecutaron un conjunto de instrucciones representativas del proyecto (refactorización, corrección de errores, generación de algoritmos y documentación).
* **Parámetros de evaluación:**
  1. **Calidad del Código:** Precisión sintáctica, cumplimiento de buenas prácticas y corrección lógica al primer intento.
  2. **Velocidad (Latencia):** Tiempo medio de respuesta y generación del código.
  3. **Tasa de Errores y Alucinaciones:** Frecuencia de fallos en el formato, sintaxis no válida o código incompleto.

---

## 3. Tabla Comparativa de Resultados

| Métrica / Criterio | MiMo-V2.6-Flash | DeepSeek V4.1 Flash |
| :--- | :--- | :--- |
| **Calidad de la respuesta** | Buena (Respuestas directas y funcionales) | Excelente (Mayor atención a la estructura y casos borde) |
| **Tiempo de respuesta (Latencia)** | Ultrarrápido (~0.8 - 1.2 segundos) | Rápido (~1.5 - 2.5 segundos) |
| **Tasa de errores / Alucinaciones** | Baja (Fallos en algoritmos muy complejos) | Muy baja (Excelente precisión sintáctica) |
| **Integración y Gratuidad** | Gratis en OpenCode (sin API Key) | Gratis en OpenCode (sin API Key) |

---

## 4. Análisis de Resultados

* **MiMo-V2.6-Flash:** Destaca principalmente por su **extrema velocidad de generación**, lo que permite una iteración fluida y rápida durante la escritura de código sencillo o consultas rápidas de sintaxis.
* **DeepSeek V4.1 Flash:** Sobresale por su **capacidad de razonamiento técnico y generación de código limpio y estructurado**, minimizando la necesidad de correcciones manuales en tareas de mayor complejidad.

---

## 5. Conclusión y Selección Final

Tras evaluar ambas alternativas, el equipo ha determinado que **DeepSeek V4.1 Flash** es el modelo principal seleccionado para el desarrollo del proyecto debido a su superior precisión lógica, utilizando **MiMo-V2.6-Flash** como alternativa para iteraciones rápidas. 

Esta decisión cumple rigurosamente con el requisito de utilizar herramientas 100% gratuitas dentro del ecosistema OpenCode.