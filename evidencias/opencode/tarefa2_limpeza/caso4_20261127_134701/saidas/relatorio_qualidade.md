# Relatório de qualidade dos dados

- Arquivo analisado: `dados/vendas.csv`
- Gerado em: 2026-11-27 13:59
- Gerado por: `validar_planilha.py` (pandas). Todas as contagens vêm do código.

## Resultado: ✅ Nenhum problema encontrado

## 1. Estrutura

- Linhas de dados: **500**
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
| `valor_total` | inteiro | 0 |

## 2. Problemas encontrados

Nenhum problema encontrado.

## Método e premissas

- Linhas contadas a partir do cabeçalho como linha 1; "linha N" é a linha na planilha.
- Nulos: vazio, `NA`, `N/A`, `NaN`, `null`, `None`, `-`, `--`.
- Datas aceitas: `AAAA-MM-DD` e `DD/MM/AAAA`. Com barra, a ordem é deduzida de datas inequívocas da própria coluna (dia > 12); sem evidência, assume-se DD/MM e há aviso.
- Valor atípico: acima de Q3+3×IQR ou abaixo de Q1−3×IQR (aviso; só `quantidade` e `preco_unitario` por produto; mínimo de 20 valores).
- `valor_total` deve ser igual a `quantidade × preco_unitario` (tolerância 0.02).
- Duplicata = cópia exata de uma linha anterior; a primeira ocorrência não conta. `pedido_id` repetido só é listado quando o conteúdo da linha difere.
- A planilha original não é modificada.
