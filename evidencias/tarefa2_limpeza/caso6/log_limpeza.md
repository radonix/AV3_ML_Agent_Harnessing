# Log de limpeza dos dados

- Arquivo de entrada: `dados/vendas.csv` (não é alterado)
- Arquivo limpo: `saidas/vendas_limpas.csv`
- Relatório de qualidade usado: `saidas/relatorio_qualidade.md`
- Gerado em: 2026-11-25 01:00
- Gerado por: `limpar_vendas.py` (pandas). Todas as contagens e correções vêm do código.

## Resultado

| Contagem | Linhas |
| --- | ---: |
| Antes (linhas de dados na entrada) | 500 |
| Removidas | 1 |
| Depois (linhas em `vendas_limpas.csv`) | 499 |
| Alteradas (mantidas com algum valor corrigido) | 10 |
| Mantidas com observação para revisão humana | 2 |

Conferência: 500 − 1 = 499 ✅

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
| preco_unitario negativo ou zero (erro) | 1 |

## 3. Alterações por tipo

Uma linha pode ter mais de um tipo de alteração.

| Tipo de alteração | Linhas |
| --- | ---: |
| quantidade vazia deduzida | 2 |
| região convertida para sigla de UF | 6 |
| texto vazio preenchido com 'Não informado' | 2 |
| valor_total divergente recalculado | 2 |

## 4. Tabela de equivalência aplicada

| Coluna | Valor original | Valor padronizado | Linhas |
| --- | --- | --- | ---: |
| `regiao` | 'São Paulo' | 'SP' | 6 |

Equivalência de regiões usada: sigla ou nome do estado, sem diferença de maiúsculas, acentos ou espaços → sigla da UF (ex.: `São Paulo`, `sao paulo`, ` sp ` → `SP`).

## 5. Problemas do relatório de qualidade (Tarefa 1) e tratamento

| Coluna | Problema na Tarefa 1 | Quantidade | Tratamento nesta limpeza |
| --- | --- | ---: | --- |
| `produto` | valor nulo/vazio | 2 | R8: preenchido com 'Não informado' |
| `quantidade` | valor nulo/vazio | 2 | R5: recomposto pela conta ou linha removida |
| `quantidade` | valor negativo | 1 | R7: devolução mantida |
| `preco_unitario` | valor negativo | 1 | R7: linha removida |
| `valor_total` | valor negativo | 2 | R7: segue a linha (devolução mantida ou linha removida) |
| `valor_total` | valor_total diferente de quantidade × preco_unitario | 2 | R6: valor_total recalculado |
| `regiao` | categoria escrita de formas diferentes | 6 | R9: padronizado |

As contagens desta limpeza (seções 2 e 3) podem ser maiores que as da Tarefa 1: duplicatas e grafias que só aparecem depois de padronizar não são vistas lá.

## 6. Linhas removidas

| Linha | pedido_id | Motivo | Detalhe |
| ---: | --- | --- | --- |
| 8 | PED-00007 | preco_unitario negativo ou zero (erro) | preco_unitario = -10 |

## 7. Linhas alteradas

| Linha | pedido_id | Alterações |
| ---: | --- | --- |
| 3 | PED-00002 | produto: '' → 'Não informado' |
| 4 | PED-00003 | produto: '' → 'Não informado'; regiao: 'São Paulo' → 'SP' |
| 5 | PED-00004 | quantidade: vazio → 4 (320÷80) |
| 6 | PED-00005 | quantidade: vazio → 4 (2800÷700) |
| 9 | PED-00008 | valor_total: 1 → 480.00 (6×80); regiao: 'São Paulo' → 'SP' |
| 10 | PED-00009 | valor_total: 2 → 21000.00 (6×3500) |
| 11 | PED-00010 | regiao: 'São Paulo' → 'SP' |
| 13 | PED-00012 | regiao: 'São Paulo' → 'SP' |
| 14 | PED-00013 | regiao: 'São Paulo' → 'SP' |
| 27 | PED-00026 | regiao: 'São Paulo' → 'SP' |

## 8. Linhas mantidas com observação (revisão humana)

| Linha | pedido_id | Observação |
| ---: | --- | --- |
| 7 | PED-00006 | devolução (quantidade negativa), mantida com valor_total negativo |
| 11 | PED-00010 | valor atípico em quantidade (9999), mantido para revisão |

## Contagens para verificação automática

Lidas por `scripts/verificar_limpeza.py`, que confere cada número com os arquivos.

```json
{"linhas_antes": 500, "removidas": 1, "linhas_depois": 499, "alteradas": 10, "com_observacao": 2, "remocoes_por_motivo": {"preco_unitario negativo ou zero (erro)": 1}, "alteracoes_por_tipo": {"quantidade vazia deduzida": 2, "região convertida para sigla de UF": 6, "texto vazio preenchido com 'Não informado'": 2, "valor_total divergente recalculado": 2}, "linhas_removidas": [8], "linhas_alteradas": [3, 4, 5, 6, 9, 10, 11, 13, 14, 27]}
```
