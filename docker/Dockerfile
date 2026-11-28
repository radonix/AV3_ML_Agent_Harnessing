# Imagem do serviço "app": uv + Python 3.12, OpenCode e Hermes Agent.
# O código do projeto não entra na imagem: ele vem montado em /app (ver docker-compose.yml).
ARG UV_VERSION=0.13.10
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:3.12-slim-bookworm

ARG OPENCODE_VERSION=2.4.1
# Hermes Agent v0.23.4 (tag v0.23.4)
ARG HERMES_COMMIT=8fc0374447313e276f6b9a2764bfc750190c966a
# O usuário precisa ter o mesmo UID/GID do dono do repositório no host
ARG UID=1000
ARG GID=1000

RUN apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates curl git libatomic1 procps xz-utils \
 && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

# Usuário sem root: o run.sh protege dados/ com chmod, o que não vale para o root,
# e o Hermes recusa um HERMES_HOME em que outros usuários possam escrever.
RUN groupadd -o -g "${GID}" agente \
 && useradd -o -m -u "${UID}" -g "${GID}" -s /bin/bash agente \
 && mkdir -p /app /opt/venv \
 && chown agente:agente /app /opt/venv
USER agente
WORKDIR /home/agente

# OpenCode
RUN curl -fsSL https://opencode.ai/v2/install | bash -s -- --version "${OPENCODE_VERSION}" --no-modify-path

# Hermes Agent + plugin do Groq (no HERMES_HOME do projeto)
RUN curl -fsSL https://hermes-agent.nousresearch.com/install.sh \
      | bash -s -- --non-interactive --skip-browser --skip-computer-use --commit "${HERMES_COMMIT}"
RUN mkdir -m 700 /home/agente/.hermes-av3 \
 && HERMES_HOME=/home/agente/.hermes-av3 /home/agente/.local/bin/hermes plugins install groq-provider

# Dependências do projeto com uv. O venv fica fora de /app para o volume não escondê-lo.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
COPY --chown=agente:agente pyproject.toml uv.lock .python-version /tmp/projeto/
RUN cd /tmp/projeto && uv sync --frozen --no-cache

# O "python3" que os agentes chamam é o do ambiente do uv
ENV VIRTUAL_ENV=/opt/venv \
    HERMES_HOME_AV3=/home/agente/.hermes-av3 \
    PATH=/opt/venv/bin:/home/agente/.opencode/bin:/home/agente/.local/bin:/usr/local/bin:/usr/bin:/bin

# Um shell de login (bash -l) redefine o PATH em /etc/profile e perderia o venv (e o pandas)
USER root
RUN echo 'export PATH="/opt/venv/bin:$PATH"' > /etc/profile.d/venv.sh
USER agente

COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh
WORKDIR /app
ENTRYPOINT ["entrypoint.sh"]
