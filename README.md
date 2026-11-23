# 🤖 Bot de Control de Gastos Personales en Telegram con IA

Asistente conversacional desarrollado en **Python** para Telegram que permite registrar, consultar y gestionar gastos personales en lenguaje natural (pesos colombianos — **COP**), utilizando **Google Gemini** para la extracción estructurada de datos y **Supabase (PostgreSQL)** como base de datos en la nube multiusuario.

---

## 📋 Características Principales

* **Procesamiento de Lenguaje Natural (NLP):** Interpreta mensajes cotidianos como *"Gasté 15.000 en almuerzo"* o *"Pagué 8.500 de transporte"* sin necesidad de comandos rígidos, extrayendo automáticamente el **monto**, la **moneda**, la **categoría** y una **descripción** limpia.
* **Arquitectura Multiusuario Aislada:** Cualquier usuario de Telegram puede interactuar libremente con el bot; cada registro queda asociado y filtrado por su `telegram_user_id` en la nube, garantizando privacidad entre usuarios.
* **Alta Disponibilidad de IA (Fallback Automático):** Configurado con un modelo principal (`gemini-3.5-flash-lite`) y un modelo de respaldo (`gemini-2.5-flash`) con reintentos automáticos ante picos de saturación (`503`).
* **Persistencia en la Nube:** Almacenamiento en tiempo real en **Supabase (PostgreSQL)** con manejo de zona horaria local (`America/Bogota`) para reportes mensuales exactos.
* **Gestión Rápida de Registros:** Soporte para reportes agrupados por categoría, eliminación del último gasto registrado (`/borrar`) y botón interactivo **Deshacer** tras cada registro.

---

## 🧠 Uso de Inteligencia Artificial (En el Producto y en el Desarrollo)

El uso de Inteligencia Artificial Gemini 4 carbon en este proyecto abarca dos frentes claros:

### 1. En el funcionamiento del Chatbot (Google Gemini API)
* **Comprensión y Clasificación Semántica:** En `ai_service.py`, el modelo **Gemini (`gemini-3.5-flash-lite` / `gemini-2.5-flash`)** actúa como el motor de interpretación del lenguaje natural del usuario, distinguiendo si un mensaje es el registro de un gasto o una conversación cotidiana.
* **Extracción Estructurada (JSON):** Transforma frases libres y ambiguas (ej. *"me gasté 12 barras en un corrientazo"* o *"pagué 5.000 de mototaxi"*) en un objeto JSON estricto con los campos `es_gasto`, `monto`, `moneda`, `categoria` y `descripcion`, permitiendo almacenarlo directamente en PostgreSQL sin reglas rígidas de expresiones regulares.
* **Asistencia Conversacional:** Cuando el usuario saluda o hace preguntas fuera del registro financiero, Gemini genera respuestas contextuales y amables sin alterar la base de datos.

### 2. En el proceso de Ingeniería y Desarrollo
* **Diseño Modular y Arquitectura:** Apoyo en la estructuración del proyecto bajo separación de responsabilidades (`main.py`, `ai_service.py`, `database.py`) para desacoplar la interfaz de Telegram, la lógica de IA y la persistencia de datos.
* **Migración de Base de Datos (SQLite a Supabase):** Asistencia en la refactorización de consultas locales hacia el cliente oficial de Supabase (PostgreSQL en la nube), implementando filtros por `telegram_user_id` y manejo de zona horaria `America/Bogota`.
* **Depuración y Resiliencia:** Diagnóstico y resolución de excepciones de red, errores de disponibilidad temporal de modelos (`503`), validación de esquemas JSON y prevención de conflictos de *polling* (`getUpdates`).

---

## 🏗️ Arquitectura del Proyecto

El código está dividido bajo el principio de **separación de responsabilidades** en tres módulos principales:

