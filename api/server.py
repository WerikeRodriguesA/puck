"""
api/server.py

API REST do Puck (FastAPI).

Responsabilidade:
    Expor controle e métricas do sistema via HTTP.

Arquitetura (Dependency Injection):
    create_app() recebe as dependências prontas — não constrói nada.
    Isso permite:
        - testar a API com fakes (sem abrir apps reais)
        - substituir componentes sem tocar na API
        - usar a mesma instância do app em main.py e nos testes

Endpoints:
    GET  /                          → identificação do serviço
    GET  /health                    → healthcheck
    GET  /modes                     → lista de modos disponíveis
    GET  /modes/{mode_name}         → detalhe de um modo
    POST /modes/{mode_name}/activate → ativa um modo (abre os apps)
    GET  /metrics                   → último relatório do sistema (cache)
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from core.events import EventBus, EventType, PuckEvent
from core.interfaces import AppLauncher, SystemMonitor
from core.modes import ModeManager
from modules.monitor.service import MonitorService
from modules.stats.tracker import StatsTracker


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Puck Control Center</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --accent: #38bdf8;
            --accent-hover: #0284c7;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border-radius: 12px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
        body { background-color: var(--bg-color); color: var(--text-primary); padding: 24px; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #334155; }
        h1 { font-size: 1.8rem; color: var(--accent); display: flex; align-items: center; gap: 10px; }
        .badge { background: #0369a1; color: #e0f2fe; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 24px; }
        .card { background: var(--card-bg); border-radius: var(--border-radius); padding: 20px; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }
        .card-title { font-size: 1rem; color: var(--text-secondary); margin-bottom: 12px; font-weight: 600; display: flex; justify-content: space-between; }
        .metric-value { font-size: 2.2rem; font-weight: 700; color: var(--text-primary); }
        
        .progress-bar-bg { background: #334155; height: 10px; border-radius: 5px; overflow: hidden; margin-top: 10px; }
        .progress-bar-fill { height: 100%; background: var(--accent); width: 0%; transition: width 0.5s ease; }

        .modes-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-top: 12px; }
        .btn-mode { background: #334155; color: var(--text-primary); border: 1px solid #475569; padding: 14px; border-radius: var(--border-radius); cursor: pointer; font-size: 1rem; font-weight: 600; transition: all 0.2s ease; display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
        .btn-mode:hover { background: var(--accent); color: #000; border-color: var(--accent); transform: translateY(-2px); }
        .btn-mode span.apps { font-size: 0.75rem; font-weight: 400; opacity: 0.8; }

        .toast { position: fixed; bottom: 20px; right: 20px; background: var(--success); color: #000; padding: 12px 20px; border-radius: 8px; font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.5); display: none; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚡ Puck Control Center <span class="badge">V2.0</span></h1>
            <div id="status-tag" style="color: var(--success); font-weight: 600;">● Online</div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-title">PROCESSADOR (CPU) <span id="cpu-percent">0%</span></div>
                <div class="metric-value" id="cpu-val">0%</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="cpu-bar"></div></div>
            </div>

            <div class="card">
                <div class="card-title">MEMÓRIA RAM <span id="ram-percent">0%</span></div>
                <div class="metric-value" id="ram-val">0 GB</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="ram-bar"></div></div>
            </div>

            <div class="card">
                <div class="card-title">DISCO PRINCIPAL <span id="disk-percent">0%</span></div>
                <div class="metric-value" id="disk-val">0 GB</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" id="disk-bar"></div></div>
            </div>
        </div>

        <div class="grid">
            <div class="card" style="grid-column: span 2;">
                <div class="card-title">MODOS DE TRABALHO DISPONÍVEIS</div>
                <div class="modes-list" id="modes-container">
                    <div style="color: var(--text-secondary);">Carregando modos...</div>
                </div>
            </div>

            <div class="card">
                <div class="card-title">ESTATÍSTICAS DE USO</div>
                <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 8px;">
                    <div>⏱️ <strong>Uptime:</strong> <span id="stat-uptime">0s</span></div>
                    <div>👏 <strong>Palmas Detectadas:</strong> <span id="stat-claps">0</span></div>
                    <div>🚀 <strong>Ativações de Modos:</strong> <span id="stat-activations">0</span></div>
                    <div>📱 <strong>Apps Disparados:</strong> <span id="stat-launches">0</span></div>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">Modo ativado com sucesso!</div>

    <script>
        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => toast.style.display = 'none', 3000);
        }

        async function loadMetrics() {
            try {
                const res = await fetch('/metrics');
                if (!res.ok) return;
                const data = await res.json();

                if (data.cpu) {
                    const cpu = data.cpu.usage_percent || 0;
                    document.getElementById('cpu-val').innerText = cpu + '%';
                    document.getElementById('cpu-percent').innerText = cpu + '%';
                    document.getElementById('cpu-bar').style.width = cpu + '%';
                }

                if (data.memory) {
                    const ramPct = data.memory.percent || 0;
                    const usedGb = data.memory.used_gb || 0;
                    document.getElementById('ram-val').innerText = usedGb + ' GB';
                    document.getElementById('ram-percent').innerText = ramPct + '%';
                    document.getElementById('ram-bar').style.width = ramPct + '%';
                }

                if (data.disk) {
                    const diskPct = data.disk.percent || 0;
                    const usedGb = data.disk.used_gb || 0;
                    document.getElementById('disk-val').innerText = usedGb + ' GB';
                    document.getElementById('disk-percent').innerText = diskPct + '%';
                    document.getElementById('disk-bar').style.width = diskPct + '%';
                }
            } catch (e) { console.error('Erro ao carregar métricas:', e); }
        }

        async function loadStats() {
            try {
                const res = await fetch('/stats');
                if (!res.ok) return;
                const data = await res.json();
                document.getElementById('stat-uptime').innerText = data.uptime_seconds + 's';
                document.getElementById('stat-claps').innerText = data.total_claps_detected;
                document.getElementById('stat-activations').innerText = data.total_mode_activations;
                document.getElementById('stat-launches').innerText = data.app_launches;
            } catch (e) { console.error('Erro ao carregar estatísticas:', e); }
        }

        async function loadModes() {
            try {
                const res = await fetch('/modes');
                if (!res.ok) return;
                const data = await res.json();
                const container = document.getElementById('modes-container');
                container.innerHTML = '';

                for (const modeName of data.modes) {
                    const btn = document.createElement('button');
                    btn.className = 'btn-mode';
                    btn.innerHTML = `<span>▶ ${modeName.toUpperCase()}</span><span class="apps">Clique para ativar</span>`;
                    btn.onclick = () => activateMode(modeName);
                    container.appendChild(btn);
                }
            } catch (e) { console.error('Erro ao carregar modos:', e); }
        }

        async function activateMode(modeName) {
            try {
                const res = await fetch(`/modes/${modeName}/activate`, { method: 'POST' });
                if (res.ok) {
                    showToast(`Modo '${modeName}' ativado com sucesso!`);
                    loadStats();
                } else {
                    showToast(`Erro ao ativar modo '${modeName}'`);
                }
            } catch (e) { showToast(`Falha de comunicação`); }
        }

        loadModes();
        loadMetrics();
        loadStats();
        setInterval(loadMetrics, 2000);
        setInterval(loadStats, 2000);
    </script>
</body>
</html>
"""


