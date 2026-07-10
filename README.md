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
  models/                  Party, Result, AnnualTotal, Source, RegionalResult (query PDO)
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
  acquire_results.py           Scarica/estrae i risultati annuali dal MEF
  acquire_party_codes.py       Scarica/estrae elenco partiti ammessi e codici dall'AdE
  acquire_regional_results.py  Scarica/estrae la ripartizione regionale delle scelte dal MEF
  db_updater.py                Scrive i dati normalizzati nel database MySQL
  add_party_alias.py           Registra una grafia alternativa per un partito esistente
  find_duplicate_parties.py    Segnala possibili duplicati nell'anagrafica partiti
  merge_parties.py             Unisce due righe duplicate dell'anagrafica in una sola
  pipeline.py                  Orchestratore: acquisizione → DB → indicatori → export
  config.yaml                  URL per anno delle fonti ufficiali (da compilare)
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
   Se il database esisteva già da prima di una modifica allo schema (es.
   l'aggiunta della tabella `regional_results`), esegui anche
   `database/migrations.sql`: `schema.sql` usa `CREATE TABLE IF NOT EXISTS`
   quindi crea le tabelle nuove ma non altera quelle già esistenti (es. i
   valori di un ENUM), motivo per cui le migrazioni sono in un file a parte.
   ```
   mysql -u <utente> -p <database> < database/migrations.sql
   ```
6. **Popola il database con i dati reali.** Due percorsi possibili:
   - **Consigliato:** la [pipeline Python](#pipeline-python-di-acquisizione-dati),
     che scarica dalle fonti ufficiali, normalizza e scrive nel database in
     un solo comando per anno — è il percorso testato end-to-end in
     produzione;
   - **Alternativo:** [import manuale via CSV](#importazione-dei-dati), utile
     se hai già i dati normalizzati in un foglio di calcolo o se preferisci
     controllare a mano ogni riga prima di importarla.

   In entrambi i casi, il calcolo degli indicatori (`calculate_indicators.php`)
   va sempre rieseguito dopo ogni import (la pipeline Python lo fa da sola).
7. **Genera gli open data:** `php scripts/export_open_data.php` (anche questo
   incluso in automatico se hai usato la pipeline Python).
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
3. `acquire_regional_results.py` scarica/estrae la tabella di ripartizione
   regionale delle scelte (regione × partito, pubblicata dal MEF sullo
   stesso portale con nodo `...AADUEXM0201` invece di `...0101`) e la
   normalizza in `data/processed/regional_results_<anno>.csv`;
4. `db_updater.py` scrive questi CSV normalizzati nel database (`sources`,
   `parties`, `results`, `party_codes`, `regional_results`), con upsert
   idempotenti — ogni fonte viene registrata una sola volta (deduplicata per
   checksum SHA-256), ogni partito individuato per slug con
   `first_year`/`last_year` estesi automaticamente;
5. `pipeline.py` richiama infine `scripts/calculate_indicators.php` e
   `scripts/export_open_data.php` (gli stessi script PHP usati per l'import
   manuale), così i numeri restano identici indipendentemente dal percorso
   di import scelto — non esiste una seconda implementazione dei calcoli in
   Python da mantenere sincronizzata con quella PHP.

**Ripartizione regionale e nomi partito non riconosciuti:** a differenza di
`acquire_results.py`/`acquire_party_codes.py` (che riportano un `code`
ufficiale AdE), la tabella regionale del MEF intesta le colonne solo con il
**nome** del partito. `db_updater.py` risolve ogni nome a un `party_id`
cercandolo (in ordine) tra `parties.canonical_name`, `party_codes.official_name`
e `party_aliases.alias_name` (tutti confrontati via `slugify()`, insensibile
ad accenti/maiuscole/punteggiatura). I nomi che non trovano corrispondenza
**non creano un nuovo partito automaticamente**: la riga viene scartata e il
nome elencato a fine esecuzione, con il comando pronto da lanciare:
```bash
python add_party_alias.py --party <slug-partito-corretto> --alias "Nome esatto non riconosciuto"
```
poi rilancia `db_updater.py` per quell'anno: la riga verrà risolta. Non è
stata creata una tabella separata per le grafie alternative (proposta
iniziale: `Codice, Nome, Tipo`) perché il progetto ha già `party_aliases`
con lo stesso scopo (denominazione alternativa → `party_id`, con
`year_from`/`year_to`/`source`) — usarla evita due fonti di verità sullo
stesso concetto.

**Popolamento massivo per più anni:** una volta verificati gli URL (si veda
sotto), la sequenza usata in produzione per un primo caricamento di più anni
insieme è:
```bash
python acquire_results.py --anni 2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025
python acquire_party_codes.py --anni 2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025
python acquire_regional_results.py --anni 2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025
python db_updater.py --anni 2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025
php ../scripts/calculate_indicators.php
php ../scripts/export_open_data.php
```
(`pipeline.py --anni <lista>` fa lo stesso in un solo comando, anno per
anno). Alla fine controlla sempre l'ultima riga di log di `db_updater.py`:
se elenca nomi non riconosciuti, risolvili con `add_party_alias.py` come
sopra e rilancia solo `db_updater.py` (non serve riscaricare).

Una volta scritta in `regional_results`, la ripartizione regionale compare
automaticamente sul sito, senza nessuna azione aggiuntiva:
- sulla scheda di ciascun partito (`/partito.php?slug=...`, sezione
  "Ripartizione regionale delle scelte": selettore anno, grafico a barre per
  regione, tabella con le quote) e nella relativa API
  (`/api/party.php?slug=...`, chiave `regional_results`);
- sulla pagina `/regioni.php` (selettore anno, totale scelte per regione,
  partito più scelto in ciascuna, link alla classifica completa);
- come filtro "Regione" in `/classifiche.php`: se impostato, la sezione
  "Più scelti" usa i dati regionali invece di quelli nazionali (le altre
  classifiche — importo, crescita, concentrazione — restano nazionali,
  perché la fonte regionale copre solo il numero di scelte). Stesso filtro
  disponibile in `/api/rankings.php?type=choices&year=YYYY&region=...`.

**Pulizia dell'anagrafica (partiti duplicati):** capita che lo stesso
partito reale finisca su due righe distinte di `parties` — tipicamente
perché in anni diversi la fonte ha usato una grafia leggermente diversa
(es. con/senza sigla) e l'euristica di risoluzione dei nomi non li ha
accorpati. Per trovarli:
```bash
python find_duplicate_parties.py
```
Segnala i candidati su tre livelli di confidenza (stesso codice AdE
condiviso tra anni = alta; nome uguale a meno della punteggiatura = media;
similarità testuale ≥95% = bassa, da rivedere a mano). Prima di unire due
righe, se hanno entrambe un `code` AdE, vale la pena controllare se
condividono anche un anno con lo stesso codice (`SELECT declaration_year,
code FROM party_codes WHERE party_id IN (id1, id2) ORDER BY declaration_year`):
se sì, è quasi certamente lo stesso partito. Poi:
```bash
python merge_parties.py --keep <slug-da-mantenere> --merge <slug-duplicato> --dry-run
# se l'anteprima torna, rilancia senza --dry-run
python merge_parties.py --keep <slug-da-mantenere> --merge <slug-duplicato>
```
Sposta risultati e codici sotto il partito mantenuto, registra il nome del
duplicato come alias storico, estende `first_year`/`last_year`. Se per lo
stesso anno esistono righe su entrambi i partiti (un vero conflitto, non
solo un doppione), **non le sovrascrive**: le segnala e non elimina la riga
duplicata finché non risolvi il conflitto a mano (confronta le due righe,
tieni quella corretta, elimina l'altra, poi il partito duplicato — ormai
vuoto — può essere cancellato). Dopo un merge, rilancia sempre
`calculate_indicators.php` e `export_open_data.php`, perché classifiche e
conteggi possono essere cambiati.

**Configurazione delle fonti:** `python/config.yaml` contiene `url_anni_risultati`
(Dipartimento delle Finanze), `url_anni_codici` (Agenzia delle Entrate) e
`url_anni_geografia` (ripartizione regionale, Dipartimento delle Finanze).
Gli URL per gli anni 2015-2025 sono precompilati e **verificati in produzione**
(scaricati con successo per tutti e tre i tipi di fonte). Per un anno nuovo,
non ancora presente in `config.yaml` (es. 2026), non dare per scontato che il
pattern funzioni identico: verifica sempre un anno alla volta prima di un
import massivo:
```bash
python acquire_results.py --anni 2026
python acquire_party_codes.py --anni 2026
python acquire_regional_results.py --anni 2026
```
e controlla il contenuto di `data/processed/mef_results_2026.csv` /
`ade_codes_2026.csv` / `regional_results_2026.csv`. Se il file scaricato non
è quello giusto o il parser non trova le colonne, apri l'URL nel browser per
trovare quello corretto e aggiorna `config.yaml`. Per gli anni non ancora
configurati, gli script si limitano a leggere un file scaricato manualmente e
salvato in `data/raw/<anno>/` (risultati), `data/raw/<anno>/codici/`
(elenco/codici) o `data/raw/<anno>/geografia/` (ripartizione regionale),
usando `--no-download`.

Nota per gli anni 2016/2020 di `url_anni_codici`: i due URL puntano allo
stesso file AdE — se l'Agenzia ne pubblica uno nuovo per uno dei due anni,
aggiorna il link corrispondente.

Un URL può essere sia una pagina HTML da scansionare per trovare i link ai
file, sia un link diretto a un file (PDF/CSV/XLSX, anche con l'estensione a
metà del path come nei link dell'Agenzia delle Entrate): `fetch_source_file()`
in `extract.py` gestisce entrambi i casi automaticamente.

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
| `GET /api/party.php?slug=...` | Scheda completa di un partito (serie storica, ripartizione regionale, alias, codici, fonti) |
| `GET /api/rankings.php?year=YYYY&type=...` | Classifiche (`choices`, `amount`, `avg_amount`, `growth_choices`, `growth_amount`, `decline_choices`, `decline_amount`, `gap_positive`, `gap_negative`, `longest_presence`). Con `type=choices` accetta anche `region=...` per la classifica regionale |
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
