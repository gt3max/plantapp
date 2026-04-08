# PlantApp — Источники данных

> Обновлено: 2026-04-08

---

## ИСПОЛЬЗУЕМ (активные)

| # | Источник | Растений | Что даёт | Доступ | Лимит |
|---|----------|---------|----------|--------|-------|
| 1 | **Trefle** | 437K | Таксономия, family, scientific names | API, free | Безлимит |
| 2 | **POWO (Kew Gardens)** | 362K | Accepted names, synonyms, origin | API, free | Безлимит |
| 3 | **WCVP (Kew Gardens)** | 362K | Lifeform + climate classification | CSV download, free | Одноразово |
| 4 | **Ellenberg Values** | 8K | F (влажность 1-12), L (свет 1-9), T, R, N, S | CSV download, free | Одноразово |
| 5 | **MiFloraDB (Xiaomi)** | 5.3K | lux, soil moisture, temp, humidity (числа) | CSV download, free | Одноразово |
| 6 | **Open Plantbook** | 5K+ | lux, moisture, temp, humidity (числа) | API token, free | 200/день |
| 7 | **Perenual** | 3K (free) | Care guides, propagation, toxicity, size | API key, free tier | 100/день, ID ≤ 3000 |
| 8 | **ASPCA** | ~1K | Toxicity (pets: dogs/cats/horses) | Scrape | Polite delay |
| 9 | **TPPT (Agroscope)** | 844 | Toxicity human + animal + parts + severity | SQLite download, free | Одноразово |
| 10 | **NC State Extension** | ~4K | Light, difficulty, soil, propagation, pests | Scrape | 0.5s delay |
| 11 | **Wikipedia** | ~50K | Descriptions, common names | REST API, free | Polite delay |
| 12 | **Wikidata** | 362K+ | Multilingual names (15 языков) | SPARQL, free | Polite delay |
| 13 | **GBIF** | All species | Scientific name verification | API, free | Безлимит |
| 14 | **iNaturalist** | All observed | Photos (research-grade), taxon verification, CV | API + JWT | CV: безлимит (JWT 24ч) |
| 15 | **USDA PLANTS** | 20K+ | Drought tolerance, wetland indicator | CSV download | Одноразово |
| 16 | **Niinemets & Valladares** | 806 | Drought tolerance 0-5 scale | CSV download, free | Одноразово |
| 17 | **biologiste95** | 60 | Light/watering/humidity scale + Arabic names | XLSX download, free | Одноразово |
| 18 | **GitHub Indoor Dataset** | 119 | Watering/light scale | CSV download, free | Одноразово |
| 19 | **CBIF (Canada)** | 259 | Poisonous plants (human/pet/livestock) | Web | — |
| 20 | **Plant.id (Kindwise)** | — | Photo identification + verification | API key | 64 credits trial |
| 21 | **SerpAPI Google Lens** | — | Photo verification | API key | 250/мес |
| 22 | **Open-Meteo** | — | Weather, temperature by city | API, free | Безлимит |
| 23 | **Cloudinary** | — | Image hosting CDN | 2 accounts, free | 25 credits/мес × 2 |

---

## НЕ ИСПОЛЬЗУЕМ — БЕСПЛАТНЫЕ (подключить)

