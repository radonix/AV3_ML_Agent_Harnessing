# AV3 — Agent Harness Engineering

Agentes em sequência para gerar relatórios de vendas (a saída de um é a entrada do próximo), executados e comparados em duas plataformas, **OpenCode** e **Hermes Agent**, com o modelo `qwen3:8b` rodando localmente no **Ollama** (padrão). O `openai/gpt-oss-20b` no GroqCloud continua disponível como opção. Em todas as tarefas, o modelo só coordena: contagens e correções vêm de scripts em pandas.

## Estrutura
- `AGENTS.md`: regras gerais dos agentes.
- `prompts/<tarefa>_plataformas.md`: instrução de cada tarefa, igual nas duas plataformas.
- `casos/<tarefa>.txt`: casos de teste de cada tarefa (preparo e arquivos esperados).
- `opencode.json`: modelo e permissões do OpenCode (negação por padrão).
- `hermes/config.yaml` e `scripts/guarda_hermes.py`: configuração do Hermes e guarda de comandos (lista de permissão). O bloco do modelo vem de `hermes/modelo_<provedor>.yaml`.
- `pyproject.toml`, `uv.lock` e `.python-version`: Python 3.12 e dependências, gerenciados pelo uv.
- `docker/` e `docker-compose*.yml`: execução em containers.
- `scripts/`: scripts das tarefas, gerador de dados de teste, coleta de métricas e testes.
- `gabaritos/`: resultado esperado da limpeza (Tarefa 2) em cada caso.
- `dados/`: planilha de entrada, somente leitura durante as execuções. `saidas/`: tudo que os agentes produzem.
- `evidencias/<plataforma>/<tarefa>/<caso>_<data>/` e `evidencias/resumos/`: registros de cada execução.
- `docs/`: documentação por tarefa.

## Casos de teste
A mesma numeração vale para todas as tarefas:

| Caso | Situação |
| --- | --- |
| `caso1` | Duplicatas e datas inválidas |
| `caso2` | Vários problemas nos dados |
| `caso3` | Arquivo vazio |
| `caso4` | Planilha sem erros |

## Rodar com Docker (recomendado)
Dois serviços: `ollama` (modelo) e `app` (uv, Python 3.12, OpenCode e Hermes). Um terceiro, `ollama-pull`, só baixa o modelo e encerra. Não é preciso instalar Python, OpenCode, Hermes nem Ollama no computador.

> **Situação dos testes:** o build da imagem `app`, as ferramentas dentro dela, os testes da guarda e a simulação (`-n`) foram verificados. Os serviços `ollama` e `ollama-pull`, uma execução com o modelo e o uso de GPU **ainda não foram testados**.

### Requisitos
- Docker com Compose v2.
- Pelo menos 10 GB de RAM livres (até 8 GB para o Ollama, mais o `app`). No Docker Desktop, aumente também o limite de memória dele.
- Cerca de 25 GB de disco (estimativa: imagens e modelo).
- No Windows, use o WSL2 e clone o repositório dentro dele.

### Passos
    cp .env.example .env            # opcional com Ollama: sem .env, valem os padrões
    docker compose build
    docker compose run --rm app -t tarefa1_validacao -c caso1     # um teste rápido
    docker compose run --rm app     # todas as tarefas: primeiro no OpenCode, depois no Hermes
    docker compose down             # desliga o Ollama (o modelo continua salvo no volume)

Os argumentos depois de `app` vão para o `run.sh` (`docker compose run --rm app -h` lista as opções). A primeira execução baixa a imagem do Ollama e o modelo, então demora. Em CPU, cada caso pode levar vários minutos; o limite por caso no Hermes é de 600 s.

No Linux, se `id -u` ou `id -g` não for `1000`, defina `HOST_UID` e `HOST_GID` no `.env` antes do build, para os arquivos gerados ficarem com o seu usuário.

### GPU (opcional)
O padrão é CPU. Para usar GPU, descomente **uma** das linhas `COMPOSE_FILE` no `.env`:

| GPU | Arquivo extra | Requisito no host |
| --- | --- | --- |
| NVIDIA | `docker-compose.nvidia.yml` | NVIDIA Container Toolkit |
| AMD | `docker-compose.amd.yml` | Linux com driver `amdgpu` (`/dev/kfd` e `/dev/dri`) |

Também dá para passar na linha de comando: `docker compose -f docker-compose.yml -f docker-compose.nvidia.yml run --rm app`.

### Modelo e memória
| Variável (`.env`) | Padrão | Observação |
| --- | --- | --- |
| `OLLAMA_MODEL` | `qwen3:8b` | Já declarados no `opencode.json`: `qwen3:8b`, `qwen3:4b` e `qwen2.5:7b-instruct`. Outro modelo precisa ser incluído lá |
| `OLLAMA_CONTEXT_LENGTH` | `65536` | O Hermes exige pelo menos 64.000. Se mudar, ajuste também `limit.context` no `opencode.json` |
| `OLLAMA_MEM_LIMIT` | `8g` | Limite de memória do container do Ollama |
| `OLLAMA_KV_CACHE_TYPE` | `q4_0` | Reduz a memória do contexto; `q8_0` usa mais memória e preserva melhor a qualidade |

O consumo do `qwen3:8b` com esse contexto **ainda não foi medido**; a estimativa fica no limite dos 8 GB. Para conferir, com o Ollama no ar: `docker compose exec ollama ollama ps` (mostra o tamanho do modelo e se está em CPU ou GPU) e `docker stats`. Se faltar memória, use `OLLAMA_MODEL=qwen2.5:7b-instruct` ou aumente `OLLAMA_MEM_LIMIT`.

## Rodar sem Docker
Em Linux ou macOS, com o [Ollama](https://ollama.com) instalado. Inicie o servidor com o mesmo contexto usado pelo projeto:

    OLLAMA_CONTEXT_LENGTH=65536 OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q4_0 ollama serve

Se o Ollama já roda como serviço, defina essas variáveis no serviço e reinicie-o. Em outro terminal:

    ollama pull qwen3:8b
    ./setup.sh                      # uv + Python 3.12 (.venv), OpenCode, Hermes + plugin do Groq, .env
    ./run.sh -t tarefa1_validacao -c caso1
    ./run.sh -h                     # todas as opções

## Usar o Groq
Defina `PROVEDOR=groq` e `GROQ_API_KEY` (console.groq.com/keys) no `.env`. O `run.sh` passa a esperar 70 s entre execuções, por causa dos limites do Groq. Com Docker, os serviços do Ollama continuam sendo iniciados; para pular essa etapa:

    docker compose run --rm --no-deps app -t tarefa1_validacao -c caso1

Os documentos em `docs/` e as evidências já versionadas descrevem execuções feitas com o Groq.

## Testes sem o modelo
    uv run python scripts/testar_limpeza.py
    uv run python scripts/testar_guarda.py

Com Docker:

    docker compose run --rm --no-deps --entrypoint python3 app scripts/testar_guarda.py
    docker compose run --rm --no-deps app -n     # simulação: lista o que seria executado

## Regras
O agente só lê `dados/` e `saidas/`, e só grava em `saidas/`. Já o `run.sh`, a cada caso, esvazia `saidas/` e recria a planilha em `dados/`. Nunca versione o `.env`.
