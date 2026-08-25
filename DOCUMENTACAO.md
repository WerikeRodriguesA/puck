# Puck — Guia do Projeto

Este documento explica, em linguagem simples, o que o Puck faz, o que foi
implementado até agora e como usar o projeto hoje. Para detalhes técnicos de
cada módulo, consulte os comentários no próprio código (eles explicam o
"porquê" de cada decisão).

---

## 1. O que é o Puck?

O **Puck** é um assistente pessoal para Windows que "obedece" ao som de
palmas. Você configura grupos de aplicativos chamados **modos** e, ao bater
palmas um número de vezes, ele abre os programas daquele grupo.

Exemplo:

| Quantidade de palmas | O que acontece |
|----------------------|----------------|
| 2 palmas             | Abre o modo ADS (VS Code + Spotify) |
| 3 palmas             | Abre o modo Estudo (WPS Writer + Spotify + Opera) |
| 4 palmas             | Abre o modo Gamer (Steam) |

Tudo é configurado por um único arquivo: `config/config.yaml`. Você nunca
precisa mexer no código para mudar aplicativos ou modos.

---

## 2. O que foi feito em cada etapa

### Sprint 0 — Correções e testes

* **Correção de erros no config.yaml**: o "Google Chrome" apontava por engano
  para o arquivo do Opera, e o "Opera GX" usava uma variável de ambiente
  frágil no caminho. Os dois foram corrigidos.
* **Suíte de testes**: criamos testes automatizados para as partes principais
  (configuração, modos, abertura de aplicativos e monitoramento). Hoje são
  **67 testes**, todos passando. Eles usam "arquivos de mentira" — nunca abrem
  aplicativos de verdade nem usam sua configuração real.

### Sprint 1 — Sistema de eventos