```text
chat-bot/
├── main.py             # Punto de entrada: handlers de Telegram, comandos, botones y flujo principal
├── ai_service.py       # Capa de IA: comunicación con Google Gemini, validación JSON y respaldo de modelos
├── database.py         # Capa de datos: conexión y consultas CRUD a Supabase (PostgreSQL)
├── requirements.txt    # Dependencias del proyecto
├── .env                # Variables de entorno y credenciales privadas (excluido en .gitignore)
├── .gitignore          # Archivos y carpetas ignorados por Git
└── README.md           # Documentación del proyecto
```

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Lenguaje** | Python 3.11+ | Lógica principal del bot y manejo asíncrono |
| **Interfaz de Mensajería** | `python-telegram-bot` (v21+) | Recepción de mensajes (Polling), comandos y botones inline |
| **Inteligencia Artificial** | `google-genai` (Gemini API) | Extracción estructurada (JSON) de gastos y respuesta conversacional |
| **Base de Datos en la Nube** | `supabase` (PostgreSQL) | Almacenamiento persistente y consultas filtradas por usuario |
| **Configuración y Tiempo** | `python-dotenv`, `tzdata` | Gestión segura de credenciales y zona horaria `America/Bogota` |

---

## 🗄️ Estructura de la Base de Datos (Supabase)

El sistema utiliza una tabla principal llamada **`gastos`** en PostgreSQL:

| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | `bigint` (PK, Identity) | Identificador único autoincremental del gasto |
| `telegram_user_id` | `bigint` (Indexado) | ID único del usuario en Telegram que registró el gasto |
| `monto` | `numeric` | Valor numérico del gasto registrado |
| `categoria` | `text` | Categoría asignada por la IA (ej. *Alimentación*, *Transporte*, *Salud*) |
| `descripcion` | `text` | Detalle corto del gasto extraído del mensaje |
| `fecha_registro` | `timestamptz` | Marca de tiempo UTC generada automáticamente al insertar |

---

## 💬 Comandos y Uso del Bot

| Acción / Comando | Descripción |
| :--- | :--- |
| `/start` | Inicia la conversación y muestra la bienvenida e instrucciones de uso |
| `/ayuda` | Muestra ejemplos de mensajes válidos y la lista de comandos disponibles |
| `/reporte` | Genera un resumen de los gastos del mes actual agrupados por categoría |
| `/borrar` | Elimina el último gasto registrado por el usuario |
| **Mensaje libre (Gasto)** | Ej: *"Compré un café en 4.500"* → La IA extrae los datos, lo guarda en Supabase y ofrece un botón **Deshacer** |
| **Mensaje libre (Charla)** | Ej: *"Hola, ¿cómo estás?"* → El bot responde de forma conversacional sin alterar la base de datos |

---

## ⚙️ Instalación y Ejecución Local

### 1. Clonar el repositorio
```bash
git clone <URL_DE_TU_REPOSITORIO>
cd chat-bot
```

### 2. Crear y activar el entorno virtual
En **Windows (PowerShell)**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

En **Linux / macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crea un archivo llamado `.env` en la raíz del proyecto con las siguientes variables:

```env
TELEGRAM_TOKEN=tu_token_de_botfather
GEMINI_API_KEY=tu_api_key_de_google_ai_studio
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_MODEL_RESPALDO=gemini-2.5-flash
SUPABASE_URL=[https://tu-proyecto.supabase.co](https://tu-proyecto.supabase.co)
SUPABASE_KEY=tu_clave_service_role_de_supabase
```

### 5. Ejecutar el bot
```bash
python main.py
```

---

## 🔒 Seguridad y Buenas Prácticas

* Las credenciales (`TELEGRAM_TOKEN`, `GEMINI_API_KEY`, `SUPABASE_KEY`) nunca se almacenan en el código fuente; se cargan dinámicamente mediante `python-dotenv` y el archivo `.env` está bloqueado en `.gitignore`.
* Cada consulta de lectura o eliminación en `database.py` exige coincidencia con el `telegram_user_id` del remitente, evitando que un usuario pueda ver o borrar registros de otro.
* Para despliegues en la nube (Railway / Render), el servicio debe ejecutarse como una única instancia (*worker* con `python main.py`) para evitar conflictos de *polling* (`getUpdates`) en la API de Telegram.
