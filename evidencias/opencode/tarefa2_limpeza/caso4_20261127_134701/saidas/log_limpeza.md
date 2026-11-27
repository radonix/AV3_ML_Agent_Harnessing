# Log de limpeza dos dados

- Arquivo de entrada: `dados/vendas.csv` (não é alterado)
- Arquivo limpo: `saidas/vendas_limpas.csv`
- Relatório de qualidade usado: `saidas/relatorio_qualidade.md`
- Gerado em: 2026-11-27 13:59
- Gerado por: `limpar_vendas.py` (pandas). Todas as contagens e correções vêm do código.

## Resultado

| Contagem | Linhas |
| --- | ---: |
| Antes (linhas de dados na entrada) | 500 |
| Removidas | 0 |
| Depois (linhas em `vendas_limpas.csv`) | 500 |
| Alteradas (mantidas com algum valor corrigido) | 0 |
| Mantidas com observação para revisão humana | 0 |

Conferência: 500 − 0 = 500 ✅

## 1. Regras aplicadas

- **R1 Espaços:** espaços nas pontas e repetidos são removidos de todas as células.
- **R2 Duplicatas exatas:** linhas idênticas em todas as colunas (após R1); fica a primeira.
- **R3 Datas:** formato final `AAAA-MM-DD`. `DD/MM/AAAA` é convertido (ordem deduzida da própria coluna, como na Tarefa 1). Data vazia, inexistente ou ilegível: **linha removida**, porque não há como saber o mês da venda.
- **R4 Números:** ponto como separador decimal; `quantidade` inteira; `preco_unitario` e `valor_total` com 2 casas. `R$`, vírgula decimal e separador de milhar são convertidos.
- **R5 Nulos numéricos:** se falta só um entre `quantidade`, `preco_unitario` e `valor_total`, ele é recomposto pela conta exata (`valor_total = quantidade × preco_unitario`; `quantidade = valor_total ÷ preco_unitario` só se o resultado for inteiro). Se faltam dois ou três: **linha removida**.
- **R6 valor_total divergente** de `quantidade × preco_unitario` (tolerância 0.02): `valor_total` é **recalculado**; quantidade e preço são tratados como a fonte.
- **R7 Negativos:** `quantidade` negativa com preço positivo é **devolução** e é mantida (com `valor_total` negativo). `preco_unitario` negativo ou zero, `quantidade` zero ou não inteira são **erro**: linha removida.
- **R8 Texto vazio** (`pedido_id`, `produto`, `categoria`, `regiao`, `vendedor`): preenchido com `Não informado`. A venda é mantida porque a receita existe; o valor não é inventado.
- **R9 Padronização:** `regiao` vira a sigla da UF (tabela abaixo). Em `produto`, `categoria` e `vendedor`, variantes que só diferem em maiúsculas, acentos ou espaços viram a forma mais frequente.
- **R10 Duplicata após padronização:** linhas que ficam idênticas depois de R1–R9; fica a primeira.
- **R11 Revisão humana:** quantidade ou preço atípico (fora de 3×IQR) e `pedido_id` repetido com conteúdo diferente **não são alterados nem removidos**; ficam listados na seção 8 para revisão.

## 2. Remoções por motivo

Nenhuma linha removida.

## 3. Alterações por tipo

Nenhuma linha alterada.

## 4. Tabela de equivalência aplicada

Nenhuma grafia precisou ser padronizada.

Equivalência de regiões usada: sigla ou nome do estado, sem diferença de maiúsculas, acentos ou espaços → sigla da UF (ex.: `São Paulo`, `sao paulo`, ` sp ` → `SP`).

## 5. Problemas do relatório de qualidade (Tarefa 1) e tratamento

O relatório da Tarefa 1 não lista problemas.

As contagens desta limpeza (seções 2 e 3) podem ser maiores que as da Tarefa 1: duplicatas e grafias que só aparecem depois de padronizar não são vistas lá.

## 6. Linhas removidas

Nenhuma.

## 7. Linhas alteradas

Nenhuma.

## 8. Linhas mantidas com observação (revisão humana)

Nenhuma.

## Contagens para verificação automática

Lidas por `scripts/verificar_limpeza.py`, que confere cada número com os arquivos.

```json
{"linhas_antes": 500, "removidas": 0, "linhas_depois": 500, "alteradas": 0, "com_observacao": 0, "remocoes_por_motivo": {}, "alteracoes_por_tipo": {}, "linhas_removidas": [], "linhas_alteradas": []}
```