* Criamos um **barramento de eventos** (o padrão "Observer"): cada parte do
  sistema anuncia o que faz (ex: "app aberto", "modo ativado", "sistema
  iniciado") sem precisar saber quem está ouvindo. Isso é a base para o futuro
  — quando houver comandos de voz, eles vão disparar os mesmos eventos das
  palmas.
* Tudo que acontece virou **log estruturado**: cada evento fica registrado
  com data, hora e origem.
* Adicionamos **argumentos de linha de comando** (explicados na seção 4).

### Sprint 3 — Monitoramento contínuo e API REST

* **Monitoramento contínuo**: o Puck agora mede CPU, memória e disco em um
  loop que roda sozinho em segundo plano (em uma thread). Ele guarda a última
  medição para consulta instantânea.
* **Alertas inteligentes**: se CPU ou memória passarem de um limite, ele
  publica um alerta (evento) e registra no log. O alerta só dispara de novo
  depois que o valor cair e subir novamente (sem spam de mensagens).
* **API REST (FastAPI)**: o Puck ganhou uma interface de comunicação HTTP —
  outros programas, aplicativos ou sites podem controlá-lo e ler suas
  métricas. Detalhes na seção 5.

---

## 3. Estrutura do projeto (visão geral)

```
puck/
├── main.py                  # Ponto de entrada — junta todas as peças
├── config/
│   ├── config.yaml          # ⭐ TUDO que você precisa configurar fica aqui
│   └── settings.py          # Lê o config.yaml com segurança
├── core/
│   ├── interfaces.py        # Contratos que os módulos devem seguir
│   ├── events.py            # Sistema de eventos (barramento)
│   └── modes.py             # Regras dos modos de trabalho
├── modules/
│   ├── audio/               # Escuta de palmas (detector)
│   ├── automation/          # Abertura de aplicativos (launcher)
│   └── monitor/             # Medição do sistema + loop contínuo
├── api/
│   └── server.py            # API REST (FastAPI)
├── utils/
│   └── logger.py            # Sistema de logs
├── tests/                   # Testes automatizados (67)
├── logs/                    # Arquivos de log gerados
└── requirements.txt         # Dependências do projeto
```

---

## 4. Como rodar o projeto hoje

### Pré-requisitos

* Python 3.12+
* Um microfone funcionando (para a detecção de palmas)

### Instalação (primeira vez)

```bash
# 1. Criar o ambiente virtual
py -3.12 -m venv .venv

# 2. Ativar (Windows)
.venv\Scripts\activate

# 3. Instalar as dependências
pip install -r requirements.txt
```

### Executar

```bash
python main.py
```

Pronto — o Puck fica ouvindo palmas. Bata **2 palmas** para ativar o modo
padrão (ou o número configurado).

### Opções de linha de comando

```bash
python main.py                        # Padrão: fica escutando palmas
python main.py --mode ads             # Ativa o modo "ads" assim que iniciar
python main.py --no-audio             # Roda sem microfone (útil para testar a API)
python main.py --config outro.yaml    # Usa outro arquivo de configuração
python main.py --list-modes           # Mostra os modos disponíveis e sai
```

### Configuração principal (config.yaml)

No `config/config.yaml` você controla:

| Seção | O que faz |
|-------|-----------|
| `apps` | Cadastro dos aplicativos (nome + caminho do executável) |
| `modes` | Grupos de aplicativos (o que abrir em cada situação) |
| `default_mode` | Modo ativado por 2 palmas |
| `clap_modes` | Mapeamento palmas → modo (ex: 3 palmas → estudo) |
| `audio` | Sensibilidade do microfone e tempos de detecção |
| `monitor` | Intervalo de medição e limites de alerta |
| `api` | Habilita/configura a API REST (veja abaixo) |
| `logging` | Nível e destino dos logs |

---

## 5. A API REST (FastAPI)

A API permite que outros programas controlem o Puck pela rede. Ela é
**opcional** — por padrão fica desligada.

### Como ativar

No `config/config.yaml`, mude:

```yaml
api:
  enabled: true
  host: "0.0.0.0"   # 0.0.0.0 = acessível na rede local | 127.0.0.1 = só nesta máquina
  port: 8000
```

Depois rode normalmente:

```bash
python main.py --no-audio   # ou sem o --no-audio, se quiser palmas também
```

A API sobe em `http://localhost:8000`. A documentação interativa (gerada
automaticamente pelo FastAPI) fica em `http://localhost:8000/docs`.

### Endpoints

#### GET `/`
Identificação do serviço.

```json
{ "service": "puck", "status": "running" }
```

#### GET `/health`
Verificação de vida ("healthcheck").

```json
{ "status": "ok" }
```

#### GET `/modes`
Lista os modos disponíveis.

```json
{ "modes": ["ads", "estudo", "gamer"] }
```

#### GET `/modes/{nome_do_modo}`
Detalhes de um modo específico. Ex: `GET /modes/ads`

```json
{ "name": "ads", "display_name": "Modo ADS", "apps": ["vscode", "spotify"] }
```

Se o modo não existir, retorna **404**.

#### POST `/modes/{nome_do_modo}/activate`
**Ativa um modo** — abre os aplicativos dele. Ex: `POST /modes/ads/activate`

```json
{ "mode": "ads", "activated": true }
```

Se o modo não existir, retorna **404**.

#### GET `/metrics`
Retorna a última medição do sistema (CPU, memória, disco, rede).

```json
{
  "cpu": { "usage_percent": 20.5, "cores": 8 },
  "memory": { "total_gb": 16.0, "used_gb": 8.2, "percent": 51.2 },
  "disk": { "total_gb": 500.0, "used_gb": 250.0, "percent": 50.0 },
  "network": { "bytes_sent_mb": 10.2, "bytes_recv_mb": 30.1 },
  "temperature_celsius": null
}
```

### Exemplos de uso rápido

PowerShell:

```powershell
# Ver os modos
Invoke-RestMethod http://localhost:8000/modes

# Ativar o modo gamer
Invoke-RestMethod -Method Post http://localhost:8000/modes/gamer/activate

# Ver as métricas do sistema
Invoke-RestMethod http://localhost:8000/metrics
```

Navegador: basta abrir `http://localhost:8000/docs` para testar tudo com
botões clicáveis.

---

## 6. Testes automatizados

Para rodar a suíte de testes (67 testes):

```bash
python -m pytest tests
```

Ou com mais detalhes:

```bash
python -m pytest tests -v
```

Os testes são seguros: eles usam configuração fake e "mockam" (simulam)
abertura de aplicativos, microfone e métricas do sistema — nada é aberto ou
medido de verdade durante os testes.

---

## 7. Próximos passos (roadmap)

O projeto já tem um caminho desenhado no `README.md`. Com o que foi feito,
os próximos passos naturais são:

* **Sprint 2 (intermediário)**: evitar abrir o mesmo app duas vezes, validação
  do config.yaml e rotação de logs.
* **Dashboard / Interface Web**: uma tela que mostra as métricas em tempo real
  e permite ativar modos com um clique (a API já fornece tudo isso).
* **Voz e IA**: comandos por voz e um assistente conversacional — o sistema de
  eventos foi desenhado exatamente para essa expansão.
