# PlantApp — Описание проекта

> Последнее обновление: 2026-04-02

---

## 1. Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flutter App     │     │  Сайт           │     │  ESP32 Web UI   │
│  (iOS/Android)   │     │  plantapp.pro   │     │  (AP mode)      │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │  API Gateway (AWS)       │
                    │  p0833p2v29.execute-api  │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     ┌────────┴────────┐ ┌──────┴──────┐ ┌────────┴────────┐
     │ polivalka-auth   │ │ polivalka-  │ │ Turso DB        │
     │ (Lambda)         │ │ api-handler │ │ (SQLite edge)   │
     │ JWT auth         │ │ (Lambda)    │ │ 10K+ растений   │
     └─────────────────┘ └──────┬──────┘ └─────────────────┘
                                │
                         ┌──────┴──────┐
                         │  DynamoDB   │
                         │  devices    │
                         │  rate_limits│
                         └─────────────┘
```

### Стек приложения (Flutter)

```
Flutter (Dart) — ветка: flutter
├── go_router            — навигация
├── flutter_riverpod     — state management
├── dio                  — HTTP клиент
├── camera               — фото / light meter
├── image_picker         — галерея
├── shared_preferences   — локальное хранение
├── flutter_local_notifications — push-уведомления
└── image                — сжатие фото для journal
```

### Бэкенд (Lambda)

Два Lambda: `polivalka-auth` (авторизация) + `polivalka-api-handler` (всё остальное).
Единый API Gateway для всех трёх клиентов.

---

## 2. Структура приложения

```
lib/
├── app/
│   ├── router.dart          — навигация (go_router)
│   └── theme.dart           — цвета, шрифты, spacing
├── constants/
│   ├── api.dart             — API endpoints
│   └── popular_plants.dart  — 6 popular plants (хардкод, legacy)
├── models/
│   ├── auth.dart            — auth models
│   └── plant.dart           — PlantEntry, IdentifyResult, SavePlantInput
├── screens/
│   ├── plant_detail_screen.dart  — карточка растения (17 секций)
│   └── tabs/
│       ├── library_screen.dart   — библиотека (из Turso DB)
│       ├── plants_screen.dart    — мои растения + journal + identify
│       ├── doctor_screen.dart    — AI Doctor (placeholder)
│       └── fleet_screen.dart     — устройства (placeholder)
├── services/
│   ├── api_client.dart           — HTTP + JWT interceptor + auto-login
│   ├── plant_service.dart        — CRUD растений
│   ├── library_service.dart      — поиск в Turso DB
│   ├── geolocation_service.dart  — GPS, сезоны, outdoor months
│   ├── light_meter_service.dart  — Lux → PPFD → DLI
│   ├── journal_service.dart      — фото-дневник
│   └── reminder_service.dart     — push-уведомления полива
├── stores/
│   ├── auth_store.dart           — авторизация (Riverpod)
│   └── settings_store.dart       — настройки (°C/°F, уведомления)
└── widgets/
    ├── light_meter_modal.dart    — камера → измерение света
    └── plant_indicators.dart     — TempRangeBar, HumidityBar, LightLevel
```

---

## 3. Карточка растения — 17 секций

### Структура

```
[Hero Image]
[Name + Scientific name]
[Description + Difficulty + Taxonomy (в развёртке)]
[4 Round Badges: Water, Light, Difficulty, Toxicity]
[Sticky Tabs]

═══ Care ═══
  1. Water — frequency, demand, soil hint, winter, guide
  2. Soil — types, repot, guide
  3. Fertilizing — type, season, NPK, guide

═══ Environment ═══
  4. Light — level, PPFD/DLI, Measure button, guide
  5. Humidity — bar, action, guide
  6. Temperature — range bar, survival limits, guide
  7. Outdoor — months (MonthBar), frost zones, guide

═══ Toxicity ═══
  8. Toxicity — severity, pets/humans, symptoms, first aid, guide

═══ Growing ═══
  9. Pruning — text guide
  10. Harvest — edible parts (greens/fruiting only)
  11. Propagation — methods, detail, guide
  12. Size — height, spread, guide
  13. Lifecycle — type, years, guide

═══ Details ═══
  14. Used for — chips, guide

═══ Companions ═══
  15. Companions — good/bad chips, guide
```

---

## 4. Идентификатор растений (Smart Identify v2)

### Принцип суперпозиции
Несколько источников дополняют друг друга. Если один падает — остальные подхватывают.

### Flow

```
Фото → PlantNet (primary, 500/день бесплатно)
     → Score ≥ 70%: уверены
     → Score < 70%: + SerpAPI Lens (second opinion, 250/мес)
     → PlantNet упал: SerpAPI Lens fallback

Параллельно enrichment:
  → Turso DB (наша база)
  → Trefle (таксономия)
  → Wikipedia (описание)
  → Perenual v2 (care данные)

