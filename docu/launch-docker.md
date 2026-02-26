# 🔥 Dev & Prod Workflow

## 🛠 Make Changes

Modify files in:

```bash
src/mcp/*
```

> **Hinweis:**
> *Im DEV-Modus (`docker-compose.dev.yml`) werden Änderungen im `src/` Ordner sofort übernommen – kein Build nötig!*
> *Im PROD-Modus (`docker-compose.yml`) muss der Code ins Image gebackt werden → Build erforderlich.*

---

## 🐳 DEV – Docker Compose v2 (live mount, Debugging)

```bash
# 1. Start DEV-Container (src gemountet, live reload)
docker compose -f docker-compose.dev.yml up -d

# 2. Optional: Build nur beim ersten Mal oder bei Dependency-Änderungen
docker compose -f docker-compose.dev.yml up --build -d

# 3. Änderungen an src/mcp/* wirken sofort
# 4. Debugger über VS Code anschließen (Port 5678)
```

**Wichtig:**

* DEV-Modus verwendet `Dockerfile.dev`
* `DEV_MODE=true` wird als ENV gesetzt
* `./src:/app/src` Volume sorgt für Live-Code

---

## 🐳 PROD – Docker Compose v2 (Image only)

```bash
# 1. Build PROD-Image
docker compose -f docker-compose.yml up --build -d

# 2. Starten (kein src mount)
docker compose -f docker-compose.yml up -d
```

**Wichtig:**

* PROD-Modus verwendet normales `Dockerfile`
* Kein Mount → Änderungen an `src/` erfordern Build
* Alle Abhängigkeiten werden ins Image gepackt

---

## ⚡ Quick Tips

* DEV-Modus = schnelle Iteration, Debugging, Breakpoints
* PROD-Modus = stabiler Container, kein Live-Code, ideal für Deployment
* Wenn du nur Python-Dateien in `src/` änderst, **im Dev-Modus reicht `up -d` ohne Build**
