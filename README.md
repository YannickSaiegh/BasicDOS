# BasicDOS

![Banner](banner.png)

![Python](https://img.shields.io/badge/python-3.10+-blue)
![HTTPS](https://img.shields.io/badge/protocol-HTTPS%20%7C%20HTTP%2F2-brightgreen)
![UI](https://img.shields.io/badge/UI-Rich-magenta)
![License](https://img.shields.io/badge/license-MIT-yellow)

Motor assíncrono de testes de carga **HTTP/HTTPS** com suporte a **HTTP/2**, pool de ligações keep-alive (reutilização TLS), painel em tempo real com **`rich`** e exportação de relatórios JSON.

---

## Funcionalidades

- **Alta Performance em HTTPS & HTTP/2**: Utiliza `asyncio` + `httpx[http2]` com pool de ligações keep-alive e multiplexing HTTP/2, evitando handshakes TLS desnecessários.
- **Painel em Tempo Real (`rich`)**: Mostra pedidos totais, códigos `2xx / 3xx / 4xx / 5xx`, timeouts, falhas de ligação/TLS, volume transferido (`MB` e `MB/s`), RPS atual, média de latência, percentis `p50 / p95 / p99` e protocolo negociado (`HTTP/2` ou `HTTP/1.1`).
- **Assistente Interativo + Modo CLI**: Corre `python main.py` para usar o menu numerado passo a passo, ou passa flags diretamente na linha de comandos para automação.
- **Controlo de Carga**: Concorrência configurável (`-c`), número máximo de pedidos (`-n`), duração máxima (`-d`) e limite global de RPS (`--max-rps`).
- **Flexibilidade HTTP/HTTPS**: Suporta `GET`, `POST`, `PUT`, `DELETE`, `HEAD`, cabeçalhos personalizados (`-H`), corpo JSON/texto (`--data`), redirecionamentos (`--follow-redirects`) e opção `--insecure` para certificados locais autoassinados.
- **Relatórios JSON**: Guarda o resumo completo das métricas com `-o load_report.json`.

---

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/YannickSaiegh/BasicDOS.git
cd BasicDOS

# (Opcional) Criar e ativar ambiente virtual
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

# Instalar dependências (inclui suporte HTTP/2)
pip install -r requirements.txt
```

---

## Utilização

### 1. Modo Interativo

```bash
python main.py
```

### 2. Modo Linha de Comandos (CLI)

**Teste HTTPS com HTTP/2 durante 30 segundos e 150 workers:**

```bash
python main.py https://meu-servidor.local/health -c 150 -d 30
```

**Envio de 5.000 pedidos `POST` em JSON com limite de 300 RPS e relatório JSON:**

```bash
python main.py https://api.meu-servidor.local/ping \
  -m POST \
  -c 100 \
  -n 5000 \
  --max-rps 300 \
  -H "Content-Type: application/json" \
  --data '{"ping":1}' \
  -o load_report.json
```

### Opções Disponíveis

| Flag | Descrição | Padrão |
| :--- | :--- | :--- |
| `url` | URL alvo (se omitires esquema, usa `https://`) | *(interativo)* |
| `-m`, `--method` | Método HTTP (`GET`, `POST`, `PUT`, `DELETE`, `HEAD`) | `GET` |
| `-c`, `--concurrency` | Workers assíncronos simultâneos | `100` |
| `-n`, `--requests` | Número total de pedidos (`0` = sem limite fixo) | `0` |
| `-t`, `--timeout` | Timeout por pedido em segundos | `5.0` |
| `-d`, `--duration` | Duração máxima em segundos (`0` = até `Ctrl+C`) | `0.0` |
| `--max-rps` | Limite global aproximado de RPS (`0` = sem limite) | `0.0` |
| `--http2` / `--no-http2` | Ativar ou desativar HTTP/2 sobre HTTPS | `--http2` |
| `-H`, `--header` | Cabeçalho extra no formato `Chave:Valor` (repetível) | `[]` |
| `--data` | Corpo do pedido HTTP | `None` |
| `--follow-redirects` | Seguir redirecionamentos (`301/302/307`) | `False` |
| `--insecure` | Desativar validação SSL/TLS (apenas testes locais) | `False` |
| `-o`, `--output` | Guardar resumo final em ficheiro JSON | `None` |

---

## Aviso Legal

Este projeto destina-se **exclusivamente a fins educativos, benchmarking e testes de carga autorizados** em sistemas próprios ou com permissão explícita. O uso não autorizado contra sistemas de terceiros é ilegal.

---

## Licença

Distribuído sob a licença **MIT**. Consulte [LICENSE](LICENSE) para mais detalhes.

---

**Made by TrionixDev**