| # | Источник | Растений | Что даёт | Формат | Статус |
|---|----------|---------|----------|--------|--------|
| 1 | **vrachieru/plant-database** | 800+ | temp/humidity/moisture/soil/fertilizer/pruning | GitHub JSON | Скачан, файл битый — пересчитать |
| 2 | **PFAF (Plants For A Future)** | 8,000 | soil, moisture, propagation, companions, edible | SQLite download | Не скачан |
| 3 | **Companion planting CSVs** | ~200 пар | good/bad companion pairs | GitHub CSV | Не скачан |
| 4 | **Practical Plants wiki** | 7,400 | propagation, companions, cultivation | Semantic MediaWiki | Не парсили |
| 5 | **FloraWeb API (Германия)** | 4,000 | Ellenberg все 7 индикаторов | REST API, free | Не подключен |
| 6 | **Permapeople API** | Large | Companions, soil, light (structured JSON) | REST API, CC BY-SA | Scraper есть, API нет |
| 7 | **RHS Plant Finder** | 250K | Moisture, sunlight, soil, habit | Scrape only | Не парсили |
| 8 | **Missouri Botanical Garden** | 7.5K | Sun, water, maintenance, problems | Scrape only | Не парсили |
| 9 | **TRY Plant Trait Database** | 69K | 52 trait groups (academic) | CSV, free (registration) | Не скачан |
| 10 | **Floriscope (Франция)** | 190K | Agronomic, ecological data | CSV/API (contact) | Не подключен |
| 11 | **GreenSnap (Япония)** | 600 | Structured indoor care | Scrape, Japanese | Не парсили |
| 12 | **iplants.ru (Россия)** | Large | Temp, watering, humidity | Scrape, Russian | Не парсили |
| 13 | **Gartenjournal.net (Германия)** | Large | Structured care | Scrape, German | Не парсили |

---

## НЕ ИСПОЛЬЗУЕМ — ПЛАТНЫЕ (на будущее)

| # | Источник | Растений | Что даёт | Цена |
|---|----------|---------|----------|------|
| 1 | **Perenual Premium** | 10K+ | Всё care (свет, полив, soil, propagation, size, toxicity) | $79/год |
| 2 | **Green Solutions (Германия)** | 75,000 | Всё + soil 12 атрибутов + companions + difficulty | На запрос |
| 3 | **APIFarmer** | 100,000 | temp/pH/fertility/drought/height | 11€ первый мес, потом 99€/мес |
| 4 | **RapidAPI House Plants** | 300+ | temp/light/watering structured | Free tier + paid |

---

## МЁРТВЫЕ / НЕДОСТУПНЫЕ

| Источник | Причина |
|----------|---------|
| **PlantNet API** | DNS мёртв с 2026-04-03. Мониторить: https://plantnet.github.io/status/ |
| **OpenFarm** | Закрыт апрель 2025. Data dump утерян |
| **Parrot Flower Power** | Cloud закрыт. База ~6K растений утеряна |
| **FDA Poisonous Plants DB** | Деактивирован январь 2022 |

---

## КАКИЕ СЕКЦИИ ПОКРЫВАЕТ КАЖДЫЙ ИСТОЧНИК

| Секция | Активные источники | Потенциальные |
|--------|-------------------|---------------|
| **Water** | Ellenberg F, MiFloraDB, Open Plantbook, Perenual | PFAF, vrachieru |
| **Light** | Ellenberg L, MiFloraDB, Open Plantbook, NC State | FloraWeb, vrachieru |
| **Humidity** | Open Plantbook, MiFloraDB | vrachieru |
| **Temperature** | Open Plantbook, MiFloraDB, WCVP climate | vrachieru, FloraWeb |
| **Toxicity** | ASPCA, TPPT, family rules, CBIF | — |
| **Soil** | NC State, Perenual (text) | PFAF, Green Solutions |
| **Fertilizing** | Perenual (text), MiFloraDB (EC) | vrachieru |
| **Pruning** | Perenual (text) | vrachieru, Practical Plants |
| **Propagation** | Perenual, NC State, Permapeople | PFAF, Practical Plants |
| **Difficulty** | NC State, Perenual | — |
| **Size** | Perenual, NC State | APIFarmer |
| **Companions** | Permapeople | PFAF, Practical Plants, companion CSVs |
| **Lifecycle** | WCVP lifeform, Trefle duration | — |
| **Taxonomy** | WCVP, Trefle, POWO | — |
| **Photos** | iNaturalist (research-grade) → Cloudinary | — |
| **Names** | POWO, GBIF, Wikipedia, Wikidata, iNaturalist | — |
| **Descriptions** | Wikipedia | — |
