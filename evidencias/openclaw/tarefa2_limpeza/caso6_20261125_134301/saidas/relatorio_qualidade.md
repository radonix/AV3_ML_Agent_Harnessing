# Relatório de qualidade dos dados

- Arquivo analisado: `dados/vendas.csv`
- Gerado em: 2026-11-25 14:18
- Gerado por: `validar_planilha.py` (pandas). Todas as contagens vêm do código.

## Resultado: ❌ 7 tipo(s) de problema encontrado(s), 16 ocorrência(s) no total

## 1. Estrutura

- Linhas de dados: **500**
- Colunas (9): `data`, `pedido_id`, `produto`, `categoria`, `regiao`, `vendedor`, `quantidade`, `preco_unitario`, `valor_total`

| Coluna | Tipo inferido | Nulos |
| --- | --- | --- |
| `data` | data | 0 |
| `pedido_id` | texto | 0 |
| `produto` | texto | 2 |
| `categoria` | texto | 0 |
| `regiao` | texto | 0 |
| `vendedor` | texto | 0 |
| `quantidade` | inteiro | 2 |
| `preco_unitario` | inteiro | 0 |
| `valor_total` | inteiro | 0 |

## 2. Problemas encontrados

| Coluna | Tipo de problema | Quantidade | Exemplos |
| --- | --- | ---: | --- |
| `produto` | valor nulo/vazio | 2 | linha 3; linha 4 |
| `quantidade` | valor nulo/vazio | 2 | linha 5; linha 6 |
| `quantidade` | valor negativo | 1 | linha 7: '-3' |
| `preco_unitario` | valor negativo | 1 | linha 8: '-10' |
| `valor_total` | valor negativo | 2 | linha 7: '-240.0'; linha 8: '-70.0' |
| `valor_total` | valor_total diferente de quantidade × preco_unitario | 2 | linha 9: 6×80=480.00, valor_total=1; linha 10: 6×3500=21000.00, valor_total=2 |
| `regiao` | categoria escrita de formas diferentes | 6 | linha 4: 'São Paulo'; linha 9: 'São Paulo'; linha 11: 'São Paulo' |

## 3. Categorias escritas de formas diferentes

A quantidade na tabela de problemas conta as linhas que usam variantes menos frequentes; a forma mais frequente é sugerida como canônica.

| Coluna | Forma mais frequente | Variantes (linhas) |
| --- | --- | --- |
| `regiao` | 'SP' | 'SP'×78, 'São Paulo'×6 |

## 4. Avisos (não alteram o resultado)

| Coluna | Observação | Quantidade | Exemplos |
| --- | --- | ---: | --- |
| `quantidade` | valor atípico (fora de 3×IQR) | 1 | linha 11: '9999' |

## Método e premissas

- Linhas contadas a partir do cabeçalho como linha 1; "linha N" é a linha na planilha.
- Nulos: vazio, `NA`, `N/A`, `NaN`, `null`, `None`, `-`, `--`.
- Datas aceitas: `AAAA-MM-DD` e `DD/MM/AAAA`. Com barra, a ordem é deduzida de datas inequívocas da própria coluna (dia > 12); sem evidência, assume-se DD/MM e há aviso.
- Valor atípico: acima de Q3+3×IQR ou abaixo de Q1−3×IQR (aviso; só `quantidade` e `preco_unitario` por produto; mínimo de 20 valores).
- `valor_total` deve ser igual a `quantidade × preco_unitario` (tolerância 0.02).
- Duplicata = cópia exata de uma linha anterior; a primeira ocorrência não conta. `pedido_id` repetido só é listado quando o conteúdo da linha difere.
- A planilha original não é modificada.
