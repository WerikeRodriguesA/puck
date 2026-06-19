# 🚀 Puck

**Puck (Personal Utility Control Kernel)** é um assistente pessoal para desktop desenvolvido em Python com foco em automação local, monitoramento do sistema e interação baseada em eventos.

O projeto foi concebido para evoluir gradualmente de um simples automador de tarefas para um verdadeiro assistente pessoal inspirado em conceitos como o Jarvis, do Homem de Ferro.

---

# 🎯 Objetivos do Projeto

O Puck busca centralizar ações e informações do computador em uma única plataforma, permitindo:

* Abrir aplicativos automaticamente.
* Executar modos de trabalho personalizados.
* Monitorar recursos do sistema.
* Detectar eventos por áudio (palmas).
* Integrar Inteligência Artificial futuramente.
* Disponibilizar uma API para comunicação externa.
* Servir como projeto de portfólio, pesquisa acadêmica e potencial TCC.

---

# ✨ Funcionalidades Atuais

## Automação de Aplicativos

Abertura automática de programas configurados no sistema.

Exemplos:

* VS Code
* Spotify
* Opera GX
* Steam
* WPS Office
* Windows Terminal

---

## Modos de Trabalho

O usuário pode definir grupos de aplicativos para diferentes contextos.

Exemplo:

### ADS

* VS Code
* Spotify

### Estudo

* Opera GX
* Spotify
* WPS Writer

### Gamer

* Steam

---

## Configuração Centralizada

Todo o comportamento do sistema é controlado através do arquivo:

```text
config/config.yaml
```

Permitindo alterar:

* Aplicativos
* Caminhos dos executáveis
* Modos
* Configurações de áudio
* Configurações de log
* Recursos futuros

Sem necessidade de modificar código.

---

## Arquitetura Modular

O projeto foi estruturado para crescimento sustentável.

Princípios adotados:

* SOLID
* Separation of Concerns
* Dependency Inversion
* Baixo acoplamento
* Alta coesão

---

# 🏗 Estrutura do Projeto

```text
puck/
│
├── core/
│   ├── interfaces.py
│   ├── events.py
│   └── modes.py
│
├── modules/
│   ├── audio/
│   │   ├── detector.py
│   │   └── listener.py
│   │
│   ├── automation/
│   │   └── launcher.py
│   │
│   └── monitor/
│       └── system_info.py
│
├── adapters/
│
├── api/
│
├── config/
│   ├── settings.py
│   └── config.yaml
│
├── logs/
│
├── tests/
│
├── main.py
├── requirements.txt
├── .env.example
└── README.md
```

---

# 🔧 Tecnologias Utilizadas

## Backend

* Python 3.12+

---

## Bibliotecas

* PyYAML
* psutil
* NumPy
* PyAudio (ou alternativa futura)
* logging

---

## Futuras Tecnologias

* FastAPI
* Ollama
* OpenAI API
* PostgreSQL
* SQLite
* React
* Electron

---

# ⚙️ Instalação

## 1. Clone o projeto

```bash
git clone https://github.com/seu-usuario/puck.git
cd puck
```

---

## 2. Crie o ambiente virtual

```bash
py -3.12 -m venv .venv
```

---

## 3. Ative o ambiente virtual

Windows:

```bash
.venv\Scripts\activate
```

---

## 4. Atualize o pip

```bash
python -m pip install --upgrade pip
```

---

## 5. Instale as dependências

```bash
pip install -r requirements.txt
```

---

# ▶️ Executando

Após configurar o arquivo:

```text
config/config.yaml
```

execute:

```bash
python main.py
```

---

# ⚙️ Configuração

Os aplicativos são cadastrados em:

```yaml
apps:
  vscode:
    display_name: "VS Code"
    path: "C:/Users/USER/AppData/Local/Programs/Microsoft VS Code/Code.exe"
```

---

Os modos são definidos em:

```yaml
modes:
  ads:
    display_name: "Modo ADS"
    apps:
      - vscode
      - spotify

  estudo:
    display_name: "Modo Estudo"
    apps:
      - opera
      - spotify
      - wps_writer
```

---

Modo padrão:

```yaml
default_mode: ads
```

---

# 📊 Roadmap

## V1 — Concluído

* Estrutura arquitetural
* Configuração YAML
* Launcher de aplicativos
* Sistema de modos
* Logging
* Contratos (ABCs)

---

## V2 — Em desenvolvimento

* Detecção de palmas
* Seleção de modos por quantidade de palmas
* Cooldown anti-repetição
* Melhor tratamento de erros

---

## V3

* Dashboard de monitoramento
* CPU
* RAM
* Disco
* Processos

---

## V4

* FastAPI
* API REST
* Endpoints de controle
* Métricas do sistema

---

## V5

* Interface Web
* React
* Controle remoto

---

## V6

* Integração com IA local
* Ollama
* Llama 3
* Assistente conversacional

---

## V7

* Comandos por voz
* Wake word
* Interação em linguagem natural

---

# 📚 Conceitos Aplicados

Este projeto utiliza conceitos importantes de engenharia de software:

* SOLID
* Clean Architecture
* Dependency Injection
* Modularização
* Configuração Externa
* Interfaces e Contratos
* Monitoramento de Sistema
* Automação Desktop

---

# 🎓 Finalidade Acadêmica

Além de uso pessoal, o Puck foi projetado para servir como:

* Projeto de portfólio profissional.
* Projeto de pesquisa.
* Trabalho de Conclusão de Curso (TCC).
* Laboratório de estudos em IA e automação.

---

# 👨‍💻 Autor

Werike Rodrigues

Estudante de Direito e Análise e Desenvolvimento de Sistemas.

Projeto criado com o objetivo de explorar automação, arquitetura de software, inteligência artificial e desenvolvimento de sistemas escaláveis.
