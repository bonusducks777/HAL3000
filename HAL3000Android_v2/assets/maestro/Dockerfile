FROM eclipse-temurin:17-jre

ARG MAESTRO_VERSION=1.41.0

# Install ADB and Maestro dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates adb unzip wget && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Use non-root user
RUN useradd -m -s /bin/bash --create-home mobile-use && \
    chown -R mobile-use:mobile-use /opt/ && \
    mkdir -p /home/mobile-use/.android && \
    chown -R mobile-use:mobile-use /home/mobile-use/.android
USER mobile-use

# Download & install Maestro
RUN mkdir -p /opt/maestro && \
    wget -q -O /tmp/${MAESTRO_VERSION} "https://github.com/mobile-dev-inc/maestro/releases/download/cli-${MAESTRO_VERSION}/maestro.zip" && \
    unzip -q /tmp/${MAESTRO_VERSION} -d /opt/ && \
    rm /tmp/${MAESTRO_VERSION}
ENV PATH="/opt/maestro/bin:${PATH}"

COPY --chown=mobile-use:mobile-use docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
