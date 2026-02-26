# NAS Indexierung und Suche

## Übersicht

Die NAS-Indexierung wurde von der Suchfunktion getrennt, um Performance zu verbessern:

- **Indexierung**: Wird einmalig oder auf Abruf ausgeführt
- **Suche**: Greift auf den bereits erstellten Index zu

## Verwendung

### 1. Dokumente indexieren

Um die NAS-Dokumente zu indexieren, führe folgenden Befehl aus:

```bash
docker exec akasha-mcp index-chroma
```

Oder während der Container läuft:

```bash
docker compose -f docker-compose.dev.yml exec akasha-mcp index-chroma
```

### 2. Index neu erstellen

Falls neue Dokumente hinzugefügt wurden oder der Index aktualisiert werden soll:

```bash
docker exec akasha-mcp index-chroma
```

Der alte Index wird automatisch gelöscht und neu erstellt.

### 3. Dokumente durchsuchen

Nach der Indexierung kann das MCP-Tool `search_nas` verwendet werden:

```python
# Via MCP Client
search_nas(query="Was ist die Antwort?")
```

## Technische Details

### Indexierungs-Skript

Das Skript `src/mcp/index_nas.py`:
- Lädt Dokumente aus `/mnt/nas_docs`
- Unterstützte Formate: `.pdf`, `.docx`, `.txt`, `.md`
- Teilt Dokumente in Chunks (500 Zeichen, 50 Overlap)
- Erstellt Embeddings mit `all-MiniLM-L6-v2`
- Speichert in ChromaDB unter `/app/chroma_index`

### Suchfunktion

Die Funktion `search_nas` in `src/mcp/tools/nas_tools.py`:
- Lädt den existierenden Index
- Führt Similarity-Search aus
- Gibt Top 3 relevante Chunks zurück

## Fehlerbehandlung

Falls `search_nas` die Meldung "Kein Index gefunden" zurückgibt:
- Führe zuerst die Indexierung aus: `docker exec akasha-mcp index-chroma`
- Prüfe, ob das Volume `/mnt/nas_docs` korrekt gemountet ist
- Prüfe, ob Dokumente im NAS-Ordner vorhanden sind
