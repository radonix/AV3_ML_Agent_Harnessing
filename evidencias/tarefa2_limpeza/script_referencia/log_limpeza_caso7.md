# Log de limpeza dos dados

- Arquivo de entrada: `<tmp>/caso7/vendas.csv` (não é alterado)
- Arquivo limpo: `/home/claude/radonix/av3_ml_agent_harnessing/saidas/testes_limpeza/caso7/vendas_limpas.csv`
- Relatório de qualidade usado: `/home/claude/radonix/av3_ml_agent_harnessing/saidas/testes_limpeza/caso7/relatorio_qualidade.md`
- Gerado em: 2026-11-24 18:51
- Gerado por: `limpar_vendas.py` (pandas). Todas as contagens e correções vêm do código.

## Resultado

| Contagem | Linhas |
| --- | ---: |
| Antes (linhas de dados na entrada) | 501 |
| Removidas | 1 |
| Depois (linhas em `vendas_limpas.csv`) | 500 |
| Alteradas (mantidas com algum valor corrigido) | 50 |
| Mantidas com observação para revisão humana | 0 |

Conferência: 501 − 1 = 500 ✅

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
| duplicata após padronização | 1 |

## 3. Alterações por tipo

Uma linha pode ter mais de um tipo de alteração.

| Tipo de alteração | Linhas |
| --- | ---: |
| data convertida para AAAA-MM-DD | 30 |
| espaços extras removidos | 1 |
| formato numérico convertido | 10 |
| grafia padronizada | 3 |
| região convertida para sigla de UF | 5 |
| valor_total vazio recalculado | 1 |

## 4. Tabela de equivalência aplicada

| Coluna | Valor original | Valor padronizado | Linhas |
| --- | --- | --- | ---: |
| `produto` | 'MESA' | 'Mesa' | 1 |
| `produto` | 'mesa' | 'Mesa' | 1 |
| `regiao` | 'RIO DE JANEIRO' | 'RJ' | 1 |
| `regiao` | 'Rio de Janeiro' | 'RJ' | 1 |
| `regiao` | 'rs' | 'RS' | 1 |
| `regiao` | 'sao paulo' | 'SP' | 1 |
| `regiao` | 'sp' | 'SP' | 1 |
| `vendedor` | 'ana' | 'Ana' | 1 |

Equivalência de regiões usada: sigla ou nome do estado, sem diferença de maiúsculas, acentos ou espaços → sigla da UF (ex.: `São Paulo`, `sao paulo`, ` sp ` → `SP`).

## 5. Problemas do relatório de qualidade (Tarefa 1) e tratamento

| Coluna | Problema na Tarefa 1 | Quantidade | Tratamento nesta limpeza |
| --- | --- | ---: | --- |
| `valor_total` | valor nulo/vazio | 1 | R5: recomposto pela conta ou linha removida |
| `data` | formatos de data misturados (AAAA-MM-DD e DD/MM/AAAA) | 30 | R3: convertido para AAAA-MM-DD |
| `preco_unitario` | formato numérico fora do padrão (R$, vírgula ou separador de milhar) | 10 | R4: convertido para número com ponto decimal |
| `valor_total` | formato numérico fora do padrão (R$, vírgula ou separador de milhar) | 10 | R4: convertido para número com ponto decimal |
| `pedido_id` | pedido_id repetido com conteúdo diferente | 1 | R10 se ficar idêntica após padronizar; senão R11 (mantida, revisão) |
| `produto` | categoria escrita de formas diferentes | 4 | R9: padronizado |
| `regiao` | categoria escrita de formas diferentes | 6 | R9: padronizado |
| `vendedor` | categoria escrita de formas diferentes | 1 | R9: padronizado |

As contagens desta limpeza (seções 2 e 3) podem ser maiores que as da Tarefa 1: duplicatas e grafias que só aparecem depois de padronizar não são vistas lá.

## 6. Linhas removidas

| Linha | pedido_id | Motivo | Detalhe |
| ---: | --- | --- | --- |
| 502 | PED-00101 | duplicata após padronização | igual à linha 102 |

## 7. Linhas alteradas

