# Wie debuggen

## 🧪 DEV-Modus (mit Breakpoints)

### Eigenschaften

* **Lokaler Projekt-Code wird live gemountet:** `./src:/app/src`
* Dev-Dockerfile (`Dockerfile.dev`) wird verwendet
* **Remote Debugging** via debugpy auf Port 5678
* Debugger wird vom **Host** (VS Code) an den Container angehängt
* `DEV_MODE=true` als ENV, um Verhalten im Python-Code zu steuern

### Voraussetzungen

**Docker Setup:**

* Port `5678` ist exponiert (für debugpy)
* Docker Compose: `docker-compose.dev.yml` existiert

**VS Code Setup:**

* `.vscode/launch.json` existiert mit Attach-Konfiguration
* Python Debugger Extension (`ms-python.debugpy`) installiert
* Optional: Python, Pylance, Docker Extensions

---

### ▶️ Container starten (DEV)

```bash
docker compose -f docker-compose.dev.yml up -d
```

**Hinweise:**

* Beim ersten Mal oder bei Dependency-Änderungen `--build` hinzufügen:

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

* **Änderungen im Python-Code** in `src/` werden live übernommen → **kein Rebuild nötig**

---

### ▶️ Container starten (PROD)

```bash
docker compose -f docker-compose.yml up --build -d
```

* Verwendet normales Dockerfile (`Dockerfile`)
* Kein Mount des `src` Ordners → Code aus Image
* Build nötig, um Änderungen einzupacken

---

###   VS Code lokal in Docker an Container anhängen (Dev Containers)

**Voraussetzung:**
* Extension **Dev Containers** (`ms-vscode-remote.remote-containers`) installiert

**Workflow:**

1. **Container läuft** (siehe oben - DEV-Modus muss gestartet sein)
2. **VS Code öffnen** (beliebiges Fenster)
3. **Command Palette** öffnen (F1 oder Strg/Cmd + Shift + P)
4. Befehl: `Dev Containers: Attach to Running Container...` eingeben
5. Container **`<containername>`** auswählen
6. **Neues VS Code Fenster öffnet sich** - läuft jetzt IM Container!
7. **Ordner öffnen**: Im neuen Fenster → File → Open Folder → `/app` eingeben
8. ✅ Sie arbeiten jetzt direkt im Container im `/app` Ordner!

**Wichtig:**
* Das neue VS Code Fenster zeigt **"Dev Container: ..."** unten links (grün)
* Sie sehen jetzt die Dateien AUS DEM CONTAINER, nicht vom Host
* Terminal öffnet direkt im Container (kein `docker exec` nötig)

---

### 🐛 Debugger anhängen (Remote Debugging)

**Variante 1: Vom Host aus debuggen (einfacher)**

1. Container läuft (DEV-Modus)
2. VS Code auf dem Host öffnen
3. Run & Debug → Konfiguration `"Attach debugger (DEV)"` auswählen
4. Starten (F5) → Status-Leiste wird orange → Debugger verbunden

**Variante 2: Im Container debuggen (nach Attach)**

1. VS Code an Container anhängen (siehe Dev Containers)
2. Run & Debug Panel öffnen → Debugger starten
3. Port 5678 auswählen (debugpy) → Debugger verbunden

**Breakpoints setzen:**

1. Datei z.B. `src/mcp/tools/greeting_tools.py` öffnen
2. Breakpoint setzen (links neben Zeilennummer)
3. Code triggern (OpenWebUI oder MCP API)
4. 🎯 Breakpoint wird getroffen

---

## 🔧 DEV_MODE im Python-Code

```python
import os

DEV_MODE = os.getenv("DEV_MODE", "false") == "true"

if DEV_MODE:
    print("Running in DEV mode – live reload enabled")
```

---

## 🧰 VS Code – empfohlene Extensions

**Pflicht (für Remote Debugging)**

```
ms-python.python
ms-python.vscode-pylance
ms-python.debugpy
```

**Sehr hilfreich**

```
ms-azuretools.vscode-docker
ms-vscode-remote.remote-containers
```

---

## 🔧 Troubleshooting

### ❌ "Failed to attach" beim Debuggen

1. Container läuft?

```bash
docker ps | grep akasha-mcp
```

2. Debug-Port offen?

```bash
docker port akasha-mcp
# sollte zeigen: 5678/tcp -> 0.0.0.0:5678
```

3. debugpy gestartet?

```bash
docker logs akasha-mcp | grep "Debugger listening"
```

---

### ❌ Breakpoints werden nicht getroffen

1. `pathMappings` in `.vscode/launch.json` korrekt?

```json
{
  "localRoot": "${workspaceFolder}/src",
  "remoteRoot": "/app/src"
}
```

2. Debugger verbunden (orange Status-Leiste)?

---

### ❓ Welcher Code läuft gerade?

```bash
docker exec akasha-mcp ls -la /app/src
docker exec akasha-mcp cat /app/src/mcp/server.py | head -20
```

---

## 🚀 Quick Start

### DEV (mit live code + Debugging)

```bash
# 1. Container starten (live mount)
docker compose -f docker-compose.dev.yml up -d

# 2. In VS Code: Run & Debug → "Attach debugger (DEV)" → F5
# 3. Breakpoints setzen, Code triggern, 🎯 Debug!
```

### PROD (nur Image, kein live mount)

```bash
docker compose -f docker-compose.yml up --build -d
```

---

Happy hacking! 🚀