def create_app(
    launcher: AppLauncher,
    mode_manager: ModeManager,
    monitor: MonitorService,
    event_bus: Optional[EventBus] = None,
    stats_tracker: Optional[StatsTracker] = None,
) -> FastAPI:
    """
    Monta a aplicação FastAPI com as dependências injetadas.

    Args:
        launcher: abre aplicativos e modos.
        mode_manager: consulta modos configurados.
        monitor: fornece o último relatório do sistema (cache).
        event_bus: opcional — usado para publicar eventos de ativação.
        stats_tracker: opcional — fornece estatísticas de uso.
    """
    app = FastAPI(title="Puck API", version="0.2.0")

    @app.get("/")
    def root() -> dict:
        return {"service": "puck", "status": "running"}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> HTMLResponse:
        return HTMLResponse(content=DASHBOARD_HTML)

    @app.get("/modes")
    def list_modes() -> dict:
        return {"modes": mode_manager.list_modes()}

    @app.get("/modes/{mode_name}")
    def get_mode(mode_name: str) -> dict:
        mode = mode_manager.get_mode(mode_name)
        if not mode:
            raise HTTPException(
                status_code=404,
                detail=f"Modo '{mode_name}' não encontrado",
            )
        return {
            "name": mode.name,
            "display_name": mode.display_name,
            "apps": mode.apps,
        }

    @app.post("/modes/{mode_name}/activate")
    def activate_mode(mode_name: str) -> dict:
        mode = mode_manager.get_mode(mode_name)
        if not mode:
            raise HTTPException(
                status_code=404,
                detail=f"Modo '{mode_name}' não encontrado",
            )

        if event_bus:
            event_bus.publish(
                PuckEvent(
                    EventType.MODE_ACTIVATED,
                    payload=mode_name,
                    source="api",
                )
            )

        launcher.launch_mode(mode_name)
        return {"mode": mode_name, "activated": True}

    @app.get("/metrics")
    def metrics() -> dict:
        report = monitor.get_latest_report()
        if not report:
            report = monitor.get_full_report()
        return report

    @app.get("/stats")
    def stats() -> dict:
        if stats_tracker:
            return stats_tracker.get_stats()
        return {"status": "StatsTracker não configurado"}

    return app

