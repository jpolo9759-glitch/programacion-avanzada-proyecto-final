# 💰 Bot de Gastos Personales con IA

Bot de Telegram que registra gastos personales a partir de mensajes en lenguaje
natural. Usa **Google Gemini** para extraer monto, moneda y categoría, y guarda
todo en **SQLite**.

> Proyecto final — Programación Avanzada

## ✨ Funcionalidades
- 💬 **Mensaje libre:** "Gasté 25.000 en el almuerzo" → se guarda y se confirma.
- 📊 `/reporte` → gastos del mes actual agrupados por categoría.
- 🗑️ `/borrar` → elimina el último gasto registrado.
- 👋 `/start` → mensaje de bienvenida.

## 🏗️ Arquitectura
| Archivo | Responsabilidad |
|---|---|
| `main.py` | Bot de Telegram: comandos y flujo de mensajes |
| `ai_service.py` | Conexión con Gemini, prompt y validación del JSON |
| `database.py` | Conexión y consultas a SQLite |

## 🚀 Instalación
1. Clonar el repositorio y entrar a la carpeta.
2. Crear y activar el entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Copiar `.env.example` a `.env` y completar:
   ```
   TELEGRAM_TOKEN=tu_token_de_botfather
   GEMINI_API_KEY=tu_api_key_de_gemini
   GEMINI_MODEL=gemini-3.5-flash
   ```
5. Ejecutar:
   ```bash
   python main.py
   ```

## 📱 Uso
Escribe al bot mensajes como:
- `Gasté 25.000 en el almuerzo`
- `Pagué 15 dólares de internet`
- `taxi 12 mil`

## 🤖 Uso de la Inteligencia Artificial
- **Modelo:** Google Gemini, vía el SDK `google-genai`.
- **Tarea:** extracción de información (NLP) de texto libre a JSON estructurado:
  `monto`, `moneda`, `categoria`, `descripcion`.
- **Técnicas:** prompt de sistema con rol y reglas, *few-shot prompting*,
  salida forzada en JSON (`response_mime_type`) y validación posterior en Python.
- **Robustez:** si la IA falla o no entiende, el bot responde con un mensaje
  amable en lugar de caerse.
- **Herramientas de IA en el desarrollo:** (el equipo declara aquí cómo usó
  asistentes de IA para construir el proyecto).

## 🔒 Seguridad
- Claves en `.env` (excluido por `.gitignore`).
- Consultas SQL parametrizadas.
- Datos aislados por `user_id` de Telegram.

