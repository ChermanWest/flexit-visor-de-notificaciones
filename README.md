# Flexit Watcher — avisos de ofertas en Arica y Parinacota

Este programa revisa `flexit.cl/trabajar` cada 30 minutos y te manda una
notificación al teléfono (via la app **ntfy**) cuando aparece una oferta
nueva en tu región. Corre gratis en GitHub Actions, 24/7, sin que tengas
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
2. Nombre: por ejemplo `flexit-watcher`. Puede ser público (así los minutos
   de GitHub Actions son ilimitados y gratis) o privado (tienes ~2000
   minutos gratis al mes, que alcanzan bien con la frecuencia de 30 min).
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

Desde ese momento corre solo cada 30 minutos.

## Cambiar la frecuencia

Edita esta línea en `.github/workflows/check.yml`:

```yaml
- cron: "*/30 * * * *"
```

Por ejemplo `*/15 * * * *` para cada 15 minutos (ojo con el límite de
minutos gratis si el repo es privado).

## Notificación de verificación

Además de avisarte cuando aparece una oferta nueva, en **cada corrida** el
script te manda una notificación de estado ("✅ Verificación Flexit
Watcher") con el total de ofertas visibles y cuál es la más reciente
(según su fecha de inicio). Sirve para confirmar de un vistazo que el
script sigue leyendo datos actuales del sitio.

Ojo: esto significa una notificación extra cada 15-30 min, todo el
tiempo (no solo cuando hay algo nuevo). Si más adelante te resulta
molesta, dime y la quito o la hacemos menos frecuente.

## ¿Por qué no se repiten los avisos?

El script guarda un identificador de cada oferta ya notificada en
`seen_jobs.json`, y ese archivo se actualiza solo en el repo después de
cada corrida. Si quieres "reiniciar" y que te vuelva a avisar de todo lo
que esté publicado ahora mismo, borra el contenido de ese archivo y déjalo
como `[]`.
