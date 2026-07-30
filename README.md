# Flexit Watcher — avisos de ofertas en Arica y Parinacota

Este programa revisa `flexit.cl/trabajar` entre las 08:00 y las 21:00
(hora de Chile), en intervalos aleatorios de 8 a 12 minutos, y te manda
una notificación al teléfono (via la app **ntfy**) cuando aparece una
oferta nueva en tu región. Corre gratis en GitHub Actions, sin que tengas
que dejar tu computador encendido.

⚠️ **Importante y honesto:** el sitio de Flexit carga las ofertas de forma
dinámica (JavaScript) después de elegir la región, así que el script usa un
navegador automatizado (Playwright) para simular ese clic y leer el
resultado. No tuve forma de probarlo contra el sitio en vivo desde este
entorno, así que es muy posible que necesites un pequeño ajuste la primera
vez. Por eso el workflow guarda automáticamente una captura de pantalla
(`debug.png`) y el texto de la página (`debug_page_text.txt`) en cada
ejecución — si algo no funciona, mándame esos dos archivos y ajusto el
script contigo.

## Paso 1: Instala la app ntfy en tu teléfono

- Android: busca "ntfy" en Play Store.
- iPhone: busca "ntfy" en App Store.

Abre la app y **suscríbete al tema** (topic):

```
flexit-arica-b8ff4933
```

(Puedes usar ese nombre tal cual, o inventar el tuyo — solo cámbialo también
en el paso 3. Los temas de ntfy son públicos si alguien adivina el nombre,
así que mientras más raro, mejor.)

## Paso 2: Crea un repositorio en GitHub

1. Ve a https://github.com/new
2. Nombre: por ejemplo `flexit-watcher`. Te recomiendo que sea **público**
   (así los minutos de GitHub Actions son ilimitados y gratis) — con el
   nuevo esquema de revisiones cada 8-12 min, un repo privado podría
   superar el límite gratuito mensual.
3. Sube estos archivos manteniendo la carpeta `.github/workflows/` tal
   como está (arrastra el zip descomprimido, o usa git).

## Paso 3: Configura el secreto NTFY_TOPIC

1. En tu repo, ve a **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Nombre: `NTFY_TOPIC`
4. Valor: `flexit-arica-b8ff4933` (o el que hayas elegido en el paso 1)

## Paso 4: Actívalo

1. Ve a la pestaña **Actions** de tu repo.
2. Si aparece un aviso pidiendo habilitar workflows, acéptalo.
3. Entra al workflow "Flexit Watcher" y dale a **Run workflow** para
   probarlo manualmente ahora mismo.
4. Revisa los logs: dice cuántas ofertas encontró y cuántas notificó.
5. Si no detectó ninguna oferta (y tú sabes que sí había, como en tu
   captura), descarga el artifact "debug-evidence" de esa ejecución y
   compárteme el `debug_page_text.txt` — con eso ajusto el patrón de
   lectura en minutos.

## Horario y frecuencia

Para no generar tráfico sospechoso ni arriesgarse a un bloqueo de IP, el
programa ahora:

- **Solo actúa entre las 08:00 y las 21:00, hora de Chile continental**
  (la misma que Arica). Fuera de ese rango no hace ninguna petición al
  sitio.
- **No revisa cada X minutos exactos.** Cada vez que revisa, decide al
  azar cuándo será la próxima vez (entre 8 y 12 minutos después), así que
  el patrón de tráfico no es perfectamente regular.

Por dentro: el workflow se dispara cada 5 minutos, pero la mayoría de esas
veces un script muy liviano (`scheduler_gate.py`, sin navegador ni
Playwright) revisa la hora y el archivo `next_run.json`, y si "todavía no
toca", termina ahí mismo en segundos sin costo real. Solo cuando
corresponde de verdad, se instala el navegador y se hace la revisión
completa.

Si quieres cambiar la ventana horaria o el rango de minutos, edita estas
líneas en `scheduler_gate.py`:

```python
HORA_INICIO = 8
HORA_FIN = 21
MIN_INTERVALO_MIN = 8
MAX_INTERVALO_MIN = 12
```

**Nota sobre minutos gratis de GitHub Actions:** con este esquema, durante
las 13 horas activas al día puede haber entre ~65 y ~100 revisiones reales
(cada una de 1-2 min). Si tu repo es **privado**, es posible que superes
los ~2000 minutos gratis al mes. Te recomiendo que el repo sea
**público** — ahí los minutos de Actions son ilimitados y gratis.

## Notificación de verificación

Además de avisarte cuando aparece una oferta nueva, en **cada corrida** el
script te manda una notificación de estado ("✅ Verificación Flexit
Watcher") con el total de ofertas visibles y cuál es la más reciente
(según su fecha de inicio). Sirve para confirmar de un vistazo que el
script sigue leyendo datos actuales del sitio.

Ojo: esto significa una notificación extra cada 8-12 min durante el
horario activo (8:00-21:00), no solo cuando hay algo nuevo. Si más
adelante te resulta molesta, dime y la quito o la hacemos menos frecuente.

## ¿Por qué no se repiten los avisos?

El script guarda un identificador de cada oferta ya notificada en
`seen_jobs.json`, y ese archivo se actualiza solo en el repo después de
cada corrida. Si quieres "reiniciar" y que te vuelva a avisar de todo lo
que esté publicado ahora mismo, borra el contenido de ese archivo y déjalo
como `[]`.
