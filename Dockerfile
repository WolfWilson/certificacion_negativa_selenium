###############################################################################
# Certificación Negativa – Contenedor GUI (Xvfb) + FreeTDS + Python 3.9
# Base Debian Buster con OpenSSL 1.1.1              (compatible SQL 2008 R2)
###############################################################################
FROM python:3.9-buster

WORKDIR /app
# ── 1. Paquetes de sistema ──────────────────────────────────────────────
#     (cambiamos http → https para evitar 403)
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' \
        /etc/apt/sources.list && \
    sed -i 's|http://security.debian.org|https://security.debian.org|g' \
        /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        xvfb fluxbox x11vnc net-tools ca-certificates curl gnupg \
        unixodbc unixodbc-dev freetds-dev tdsodbc freetds-bin \
        chromium chromium-driver supervisor && \
    update-ca-certificates --fresh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
# ── 2. FreeTDS → freetds.conf + odbcinst.ini ────────────────────────────────
# ── 1. Paquetes gráficos + red ──────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        xvfb fluxbox x11vnc net-tools ca-certificates curl gnupg \
        unixodbc unixodbc-dev freetds-dev tdsodbc freetds-bin chromium chromium-driver \
        supervisor && \
    update-ca-certificates --fresh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ── 2. FreeTDS → freetds.conf + odbcinst.ini ────────────────────────────────
#     El host se inyectará vía ARG para poder cambiarlo sin re-compilar.
ARG SQL_HOST=128.0.128.200
ARG SQL_PORT=1433
ARG TDS_VER=7.3

RUN echo "[SQL01_SERVER]"              >  /etc/freetds/freetds.conf && \
    echo "    host = ${SQL_HOST}"     >> /etc/freetds/freetds.conf && \
    echo "    port = ${SQL_PORT}"     >> /etc/freetds/freetds.conf && \
    echo "    tds version = ${TDS_VER}" >> /etc/freetds/freetds.conf && \
    echo "    client charset = UTF-8" >> /etc/freetds/freetds.conf

RUN echo "[FreeTDS]"                                    >  /etc/odbcinst.ini && \
    echo "Description = FreeTDS unixODBC Driver"       >> /etc/odbcinst.ini && \
    echo "Driver      = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so" >> /etc/odbcinst.ini && \
    echo "Setup       = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so"    >> /etc/odbcinst.ini && \
    echo "UsageCount  = 1"                              >> /etc/odbcinst.ini

# ── 3. Python deps ──────────────────────────────────────────────────────────
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# ── 4. Copiar código ────────────────────────────────────────────────────────
COPY app/ /app

# ── 5. Supervisor ───────────────────────────────────────────────────────────
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Exponemos puertos de servicios
EXPOSE 5900
#EXPOSE 6080       # (añádelo si luego integras noVNC)

CMD ["/usr/bin/supervisord","-n"]