Кэш enrichment: DynamoDB, TTL 30 дней
```

### Сервисы идентификации

| Сервис | Роль | Лимит | Ключ |
|--------|------|-------|------|
| PlantNet | Primary ID по фото | 500/день | SECRETS.txt |
| SerpAPI Google Lens | Fallback + cross-check | 250/мес | SECRETS.txt |
| Perenual v2 | Care enrichment | 100/день | SECRETS.txt |
| Trefle | Таксономия enrichment | 120/мин | SECRETS.txt |
| Wikipedia | Описания | Безлимит | — |

### Rate limits (пользователи)

| Тип | Identify/день |
|-----|--------------|
| Admin | Безлимит |
| Premium | 20 |
| Free (зарегистрирован) | 3 |
| Anonymous (по IP) | 1 |

### Все API ключи

Единственный источник правды: `/Users/maximshurygin/Polivalka/lambda/SECRETS.txt`
Синхронизируется с: Lambda env variables + `scripts/plant-parser/.env`

---

## 5. База растений

### Хранение

**Turso** (SQLite edge database) — 9 ГБ бесплатно, без кредитной карты.

5 таблиц: `plants` (14 колонок), `care` (37 колонок), `common_names`, `plant_tags`, `external_ids`

### Текущее состояние (2026-04-02)

| Метрика | Значение |
|---------|----------|
| Всего растений | **10,175** |
| Полные care (Perenual) | 63 |
| Каркас + preset (Trefle) | ~10,000 |
| С фотографией | ~8,700 (85%) |
| С описанием | ~674 |
| Xiaomi enrichment | В процессе (~1,000) |

### Источники данных для наполнения

| Источник | Что даёт | Видов | Лимит |
|----------|----------|-------|-------|
| **Perenual v2** | Полные care (50 полей) | 3,000 (free, ID 1-3000) | 100/день |
| **Trefle** | Таксономия, фото | 437,255 | Безлимит |
| **Wikipedia** | Описания | ~20,000 | Безлимит |
| **Xiaomi Flower Care DB** | PPFD, humidity, fertilizing, pruning, temp, soil moisture | 1,000 | Бесплатно, open source |
| **Наши 76 preset семейств** | Базовый care по семейству | Все | — |

### Покрытие секций по источникам

| Секция | Perenual | Xiaomi | Trefle | Wikipedia | Preset |
|--------|----------|--------|--------|-----------|--------|
| Water | ✅ | ✅ | ❌ | ❌ | ✅ |
| Soil | ✅ | ✅ | ❌ | ❌ | ❌ |
| Fertilizing | ❌ | ✅ | ❌ | ❌ | ❌ |
| Light | ✅ | ✅ | ❌ | ❌ | ✅ |
| PPFD/DLI | ❌ | ✅ | ❌ | ❌ | ❌ |
| Humidity | ❌ | ✅ | ❌ | ❌ | ✅ |
| Temperature | ✅ | ✅ | ❌ | ❌ | ✅ |
| Toxicity | ✅ | ❌ | ❌ | ❌ | ❌ |
| Pruning | ✅ months | ✅ text | ❌ | ❌ | ❌ |
| Propagation | ✅ methods | ❌ | ❌ | ❌ | ❌ |
| Difficulty | ✅ | ❌ | ❌ | ❌ | ❌ |
| Size | ✅ | ✅ | ❌ | ❌ | ❌ |
| Lifecycle | ✅ | ✅ | ❌ | ❌ | ❌ |
| Description | ✅ | ✅ | ❌ | ✅ | ❌ |
| Image | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Companions** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Used for** | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Propagation detail** | ❌ | ❌ | ❌ | ❌ | ❌ |

**Незакрытые пробелы:** Companions, Used for, Propagation detail — ни один бесплатный API не даёт. На будущее: ИИ генерация или ручное заполнение.

### Скрипты наполнения

```
cd scripts/plant-parser

python3 sources/perenual_fetcher.py 100     # Perenual: 100/день
python3 sources/trefle_fetcher.py 5000      # Trefle: каркас (безлимит)
python3 sources/wikipedia_fetcher.py 500    # Wikipedia: описания
python3 sources/xiaomi_fetcher.py 1000      # Xiaomi: PPFD, humidity, fertilizing
python3 backup.py                           # JSON backup в git
```

### План наполнения

| Период | Действие | Результат |
|--------|----------|-----------|
| Ежедневно | Perenual +100 | До 3,000 полных за месяц |
| Разово | Trefle каркас | 10,000+ уже сделано |
| Разово | Wikipedia описания | ~700 уже, остальные нет в Wikipedia |
| Разово | Xiaomi enrichment | ~1,000 с PPFD/humidity/fertilizing |
| Будущее | Perenual Premium ($30/мес) | +7,000 полных care |
| Будущее | ИИ генерация | Companions, Used for, Propagation detail |

---

## 6. AI Doctor (планируется)

Диагностика болезней растений по фото. Placeholder в приложении.
Будет включать: Problems & Pests, фото-диагностика, рекомендации лечения.

---

## 7. Монетизация (планируется)

| Уровень | Что входит | Цена |
|---------|-----------|------|
| Free | 5 растений, 3 identify/день, базовые напоминания | $0 |
| Premium Monthly | Безлимит растений, 20 identify/день, офлайн, AI Doctor | $4.99/мес |
| Premium Annual | Всё выше + приоритетная поддержка | $29.99/год |

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-04-02 | Документ создан. Smart Identify v2, база 10K+, Xiaomi enrichment |
