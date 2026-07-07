# 2x1000 Open Data — Partiti politici

Piattaforma open data per consultare la serie storica del 2 per mille IRPEF
destinato dai contribuenti italiani ai partiti politici. Realizzata nel
contesto dell'**Osservatorio ASSIF sul 5, 2 e 8 per mille**.

La piattaforma **non** presenta il 2x1000 come misura del consenso
elettorale: lo tratta come una forma specifica di partecipazione fiscale,
la scelta volontaria di destinare una quota dell'IRPEF a un partito
ammesso al beneficio. Si veda la pagina `/metodo.php` per la nota
metodologica completa.

- Ambiente di sviluppo: https://dev2x1000.almagioni.com
- Produzione: https://2x1000.assif.it
- Repository: https://github.com/aalmagio/2x1000

## Indice

- [Requisiti](#requisiti)
- [Struttura del progetto](#struttura-del-progetto)
- [Installazione su Plesk](#installazione-su-plesk)
- [Configurazione](#configurazione)
- [Importazione dei dati](#importazione-dei-dati)
- [Pipeline Python di acquisizione dati](#pipeline-python-di-acquisizione-dati)
- [Generazione degli open data](#generazione-degli-open-data)
- [API](#api)
- [Dati demo](#dati-demo)
- [Note metodologiche](#note-metodologiche)
- [Licenza](#licenza)
- [Fonti e crediti](#fonti-e-crediti)

## Requisiti

- PHP 8.1 o superiore, con estensione `pdo_mysql`
- MySQL 5.7+ oppure MariaDB 10.3+
- Un server web (Apache/nginx via Plesk) con document root su `public/`
- Nessuna dipendenza da Composer o Node.js in produzione: il frontend usa
  Chart.js vendorizzato in `public/assets/js/vendor/`, senza chiamate a CDN
  esterni
- Python 3.10+ **opzionale**, solo se si usa la pipeline di acquisizione
  automatica in `python/` (l'import via CSV manuale non ne ha bisogno)

## Struttura del progetto

```
app/
  config/database.php     Connessione PDO e caricamento .env
  includes/                Helper, header/footer/layout condivisi
  models/                  Party, Result, AnnualTotal, Source (query PDO)
  api/                     Logica delle API JSON (richiamata da public/api)
  views/                   Template delle pagine (incluse dentro il layout)
public/
  *.php                    Entry point delle pagine (document root Plesk)
  api/                     Wrapper sottili che richiamano app/api/*.php
  assets/                  CSS, JS (incluso Chart.js vendorizzato), immagini
  download.php             Streaming controllato dei file in data/exports/
data/
  raw/                     File grezzi delle fonti (CSV/HTML/PDF), non versionati
  processed/               CSV normalizzati pronti per l'import
  exports/                 Dataset open data generati (CSV/JSON + manifest.json)
database/
  schema.sql               Schema completo (tabelle + indici)
  views.sql                Viste SQL di comodo (v_results_full, v_party_summary)
  seed.sql                 Dati DEMO (marcati esplicitamente, non reali)
scripts/
  import_parties.php       Importa/aggiorna l'anagrafica partiti da CSV
  import_results.php       Importa i risultati annuali da CSV
  calculate_indicators.php Calcola quote, ranking, medie, concentrazione
  export_open_data.php     Genera i CSV/JSON pubblicati in data/exports/
python/
  acquire_results.py       Scarica/estrae i risultati annuali dal MEF
  acquire_party_codes.py   Scarica/estrae elenco partiti ammessi e codici dall'AdE
  db_updater.py            Scrive i dati normalizzati nel database MySQL
  pipeline.py              Orchestratore: acquisizione → DB → indicatori → export
  config.yaml              URL per anno delle fonti ufficiali (da compilare)
```

## Installazione su Plesk

1. **Crea il database.** Dal pannello Plesk, crea un database MySQL/MariaDB
   e un utente dedicato con privilegi su quel database.
2. **Carica il codice.** Via Git (consigliato: collega il repository
   GitHub dal pannello "Git" di Plesk) oppure via upload/FTP dell'intero
   progetto nella webspace del dominio.
3. **Punta il dominio a `public/`.** In Plesk → Hosting Settings → Document
   root, impostare `public` come document root (non la radice del
   repository).
4. **Configura `.env`.** Copia `.env.example` in `.env` nella radice del
   progetto (fuori da `public/`, quindi non accessibile dal browser) e
   inserisci le credenziali reali del database.
5. **Importa lo schema.**
   ```
   mysql -u <utente> -p <database> < database/schema.sql
   mysql -u <utente> -p <database> < database/views.sql
   ```
   Non eseguire `database/seed.sql` in produzione: contiene solo dati DEMO.
6. **Importa i dati reali** (si veda [Importazione dei dati](#importazione-dei-dati)).
7. **Genera gli open data:** `php scripts/export_open_data.php`.
8. **Permessi cartelle.** Assicurati che `data/exports/` sia scrivibile
   dall'utente con cui girano i processi PHP (per rigenerare gli export),
   e che `data/raw/` e `data/processed/` non siano esposte pubblicamente
   (sono fuori da `public/`, quindi già non raggiungibili via HTTP con
   document root su `public/`).
9. **Cron (opzionale).** Per rigenerare periodicamente gli indicatori e gli
   export, in Plesk → Programmazione attività:
   ```
   php /var/www/vhosts/<dominio>/scripts/calculate_indicators.php
   php /var/www/vhosts/<dominio>/scripts/export_open_data.php
   ```

## Configurazione

Tutte le variabili sono lette da `.env` (vedi `.env.example`):

| Variabile | Descrizione |
|---|---|
| `APP_ENV` | `development` oppure `production` |
| `APP_URL` | URL base del sito (usato per link assoluti) |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_CHARSET` | Connessione MySQL/MariaDB |
| `GROWTH_MIN_PREVIOUS_CHOICES` | Soglia minima di scelte nell'anno precedente per essere incluso nelle classifiche di crescita/calo percentuale (evita distorsioni su numeri piccoli) |

`.env` non va mai versionato (è già in `.gitignore`).

## Importazione dei dati

Il flusso previsto è: CSV normalizzati in `data/processed/` → import nel
database → calcolo indicatori → export open data.

1. **Anagrafica partiti** — `data/processed/parties.csv` con intestazione
   `canonical_name,slug,first_year,last_year,is_active,notes`:
   ```
   php scripts/import_parties.php
   ```
2. **Risultati annuali** — `data/processed/results.csv` con intestazione
   `party_slug,declaration_year,tax_year,valid_choices,amount,source_id`
   (il partito deve già esistere; `source_id` è opzionale e deve riferirsi
   a una riga già presente in `sources`):
   ```
   php scripts/import_results.php
   ```
3. **Calcolo indicatori** — quote, ranking, importo medio, variazioni,
   concentrazione top 3/5/10:
   ```
   php scripts/calculate_indicators.php
   ```

Entrambi gli script di import accettano un percorso CSV alternativo come
primo argomento, es. `php scripts/import_results.php /percorso/mio.csv`.

Le fonti (tabella `sources`) e i codici annuali da dichiarazione (tabella
`party_codes`) si popolano tramite `INSERT` diretti (manuali o da script
ad hoc) sul database, dato il basso volume e la necessità di verifica
manuale del contenuto ufficiale — oppure automaticamente tramite la pipeline
Python descritta di seguito.

## Pipeline Python di acquisizione dati

In alternativa all'import manuale via CSV, il progetto include in `python/`
una pipeline di acquisizione automatica dalle fonti ufficiali al database,
analoga (ma più semplice, dato il formato del 2x1000) a quella già usata nel
progetto gemello [5x1000](https://github.com/aalmagio/5x1000). Scrive nello
**stesso database** del sito PHP, leggendo le stesse variabili da `.env`
(`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`).

```bash
cd python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Pipeline completa per un anno: download → estrazione → DB → indicatori → export
python pipeline.py --anni 2024

# Solo scrittura DB + ricalcolo indicatori, senza riscaricare (file già in data/raw/)
python pipeline.py --anni 2024 --skip-download

# Solo alcuni step
python pipeline.py --anni 2024 --only db,indicators,export

# Analisi senza scrivere nel database
python pipeline.py --anni 2024 --dry-run
```

**Come funziona:**
1. `acquire_results.py` scarica (o legge da `data/raw/<anno>/`) il file dei
   risultati annuali pubblicato dal **MEF – Dipartimento delle Finanze** e lo
   normalizza in `data/processed/mef_results_<anno>.csv`;
2. `acquire_party_codes.py` fa lo stesso per l'elenco dei partiti ammessi e i
   codici da dichiarazione pubblicati dall'**Agenzia delle Entrate**
   (`data/processed/ade_codes_<anno>.csv`);
3. `db_updater.py` scrive questi CSV normalizzati nel database (`sources`,
   `parties`, `results`, `party_codes`), con upsert idempotenti — ogni fonte
   viene registrata una sola volta (deduplicata per checksum SHA-256), ogni
   partito individuato per slug con `first_year`/`last_year` estesi
   automaticamente;
4. `pipeline.py` richiama infine `scripts/calculate_indicators.php` e
   `scripts/export_open_data.php` (gli stessi script PHP usati per l'import
   manuale), così i numeri restano identici indipendentemente dal percorso
   di import scelto — non esiste una seconda implementazione dei calcoli in
   Python da mantenere sincronizzata con quella PHP.

**Configurazione delle fonti — da compilare:** `python/config.yaml` contiene
`url_anni_risultati` e `url_anni_codici`, entrambi **vuoti di default**.
Nessun URL del MEF o dell'Agenzia delle Entrate è precompilato: le pagine
ufficiali vanno cercate e verificate manualmente (Dipartimento delle Finanze
→ Analisi statistiche delle dichiarazioni → 2 per mille; Agenzia delle
Entrate → elenco partiti ammessi al due per mille), poi aggiunte a
`config.yaml` una volta confermate. Finché un URL non è configurato per un
anno, gli script si limitano a leggere un file già scaricato manualmente e
salvato in `data/raw/<anno>/` (risultati) o `data/raw/<anno>/codici/`
(elenco/codici) — usando `--no-download`, esattamente come funziona senza
alcuna configurazione di rete.

I parser (CSV, XLSX, PDF) individuano le colonne per alias di nome (es.
"Denominazione"/"Partito", "Numero scelte"/"Scelte", "Importo") invece che
per posizione fissa, per tollerare le variazioni di formato tra un anno e
l'altro delle fonti ufficiali.

## Generazione degli open data

```
php scripts/export_open_data.php
```

Genera in `data/exports/` i seguenti file (CSV con BOM UTF-8 + JSON
equivalente), più un `manifest.json` con data di generazione:

- `2x1000_partiti_risultati.{csv,json}`
- `2x1000_partiti_anagrafica.{csv,json}`
- `2x1000_partiti_codici_annuali.{csv,json}`
- `2x1000_partiti_totali_annuali.{csv,json}`
- `2x1000_partiti_fonti.{csv,json}`

Questi file sono scaricabili dal pubblico tramite la pagina `/open-data.php`,
che li serve attraverso `public/download.php` (whitelist rigorosa sul nome
file, nessun accesso diretto alla cartella `data/`).

## API

API JSON pubbliche, sotto `/api/`:

| Endpoint | Descrizione |
|---|---|
| `GET /api/annual_totals.php[?year=YYYY]` | Totali annuali di sistema (tutti, o per un anno) |
| `GET /api/results.php[?year=YYYY]` | Risultati per partito (tutti gli anni, o un anno) |
| `GET /api/parties.php` | Elenco partiti con ultimo dato disponibile |
| `GET /api/party.php?slug=...` | Scheda completa di un partito (serie storica, alias, codici, fonti) |
| `GET /api/rankings.php?year=YYYY&type=...` | Classifiche (`choices`, `amount`, `avg_amount`, `growth_choices`, `growth_amount`, `decline_choices`, `decline_amount`, `gap_positive`, `gap_negative`, `longest_presence`) |
| `GET /api/compare.php?parties=slug1,slug2,...` | Confronto tra 1-5 partiti |

Tutte le API restituiscono JSON con header corretti e gestiscono gli errori
(parametri mancanti/non validi → 400, risorsa non trovata → 404), senza mai
concatenare l'input utente direttamente in query SQL (uso esclusivo di PDO
con prepared statement).

## Dati demo

Il repository include un set di dati **dimostrativi** (`database/seed.sql`,
`data/processed/parties.csv`, `data/processed/results.csv`) con partiti
denominati "Partito Demo A"..."H" e numeri inventati, marcati esplicitamente
come SAMPLE/DEMO in ogni record (`notes`, `sources.institution = 'DATI DEMO'`).
Servono solo per avere una piattaforma funzionante in sviluppo: **non vanno
mai caricati in produzione** e non rappresentano dati ufficiali reali.

Per popolare l'ambiente di sviluppo:
```
mysql -u <utente> -p <database> < database/schema.sql
mysql -u <utente> -p <database> < database/views.sql
mysql -u <utente> -p <database> < database/seed.sql
php scripts/calculate_indicators.php
php scripts/export_open_data.php
```

## Note metodologiche

Il 2x1000 ai partiti politici non misura il consenso elettorale, il numero
di iscritti o le donazioni private: misura la destinazione volontaria di una
quota dell'IRPEF espressa dai contribuenti in dichiarazione dei redditi.
L'importo medio per scelta è un indicatore aggregato del valore fiscale medio
delle scelte, non il reddito medio di chi effettua la scelta. Il dettaglio
completo (fonti, normalizzazioni, limiti interpretativi) è nella pagina
`/metodo.php` del sito.

## Licenza

Codice: MIT (si veda `LICENSE`). Dataset pubblicati in `/open-data.php`:
Creative Commons Attribuzione 4.0 (CC BY 4.0).

## Fonti e crediti

- Ministero dell'Economia e delle Finanze (MEF) — Dipartimento delle Finanze:
  risultati annuali del 2x1000 ai partiti politici
- Agenzia delle Entrate: elenco dei partiti ammessi e codici da dichiarazione
- Osservatorio ASSIF sul 5, 2 e 8 per mille — progetto e cura editoriale

L'elenco puntuale delle fonti effettivamente caricate nel database è
consultabile nella pagina `/fonti.php` e nel file
`data/exports/2x1000_partiti_fonti.csv`.
