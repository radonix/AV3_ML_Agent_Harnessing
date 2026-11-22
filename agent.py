import os
import json
from openai import OpenAI

class AgentHarness:
    def __init__(self, system_prompt: str):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY")
        )
        self.messages = [{"role": "system", "content": system_prompt}]
        self.max_loops = 5

    def execute_step(self, user_prompt: str):
        self.messages.append({"role": "user", "content": user_prompt})
        
        loop_count = 0
        while loop_count < self.max_loops:
            loop_count += 1
            print(f"\n--- [Ciclo de Execução {loop_count}] ---")
            
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=self.messages,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "description": "Cria ou sobrescreve um arquivo de texto/código com o conteúdo fornecido de forma segura (UTF-8).",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "filepath": {"type": "string", "description": "Nome ou caminho do arquivo a ser criado."},
                                    "content": {"type": "string", "description": "Conteúdo exato a ser gravado no arquivo."}
                                },
                                "required": ["filepath", "content"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "run_bash_command",
                            "description": "Executa um comando seguro no ambiente do Windows.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string", "description": "Comando bash/cmd a executar"}
                                },
                                "required": ["command"]
                            }
                        }
                    }
                ],
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            self.messages.append(message.model_dump(exclude_unset=True))
            
            if message.content:
                print(f"Agente: {message.content}")
                
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    print(f"[Tool Call] Acionando {func_name} com argumentos: {func_args}")
                    
                    # Direciona para a ferramenta correta
                    if func_name == "write_file":
                        tool_output = self.tool_write_file(func_args.get("filepath"), func_args.get("content"))
                    elif func_name == "run_bash_command":
                        tool_output = self.tool_run_command(func_args.get("command"))
                    else:
                        tool_output = f"Erro: Ferramenta {func_name} desconhecida."
                        
                    print(f"[Tool Output]\n{tool_output}")
                    
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_output
                    })
            else:
                break

    def tool_write_file(self, filepath: str, content: str) -> str:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Arquivo '{filepath}' criado com sucesso."
        except Exception as e:
            return f"Erro ao escrever arquivo: {str(e)}"

    def tool_run_command(self, command: str) -> str:
        import subprocess
        try:
            if "rmdir /s /q C:\\" in command or "format C:" in command:
                return "Erro de Segurança: Comando bloqueado pelo isolamento operacional."
            
            result = subprocess.run(
                ["cmd.exe", "/c", command], 
                capture_output=True, 
                text=True, 
                encoding="utf-8", 
                errors="replace",
                timeout=10
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return output.strip() if output else "Comando executado com sucesso."
        except Exception as e:
            return str(e)

if __name__ == "__main__":
    system_prompt = (
        "Você é um engenheiro de software autônomo sênior operando no Windows. "
        "Sempre que precisar criar arquivos de código, utilize preferencialmente a ferramenta 'write_file' "
        "para evitar problemas de escape de aspas no terminal."
    )
    harness = AgentHarness(system_prompt)
    harness.execute_step("Crie um arquivo chamado 'ola.py' que imprima 'Olá do Agente Autônomo!' e execute-o usando python.")