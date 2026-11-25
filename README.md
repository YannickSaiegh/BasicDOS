# BasicDOS

![Banner](banner.png)

![Python](https://img.shields.io/badge/python-3.8+-blue)
![UI](https://img.shields.io/badge/UI-Rich-magenta)
![License](https://img.shields.io/badge/license-MIT-yellow)

Ferramenta educativa em Python para testes básicos de carga HTTP com múltiplas threads e interface interativa no terminal usando **`rich`** e **`requests`**.

---

## Funcionalidades

- **Estatísticas em Tempo Real**: Total de pedidos, pedidos bem-sucedidos, falhas de ligação, timeouts, pedidos por segundo (RPS) e tempo médio de resposta.
- **Interface Interativa (`rich`)**: Painéis formatados com o banner **Soul Reaper** e barra de progresso em tempo real.
- **Velocidade Configurável**: Permite definir o atraso entre pedidos (`0.1s` a `1.0s`).
- **Resumo Final**: Apresenta métricas consolidadas assim que o teste é interrompido com `Ctrl+C`.

---

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/YannickSaiegh/BasicDOS.git
cd BasicDOS

# Instalar dependências
pip install -r requirements.txt
```

---

## Utilização

```bash
python main.py
```

1. Introduz o URL do servidor de teste autorizado.
2. Escolhe o atraso entre pedidos (`0.1` a `1` segundo; padrão `0.1`).
3. Pressiona `Ctrl+C` a qualquer momento para parar e ver o resumo final.

---

## Aviso Legal

Este projeto destina-se **exclusivamente a fins educativos e testes autorizados** em sistemas próprios ou com permissão explícita. O uso não autorizado contra sistemas de terceiros é ilegal.

---

## Licença

Distribuído sob a licença **MIT**. Consulte [LICENSE](LICENSE) para mais detalhes.

---

**Made by TrionixDev**
