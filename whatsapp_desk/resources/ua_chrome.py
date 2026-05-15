"""User-Agent de Chrome para evadir el bloqueo de WhatsApp Web.

WhatsApp Web realiza sniffing del User-Agent y bloquea navegadores
que no sean Chrome, Firefox o Edge. Usamos un UA de Chrome reciente.
Actualizado: 2026-05-15
"""

CHROME_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