| Linha | pedido_id | Alterações |
| ---: | --- | --- |
| 2 | PED-00001 | data: '07/01/2026' → 2026-01-07 |
| 3 | PED-00002 | data: '27/01/2026' → 2026-01-27 |
| 4 | PED-00003 | data: '09/01/2026' → 2026-01-09 |
| 5 | PED-00004 | data: '10/05/2026' → 2026-05-10 |
| 6 | PED-00005 | data: '16/06/2026' → 2026-06-16 |
| 7 | PED-00006 | data: '31/05/2026' → 2026-05-31 |
| 8 | PED-00007 | data: '29/03/2026' → 2026-03-29 |
| 9 | PED-00008 | data: '27/01/2026' → 2026-01-27 |
| 10 | PED-00009 | data: '30/03/2026' → 2026-03-30 |
| 11 | PED-00010 | data: '18/05/2026' → 2026-05-18 |
| 12 | PED-00011 | data: '17/03/2026' → 2026-03-17 |
| 13 | PED-00012 | data: '30/06/2026' → 2026-06-30 |
| 14 | PED-00013 | data: '16/03/2026' → 2026-03-16 |
| 15 | PED-00014 | data: '13/03/2026' → 2026-03-13 |
| 16 | PED-00015 | data: '01/04/2026' → 2026-04-01 |
| 17 | PED-00016 | data: '05/06/2026' → 2026-06-05 |
| 18 | PED-00017 | data: '11/02/2026' → 2026-02-11 |
| 19 | PED-00018 | data: '26/02/2026' → 2026-02-26 |
| 20 | PED-00019 | data: '22/03/2026' → 2026-03-22 |
| 21 | PED-00020 | data: '26/05/2026' → 2026-05-26 |
| 22 | PED-00021 | data: '12/04/2026' → 2026-04-12 |
| 23 | PED-00022 | data: '05/03/2026' → 2026-03-05 |
| 24 | PED-00023 | data: '20/04/2026' → 2026-04-20 |
| 25 | PED-00024 | data: '05/02/2026' → 2026-02-05 |
| 26 | PED-00025 | data: '29/01/2026' → 2026-01-29 |
| 27 | PED-00026 | data: '02/06/2026' → 2026-06-02 |
| 28 | PED-00027 | data: '30/04/2026' → 2026-04-30 |
| 29 | PED-00028 | data: '24/06/2026' → 2026-06-24 |
| 30 | PED-00029 | data: '29/01/2026' → 2026-01-29 |
| 31 | PED-00030 | data: '01/01/2026' → 2026-01-01 |
| 32 | PED-00031 | preco_unitario: 'R$ 80,00' → 80; valor_total: '720,00' → 720 |
| 33 | PED-00032 | preco_unitario: 'R$ 700,00' → 700; valor_total: '2.800,00' → 2800 |
| 34 | PED-00033 | preco_unitario: 'R$ 700,00' → 700; valor_total: '6.300,00' → 6300 |
| 35 | PED-00034 | preco_unitario: 'R$ 900,00' → 900; valor_total: '900,00' → 900 |
| 36 | PED-00035 | preco_unitario: 'R$ 80,00' → 80; valor_total: '80,00' → 80 |
| 37 | PED-00036 | preco_unitario: 'R$ 3.500,00' → 3500; valor_total: '28.000,00' → 28000 |
| 38 | PED-00037 | preco_unitario: 'R$ 80,00' → 80; valor_total: '640,00' → 640 |
| 39 | PED-00038 | preco_unitario: 'R$ 700,00' → 700; valor_total: '7.000,00' → 7000 |
| 40 | PED-00039 | preco_unitario: 'R$ 1.200,00' → 1200; valor_total: '4.800,00' → 4800 |
| 41 | PED-00040 | preco_unitario: 'R$ 900,00' → 900; valor_total: '8.100,00' → 8100 |
| 42 | PED-00041 | regiao: ' sp ' → 'SP' |
| 43 | PED-00042 | regiao: 'Rio de Janeiro' → 'RJ' |
| 44 | PED-00043 | regiao: 'sao paulo' → 'SP' |
| 45 | PED-00044 | regiao: 'RIO DE JANEIRO' → 'RJ' |
| 46 | PED-00045 | regiao: 'rs' → 'RS' |
| 47 | PED-00046 | produto: 'mesa' → 'Mesa' |
| 48 | PED-00047 | produto: '  Monitor  ' → 'Monitor' |
| 49 | PED-00048 | produto: 'MESA' → 'Mesa' |
| 50 | PED-00049 | vendedor: 'ana' → 'Ana' |
| 51 | PED-00050 | valor_total: vazio → 5400.00 (6×900) |

## 8. Linhas mantidas com observação (revisão humana)

Nenhuma.

## 9. Avisos

- Datas com barra interpretadas como DD/MM/AAAA.

## Contagens para verificação automática

Lidas por `scripts/verificar_limpeza.py`, que confere cada número com os arquivos.

```json
{"linhas_antes": 501, "removidas": 1, "linhas_depois": 500, "alteradas": 50, "com_observacao": 0, "remocoes_por_motivo": {"duplicata após padronização": 1}, "alteracoes_por_tipo": {"data convertida para AAAA-MM-DD": 30, "espaços extras removidos": 1, "formato numérico convertido": 10, "grafia padronizada": 3, "região convertida para sigla de UF": 5, "valor_total vazio recalculado": 1}, "linhas_removidas": [502], "linhas_alteradas": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51]}
```
