# Financial News Archive Crawler

Outil de collecte d'articles de presse financière historiques à partir de dates spécifiques.
Il récupère les articles, les enrichit avec des données d'archivage, puis les classe par score de pertinence.

---

## Configuration — config.json

```json
{
    "source": "wayback",
    "dates": [
        "2021-10-05",
        "2022-07-05"
    ],
    "top_n": 3
}
```

| Champ | Description |
|-------|-------------|
| `source` | Source principale : `"wayback"` ou `"gdelt"` |
| `dates` | Liste de dates au format `AAAA-MM-JJ` |
| `top_n` | Nombre d'articles à retourner par date |

---

## Sources disponibles

### Wayback Machine (`wayback`) — défaut
- Gratuit, aucune clé API requise
- Scrape les pages archivées de Reuters, CNBC, MarketWatch, Bloomberg
- Idéal pour récupérer les titres tels qu'ils apparaissaient à la date exacte

### GDELT (`gdelt`) — fallback automatique
- Gratuit, aucune clé API requise
- Base de données mondiale d'articles de presse indexés
- Meilleure couverture en volume, moins précis visuellement

> Si une date échoue sur la source principale, le crawler réessaie automatiquement sur l'autre source.

---

## Lancer le crawler

```bash
python main.py
```

### Étapes exécutées automatiquement :
1. Chargement de `config.json`
2. Pour chaque date → fetch des articles via la source principale
3. Dates échouées → retry automatique sur la source de fallback
4. Enrichissement Wayback : compte combien de fois chaque URL a été archivée
5. Calcul du score de pertinence pour chaque article
6. Sauvegarde des résultats dans `output/`

---

## Score de pertinence `[0.000 – 1.000]`

Chaque article reçoit un score entre 0 et 1. Plus le score est élevé, plus l'article est jugé important financièrement.

### Composantes du score

| Composante | Poids (avec captures) | Poids (sans captures) | Description |
|---|---|---|---|
| `financial_keywords` | 30% | 40% | Présence de mots-clés financiers dans le titre |
| `position` | 20% | 30% | Position de l'article dans les résultats bruts |
| `cross_domain` | 15% | 20% | Même sujet couvert par plusieurs sources différentes |
| `us_relevance` | 10% | 10% | Pertinence pour le marché américain |
| `wayback_captures` | 25% | — | Nombre de fois que l'URL a été archivée (popularité) |

### Mots-clés financiers (exemples)

| Tier | Poids | Exemples |
|------|-------|---------|
| Tier 1 — critique | 3.0 | federal reserve, inflation, recession, stock market, S&P 500, FOMC, rate hike |
| Tier 2 — important | 2.0 | bond yield, trade war, tariff, stimulus, bankruptcy, IPO, CPI |
| Tier 3 — général | 1.0 | economy, market, financial, investor, stock, equity |

### Wayback captures
Le nombre de captures Wayback est un indicateur de **popularité au moment de la publication** : un article archivé des milliers de fois était largement partagé et référencé. Ce signal est normalisé sur une échelle logarithmique pour éviter qu'un seul article viral écrase tous les autres.

---

## Résultats

Les fichiers sont sauvegardés dans le dossier `output/` :

| Fichier | Contenu |
|---------|---------|
| `results_[source]_[timestamp].json` | Résultats complets avec score détaillé |
| `results_[source]_[timestamp].csv` | Tableau plat, une ligne par article |

### Colonnes du CSV

| Colonne | Description |
|---------|-------------|
| `date` | Date demandée |
| `rank` | Classement (1 = meilleur) |
| `title` | Titre de l'article |
| `url` | Lien vers l'article |
| `source` | Nom du média |
| `score` | Score final de pertinence |
| `score_keywords` | Sous-score mots-clés |
| `score_position` | Sous-score position |
| `score_cross_domain` | Sous-score multi-sources |
| `score_us` | Sous-score pertinence US |
| `score_captures` | Sous-score captures Wayback |
| `raw_captures` | Nombre brut de captures Wayback |
