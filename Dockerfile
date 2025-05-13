FROM python:3.12.10-slim
#me recomienda otros tags más recientes por vulnerabilidaden libxm12
# 1. paquetes base
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        xvfb chromium chromium-driver curl ca-certificates gnupg2 && \
    rm -rf /var/lib/apt/lists/*

# 2. clave GPG y repo de Microsoft (forma nueva, apt-key deprecated)
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] \
        https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list

# 3. instalar ODBC 18 + unixODBC + auto update de libxm12
RUN apt-get update && apt-get upgrade -y && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        libxml2 \
        msodbcsql18 \
        unixodbc \
        unixodbc-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
#apt-get upgrade puede aumentar un poco el tamaño de la imagen, pero vale la pena si estás enfocado en seguridad y parches críticos.

# 4. variables de entorno
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV TZ=America/Argentina/Cordoba

# 5. copiar código
WORKDIR /app
COPY app/ /app
RUN pip install --no-cache-dir \
      --trusted-host pypi.org \
      --trusted-host files.pythonhosted.org \
      -r requirements.txt


# 6. entrypoint
CMD ["bash", "-c", "\
      rm -f /tmp/.X99-lock && rm -rf /tmp/chrome_* && \
      Xvfb :99 -screen 0 1366x768x24 & \
      exec python obtener_certificacion_negativa.py"]

