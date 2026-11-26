# Relatório de qualidade dos dados

- Arquivo analisado: `dados/vendas.csv`
- Gerado em: 2026-11-25 14:20
- Gerado por: `validar_planilha.py` (pandas). Todas as contagens vêm do código.

## Resultado: ❌ 8 tipo(s) de problema encontrado(s), 63 ocorrência(s) no total

## 1. Estrutura

- Linhas de dados: **501**
- Colunas (9): `data`, `pedido_id`, `produto`, `categoria`, `regiao`, `vendedor`, `quantidade`, `preco_unitario`, `valor_total`

| Coluna | Tipo inferido | Nulos |
| --- | --- | --- |
| `data` | data | 0 |
| `pedido_id` | texto | 0 |
| `produto` | texto | 0 |
| `categoria` | texto | 0 |
| `regiao` | texto | 0 |
| `vendedor` | texto | 0 |
| `quantidade` | inteiro | 0 |
| `preco_unitario` | inteiro | 0 |
| `valor_total` | inteiro | 1 |

## 2. Problemas encontrados

| Coluna | Tipo de problema | Quantidade | Exemplos |
| --- | --- | ---: | --- |
| `valor_total` | valor nulo/vazio | 1 | linha 51 |
| `data` | formatos de data misturados (AAAA-MM-DD e DD/MM/AAAA) | 30 | 471 linhas ISO, 30 linhas com barra |
| `preco_unitario` | formato numérico fora do padrão (R$, vírgula ou separador de milhar) | 10 | linha 32: 'R$ 80,00'; linha 33: 'R$ 700,00'; linha 34: 'R$ 700,00' |
| `valor_total` | formato numérico fora do padrão (R$, vírgula ou separador de milhar) | 10 | linha 32: '720,00'; linha 33: '2.800,00'; linha 34: '6.300,00' |
| `pedido_id` | pedido_id repetido com conteúdo diferente | 1 | linha 502: 'PED-00101' |
| `produto` | categoria escrita de formas diferentes | 4 | linha 47: 'mesa'; linha 48: '  Monitor  '; linha 49: 'MESA' |
| `regiao` | categoria escrita de formas diferentes | 6 | linha 42: ' sp '; linha 43: 'Rio de Janeiro'; linha 44: 'sao paulo' |
| `vendedor` | categoria escrita de formas diferentes | 1 | linha 50: 'ana' |

## 3. Categorias escritas de formas diferentes

A quantidade na tabela de problemas conta as linhas que usam variantes menos frequentes; a forma mais frequente é sugerida como canônica.

| Coluna | Forma mais frequente | Variantes (linhas) |
| --- | --- | --- |
| `produto` | 'Mesa' | 'Mesa'×87, 'MESA'×1, 'mesa'×1 |
| `produto` | 'Mouse' | 'Mouse'×94, 'MOUSE'×1 |
| `produto` | 'Monitor' | 'Monitor'×72, '  Monitor  '×1 |
| `regiao` | 'RS' | 'RS'×106, 'rs'×1 |
| `regiao` | 'SP' | 'SP'×82, ' sp '×1, 'sao paulo'×1 |
| `regiao` | 'PR' | 'PR'×110, 'Paraná'×1 |
| `regiao` | 'RJ' | 'RJ'×94, 'RIO DE JANEIRO'×1, 'Rio de Janeiro'×1 |
| `vendedor` | 'Ana' | 'Ana'×100, 'ana'×1 |

## Método e premissas

- Linhas contadas a partir do cabeçalho como linha 1; "linha N" é a linha na planilha.
- Nulos: vazio, `NA`, `N/A`, `NaN`, `null`, `None`, `-`, `--`.
- Datas aceitas: `AAAA-MM-DD` e `DD/MM/AAAA`. Com barra, a ordem é deduzida de datas inequívocas da própria coluna (dia > 12); sem evidência, assume-se DD/MM e há aviso.
- Valor atípico: acima de Q3+3×IQR ou abaixo de Q1−3×IQR (aviso; só `quantidade` e `preco_unitario` por produto; mínimo de 20 valores).
- `valor_total` deve ser igual a `quantidade × preco_unitario` (tolerância 0.02).
- Duplicata = cópia exata de uma linha anterior; a primeira ocorrência não conta. `pedido_id` repetido só é listado quando o conteúdo da linha difere.
- A planilha original não é modificada.
