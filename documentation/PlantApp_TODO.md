# PlantApp — TODO / Feedback Notes

> Обновлено: 2026-04-03

---

## НАПОЛНЕНИЕ БАЗЫ — ЕЖЕДНЕВНЫЙ ПЛАН

### Скрипты
```
cd scripts/plant-parser
python3 sources/perenual_fetcher.py 100     # Perenual: 100/день (лимит API)
python3 sources/trefle_fetcher.py 5000      # Trefle: каркас (безлимит)
python3 sources/wikipedia_fetcher.py 500    # Wikipedia: описания
python3 sources/xiaomi_fetcher.py 1000      # Xiaomi: PPFD, humidity, fertilizing
python3 sources/ncstate_fetcher.py 2000     # NC State: научные care данные
python3 backup.py                           # JSON backup в git
```

### Текущее состояние базы (03.04.2026)

| Метрика | Значение |
|---------|----------|
| Всего растений | **10,206** |
| 17/17 полей (полные) | **6** |
| 11-14 полей | ~15 |
| 8-10 полей | ~364 |
| 5-7 полей (каркас) | ~8,400 |
| С фото | 8,772 (86%) |
| С описанием | 707 (7%) |
| Бэкап | data/plants/ — 394 JSON, 17 МБ |

### Источники данных

| Источник | Записей | Что даёт | Лимит |
|----------|---------|----------|-------|
| Perenual v2 | 96 | Полные care (50 полей) | 100/день, max 3,000 free |
| Trefle | 10,088 | Каркас: название, семейство, фото | Безлимит |
| Xiaomi DB | 862 | PPFD, humidity, fertilizer, pruning, temp | Разово, 1,000 |
| Wikipedia | 707 | Описания | Безлимит |
| NC State Extension | ~57+ (работает) | Научные: light, difficulty, propagation, insects/diseases, growth | Парсинг, 5,000 |
| Permapeople | 100 | Propagation detail, used for, edibility | Пагинация сломана, ждём |
| POWO (Kew) | — | Климат, distribution | API бесплатный |

### Ежедневный ритуал
1. `python3 sources/perenual_fetcher.py 100` — новые 100 полных care
2. `python3 sources/ncstate_fetcher.py 500` — научные данные для существующих
3. `python3 backup.py` — бэкап в git
4. `git add data/plants/ && git commit && git push`

---

## TODO (по приоритету)

### 1. Insects & Diseases — собирать данные СЕЙЧАС
- NC State даёт insects_diseases для каждого растения
- Perenual даёт pest_susceptibility
- Нужно: **разделить на insects и diseases отдельно** в базе
- Данные пригодятся для AI Doctor
- Сейчас всё в common_problems/common_pests — нужна структура
- Рассмотреть: отдельная таблица `plant_diseases` в Turso

### 2. Панель мониторинга (Admin Dashboard)
- Страница на сайте (plantapp.pro/admin)
- Статус сервисов, расход лимитов, ошибки
- Объём базы, % заполненности
- Количество пользователей, identify за день

### 3. Перепроверка данных 6 popular plants
- Сверить с Perenual (завтра, когда лимит сбросится)
- Сверить с NC State
- Записать расхождения если есть

### 4. Офлайн identify (Premium фича)
- Встроенная нейросеть PlantNet-300K TFLite (~100 MB, 1,081 вид)
- Работает без интернета

### 5. Фото растений — карусель
- Несколько фото (как у Planta — swipe, zoom)
- Perenual даёт other_images[]
- Фото увеличение по тапу (сделано v4.12.1)

### 6. UI identify результатов
- Кнопка save — отдельная, не по тапу на фото
- Несколько фото в результате

### 7. Data Sources в Settings
- ✅ Добавлено (v4.12.4): PlantNet, Perenual, Trefle, Wikipedia, Permapeople, Xiaomi, SerpAPI, NC State, POWO

### 8. Auth / Логин
- Dev auto-login, не трогать до релиза
- Позже: нормальные аккаунты

### 9. Permapeople пагинация
- 9,032 растения на сайте, API отдаёт только 100
- Написать им / попробовать другой формат запроса
- Если починят — propagation detail + used for для тысяч

---

## ВЫПОЛНЕНО ✅

- About → Details, Difficulty/Taxonomy в развёртку (2026-04-01)
- "Companion data coming soon" убрано (2026-04-01)
- API ключи синхронизированы (2026-04-01)
- Smart Identify v2 (2026-04-02)
- Library → Turso DB (2026-04-02)
- Perenual fetcher (2026-04-02)
- Trefle fetcher — 10K каркас (2026-04-02)
- Wikipedia fetcher (2026-04-02)
- Xiaomi enrichment — 862 растения (2026-04-02)
- 6 popular plants полные 17/17 в Turso (2026-04-02)
- Perenual resume fix (2026-04-03)
- NC State parser (2026-04-03)
- Data Sources в Settings (2026-04-03)
- Бэкап базы — data/plants/ (2026-04-03)
