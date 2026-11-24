"""Agente genérico (laço de agente + ferramentas). Cada tarefa só passa uma Config."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

RAIZ = Path(__file__).resolve().parents[1]
MODELO = "openai/gpt-oss-20b"


@dataclass
class Config:
    nome: str                    # nome da pasta de evidências, ex.: "tarefa1_validacao"
    system_prompt: str
    tarefa: str                  # instrução enviada ao agente
    leitura: tuple = ("dados",)  # pastas que o agente pode ler (head -n 5)
    escrita: bool = True         # False = o agente não recebe a ferramenta write_file
    max_loops: int = 8


def carregar_env(raiz=RAIZ):
    """Lê GROQ_API_KEY do arquivo .env (funciona em qualquer shell)."""
    arquivo = Path(raiz) / ".env"
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.startswith("#"):
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(), valor.strip().strip("'\""))


def hash_pasta(pasta: Path) -> dict:
    return {str(p.relative_to(pasta)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(pasta.rglob("*")) if p.is_file()} if pasta.exists() else {}


class AgentHarness:
    def __init__(self, cfg: Config, client=None, raiz=RAIZ):
        self.cfg = cfg
        self.raiz = Path(raiz).resolve()
        self.client = client or OpenAI(base_url="https://api.groq.com/openai/v1",
                                       api_key=os.environ.get("GROQ_API_KEY"))
        self.messages = [{"role": "system", "content": cfg.system_prompt}]
        self.max_tokens = 3000
        self.prefixos = (["python3 saidas/", "python3 scripts/"]
                         + [f"head -n 5 {p}/" for p in cfg.leitura])
        self.metricas = {"tarefa": cfg.nome, "requisicoes": 0, "tokens_entrada": 0,
                         "tokens_saida": 0, "erros_429": 0, "erros_400_json": 0,
                         "chamadas_ferramenta": 0, "bloqueios": 0, "parada": "concluido",
                         "final": ""}

    # ------------------------------------------------------------------ ferramentas
    def tools(self):
        lista = [
            {"type": "function", "function": {
                "name": "write_file",
                "description": "Cria ou sobrescreve um arquivo de texto dentro de saidas/.",
                "parameters": {"type": "object", "properties": {
                    "filepath": {"type": "string", "description": "Ex.: saidas/arquivo.py"},
                    "content": {"type": "string", "description": "Conteúdo do arquivo."}},
                    "required": ["filepath", "content"]}}},
            {"type": "function", "function": {
                "name": "run_command",
                "description": "Executa um comando. Permitidos: " + ", ".join(self.prefixos),
                "parameters": {"type": "object", "properties": {
                    "command": {"type": "string", "description": "Comando a executar."}},
                    "required": ["command"]}}},
        ]
        return lista if self.cfg.escrita else lista[1:]

    def tool_write_file(self, filepath: str, content: str) -> str:
        alvo = (self.raiz / filepath).resolve()
        if not self.cfg.escrita or self.raiz / "saidas" not in alvo.parents:
            self.metricas["bloqueios"] += 1
            return "Erro de segurança: só é permitido gravar dentro de saidas/."
        try:
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(content, encoding="utf-8")
            return f"Arquivo '{filepath}' criado com sucesso."
        except Exception as e:
            return f"Erro ao escrever arquivo: {e}"

    def tool_run_command(self, command: str) -> str:
        if (not command.startswith(tuple(self.prefixos)) or ".." in command
                or any(c in command for c in ";&|<>`$")):
            self.metricas["bloqueios"] += 1
            return "Erro de segurança: comando não permitido."
        if command.startswith("python3 "):
            command = f'"{sys.executable}" ' + command[len("python3 "):]
        try:
            r = subprocess.run(command, shell=True, cwd=self.raiz, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=60)
            return ((r.stdout + r.stderr).strip() or f"(saída vazia; código de saída {r.returncode})")[:1500]
        except Exception as e:
            return str(e)

    # ---------------------------------------------------------------- modelo (Groq)
    def chamar_modelo(self):
        falhas_json = 0
        for tentativa in range(5):
            try:
                return self.client.chat.completions.create(
                    model=MODELO, messages=self.messages, tools=self.tools(),
                    tool_choice="auto", max_completion_tokens=self.max_tokens,
                    extra_body={"reasoning_effort": "low"})
            except Exception as e:
                status = getattr(e, "status_code", None)
                texto = str(e)
                if status == 429 and tentativa < 4:
                    self.metricas["erros_429"] += 1
                    espera = 30
                    headers = getattr(getattr(e, "response", None), "headers", None) or {}
                    try:
                        espera = float(headers.get("retry-after", 30)) + 1
                    except (TypeError, ValueError):
                        pass
                    print(f"Limite do Groq (429). Esperando {espera:.0f}s...")
                    time.sleep(espera)
                    continue
                if status == 400 and "tool call" in texto.lower() and falhas_json < 2:
                    # o modelo gerou JSON inválido numa chamada de ferramenta
                    falhas_json += 1
                    self.metricas["erros_400_json"] += 1
                    print("JSON de ferramenta inválido. Pedindo para tentar de novo.")
                    self.messages.append({"role": "user", "content":
                        "ERRO: sua última chamada de ferramenta tinha JSON inválido. "
                        "Tente de novo com arquivos menores e sem barras invertidas desnecessárias."})
                    continue
                raise

    # ------------------------------------------------------------------------ laço
    def execute_step(self, user_prompt: str):
        m = self.metricas
        self.messages.append({"role": "user", "content": user_prompt})
        for ciclo in range(1, self.cfg.max_loops + 1):
            print(f"\n--- [Ciclo de Execução {ciclo}] ---")
            response = self.chamar_modelo()
            choice = response.choices[0]
            message = choice.message
            m["requisicoes"] += 1
            m["tokens_entrada"] += response.usage.prompt_tokens
            m["tokens_saida"] += response.usage.completion_tokens
            print(f"[Tokens] entrada={response.usage.prompt_tokens} "
                  f"saida={response.usage.completion_tokens}")

            if choice.finish_reason == "length" and not (message.content or message.tool_calls):
                self.max_tokens = min(self.max_tokens * 2, 8000)
                print(f"Resposta cortada. Aumentando o limite de saída para {self.max_tokens}.")
                continue

            msg = {"role": "assistant", "content": message.content or ""}
            if message.tool_calls:
                msg["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message.tool_calls]
            self.messages.append(msg)
            if message.content:
                print(f"Agente: {message.content}")
            if not message.tool_calls:
                m["final"] = message.content or ""
                return

            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                m["chamadas_ferramenta"] += 1
                print(f"[Tool Call] {tc.function.name} {str(args)[:150]}")
                if tc.function.name == "write_file":
                    saida = self.tool_write_file(args.get("filepath", ""), args.get("content", ""))
                elif tc.function.name == "run_command":
                    saida = self.tool_run_command(args.get("command", ""))
                else:
                    saida = f"Erro: ferramenta {tc.function.name} desconhecida."
                print(f"[Tool Output]\n{saida}")
                self.messages.append({"role": "tool", "tool_call_id": tc.id, "content": saida})
        m["parada"] = f"limite de {self.cfg.max_loops} ciclos"

    def executar(self, execucao: str = "exec01") -> dict:
        """Roda a tarefa e grava evidencias/<tarefa>/<execucao>/."""
        antes = hash_pasta(self.raiz / "dados")
        inicio = time.time()
        try:
            self.execute_step(self.cfg.tarefa)
        except Exception as e:
            self.metricas["parada"] = f"erro: {type(e).__name__}: {str(e)[:200]}"
        self.metricas["duracao_s"] = round(time.time() - inicio, 1)
        self.metricas["dados_intactos"] = hash_pasta(self.raiz / "dados") == antes
        pasta = self.raiz / "evidencias" / self.cfg.nome / execucao
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "metricas.json").write_text(
            json.dumps(self.metricas, ensure_ascii=False, indent=2), encoding="utf-8")
        (pasta / "conversa.json").write_text(
            json.dumps(self.messages, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n=== RESUMO ===")
        print(json.dumps({k: v for k, v in self.metricas.items() if k != "final"},
                         ensure_ascii=False, indent=2))
        print(f"Evidências em evidencias/{self.cfg.nome}/{execucao}")
        return self.metricas


def main(cfg: Config):
    ap = argparse.ArgumentParser()
    ap.add_argument("--exec", dest="execucao", default="exec01",
                    help="nome da execução, usado na pasta de evidências")
    ap.add_argument("--prompt", help="substitui a tarefa (testes de segurança)")
    a = ap.parse_args()
    if a.prompt:
        cfg.tarefa = a.prompt
    carregar_env()
    if not os.environ.get("GROQ_API_KEY"):
        sys.exit("ERRO: defina GROQ_API_KEY no arquivo .env")
    AgentHarness(cfg).executar(a.execucao)
