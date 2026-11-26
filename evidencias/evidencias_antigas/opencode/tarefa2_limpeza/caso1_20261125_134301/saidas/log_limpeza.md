# Log de limpeza dos dados

- Arquivo de entrada: `dados/vendas.csv` (não é alterado)
- Arquivo limpo: `saidas/vendas_limpas.csv`
- Relatório de qualidade usado: `saidas/relatorio_qualidade.md`
- Gerado em: 2026-11-25 14:01
- Gerado por: `limpar_vendas.py` (pandas). Todas as contagens e correções vêm do código.

## Resultado

| Contagem | Linhas |
| --- | ---: |
| Antes (linhas de dados na entrada) | 505 |
| Removidas | 8 |
| Depois (linhas em `vendas_limpas.csv`) | 497 |
| Alteradas (mantidas com algum valor corrigido) | 0 |
| Mantidas com observação para revisão humana | 0 |

Conferência: 505 − 8 = 497 ✅

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

| Motivo | Linhas |
| --- | ---: |
| data vazia ou inválida | 3 |
| duplicata exata | 5 |

## 3. Alterações por tipo

Nenhuma linha alterada.

## 4. Tabela de equivalência aplicada

Nenhuma grafia precisou ser padronizada.

Equivalência de regiões usada: sigla ou nome do estado, sem diferença de maiúsculas, acentos ou espaços → sigla da UF (ex.: `São Paulo`, `sao paulo`, ` sp ` → `SP`).

## 5. Problemas do relatório de qualidade (Tarefa 1) e tratamento

| Coluna | Problema na Tarefa 1 | Quantidade | Tratamento nesta limpeza |
| --- | --- | ---: | --- |
| `data` | data inválida | 3 | R3: linha removida |
| `(linha inteira)` | linha duplicada (cópia exata de outra) | 5 | R2: linha removida |

As contagens desta limpeza (seções 2 e 3) podem ser maiores que as da Tarefa 1: duplicatas e grafias que só aparecem depois de padronizar não são vistas lá.

## 6. Linhas removidas

| Linha | pedido_id | Motivo | Detalhe |
| ---: | --- | --- | --- |
| 22 | PED-00021 | data vazia ou inválida | data inexistente ('2026-02-30') |
| 62 | PED-00061 | data vazia ou inválida | data inexistente ('31/04/2026') |
| 92 | PED-00091 | data vazia ou inválida | data ilegível ('abc') |
| 502 | PED-00011 | duplicata exata | igual à linha 12 |
| 503 | PED-00051 | duplicata exata | igual à linha 52 |
| 504 | PED-00101 | duplicata exata | igual à linha 102 |
| 505 | PED-00151 | duplicata exata | igual à linha 152 |
| 506 | PED-00201 | duplicata exata | igual à linha 202 |

## 7. Linhas alteradas

Nenhuma.

## 8. Linhas mantidas com observação (revisão humana)

Nenhuma.

## 9. Avisos

- Datas com barra interpretadas como DD/MM/AAAA.

## Contagens para verificação automática

Lidas por `scripts/verificar_limpeza.py`, que confere cada número com os arquivos.

```json
{"linhas_antes": 505, "removidas": 8, "linhas_depois": 497, "alteradas": 0, "com_observacao": 0, "remocoes_por_motivo": {"data vazia ou inválida": 3, "duplicata exata": 5}, "alteracoes_por_tipo": {}, "linhas_removidas": [22, 62, 92, 502, 503, 504, 505, 506], "linhas_alteradas": []}
```
