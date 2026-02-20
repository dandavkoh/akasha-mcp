# Wie debuggen

## 🧪 DEV-Modus (mit Breakpoints)

### Eigenschaften

* ~~**TODO** Lokaler Projekt-Code wird komplett gemountet (`. :/app`)~~
* Image wird lokal aus dem Dockerfile gebaut
* **Remote Debugging** via debugpy auf Port 5678
* Debugger wird vom **Host** (VS Code) an den Container angehängt

### Voraussetzungen

**Docker Setup:**
* Port `5678` ist exponiert (für debugpy)

**VS Code Setup:**
* `.vscode/launch.json` existiert mit Attach-Konfiguration
* **Python Debugger Extension** (`ms-python.debugpy`) installiert
* Optional: Python, Pylance, Docker Extensions

---

### ▶️ Containerstarten

```bash
docker compose -f docker-compose.yml up --build -d
```

**Wichtig:** Beim ersten Mal oder bei Dependency-Änderungen `--build` verwenden!

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

**Es gibt zwei Varianten:**

#### Variante 1: Vom Host aus debuggen (einfacher)

1. **Container läuft** (siehe oben)
2. **VS Code auf dem Host** öffnen (normales Projektfenster)
3. **Run & Debug Panel öffnen** (Strg/Cmd + Shift + D)
4. Konfiguration **"Attach debugger (DEV)"** auswählen
5. **Start-Button klicken** (F5) oder "Start Debugging"
6. ✅ Status-Leiste wird orange → Debugger verbunden!

#### Variante 2: Im Container debuggen (nach Attach)

1. **VS Code an Container anhängen** (siehe oben)
2. **Im Container-Fenster:** Run & Debug Panel öffnen
3. Debugger-Konfiguration erstellen oder F5 drücken
4. Port 5678 auswählen (debugpy)
5. ✅ Debugger verbunden!

**Breakpoints setzen:**

1. Öffne z.B. `src/mcp/tools/greeting_tools.py`
2. Setze Breakpoint (Klick links neben Zeilennummer)
3. Triggere Codeausschnitt über OpenWebUI oder so
4. 🎯 **Breakpoint wird getroffen!**

**Debug-Features:**

* ✅ Step Over / Step Into / Continue
* ✅ Variablen inspizieren
* ✅ Watch Expressions
* ✅ Call Stack
* ✅ Debug Console (REPL)

**Debugger stoppen:**

* Stopp-Button in VS Code oder Shift+F5
* Container läuft weiter (debugpy wartet auf nächsten Attach)

---

## 🧰 VS Code – empfohlene Extensions

### Pflicht (für Remote Debugging)

```
ms-python.python          - Python (IntelliSense, Linting)
ms-python.vscode-pylance  - Pylance (Type Checking)
ms-python.debugpy         - Python Debugger (Remote Debugging) ⚡
```

### Sehr hilfreich

```
ms-azuretools.vscode-docker        - Docker (Container Management)
ms-vscode-remote.remote-containers - Dev Containers (optional)
```

**Installation:**

1. Öffne VS Code
2. Extensions Panel (Strg/Cmd + Shift + X)
3. Suche nach `ms-python.debugpy`
4. Installiere **Python Debugger**

Diese Extensions ermöglichen:

* ✅ Syntax Highlighting & IntelliSense
* ✅ Remote Debugging mit Breakpoints
* ✅ Docker Container Logs & Übersicht
* ✅ Type Checking & Linting

---

## 🔧 Troubleshooting

### ❌ "Failed to attach" beim Debuggen

**Ursachen:**

1. Container läuft nicht
   ```bash
   docker ps | grep pipelines
   ```

2. Debug-Port nicht exponiert
   ```bash
   docker port openwebui-pipelines-dev
   # sollte zeigen: 5678/tcp -> 0.0.0.0:5678
   ```

3. debugpy wurde nicht gestartet
   ```bash
   docker logs <containername> | grep "Debugger listening"
   # sollte zeigen: 🧲 Debugger listening on port 5678
   ```

---

### ❌ Breakpoints werden nicht getroffen

**Prüfen:**

1. **Path Mappings** in `.vscode/launch.json` korrekt?
   ```json
   {
     "version": "0.2.0",
     "configurations": [
       {
        "name": "Attach debugger (DEV)",
         "type": "debugpy",
         "request": "attach",
         "connect": {
           "host": "localhost",
           "port": 5678
         },
         "pathMappings": [
           {
             "localRoot": "${workspaceFolder}",
             "remoteRoot": "/app"
           }
         ]
       }
     ]
   }
   ```

2. **Debugger verbunden?** (Orange Status-Leiste in VS Code)

---

### ❓ Welcher Code läuft gerade?

```bash
# Pipeline-Dateien anzeigen
docker exec <containername> ls -la /app/src

# Inhalt einer Datei prüfen
docker exec <containername> cat /app/src/mcp/server.py | head -20
```

---

## 🚀 Quick Start (TL;DR)

### DEV mit Debugging

```bash
# 1. Container starten
docker compose -f docker-compose.yml up --build

# 2. In VS Code: Run & Debug → "Attach Pipelines (DEV)" → Start (F5)
# 3. Breakpoints setzen
# 4. Pipeline triggern
# 5. 🎯 Debug!
```

---

Happy hacking! 🚀
