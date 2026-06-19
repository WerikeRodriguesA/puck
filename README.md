# Puck

Puck (Personal Utility Control Kernel) é um assistente de automação desktop desenvolvido em Python, projetado com arquitetura modular e princípios SOLID para facilitar manutenção, escalabilidade e futuras integrações com IA.

## Funcionalidades

* Execução automática de aplicativos.
* Modos de trabalho configuráveis via YAML.
* Monitoramento de recursos do sistema.
* Detecção de eventos por áudio (em desenvolvimento).
* Sistema de logs.
* Estrutura preparada para API REST e integração com IA.

## Estrutura

```text
puck/
├── core/          # Contratos e regras de negócio
├── modules/       # Implementações dos módulos
├── adapters/      # Integrações externas
├── api/           # FastAPI (futuro)
├── config/        # Configurações da aplicação
├── logs/          # Logs gerados em runtime
├── tests/         # Testes automatizados
└── main.py        # Ponto de entrada
```

## Requisitos

* Python 3.12+
* Windows 10/11

## Instalação

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

## Configuração

Toda a configuração da aplicação é centralizada em:

```text
config/config.yaml
```

O arquivo permite configurar:

* Aplicativos disponíveis.
* Caminhos dos executáveis.
* Modos de trabalho.
* Configurações de áudio.
* Logging.
* Recursos futuros (IA, API e banco de dados).

## Arquitetura

O projeto segue os princípios:

* SOLID
* Dependency Inversion
* Separation of Concerns
* Baixo acoplamento
* Alta coesão

As implementações dependem de contratos definidos em `core/interfaces.py`, permitindo substituir componentes sem impactar o restante do sistema.

## Roadmap

* [x] Sistema de modos
* [x] Launcher de aplicativos
* [x] Configuração via YAML
* [x] Logging
* [ ] Detecção de palmas
* [ ] Cooldown de eventos
* [ ] Monitoramento avançado
* [ ] FastAPI
* [ ] Dashboard Web
* [ ] Integração com IA local (Ollama)
* [ ] Comandos por voz

## Autor

Werike Rodrigues
