# PlantApp — TODO / Feedback Notes

## ВЫПОЛНЕНО ✅

### About group → Details (2026-04-01) ✅
- Переименовано About → Details
- Difficulty и Taxonomy перенесены в развёртку описания
- Used for guide: "About this plant" → "Uses & benefits"

### "Companion data coming soon" (2026-04-01) ✅
- Убрано. Для popular plants companions показываются, для остальных — пусто (как в RN)

### API ключи (2026-04-01) ✅
- Все 6 ключей синхронизированы: SECRETS.txt = Lambda = parser .env
- PlantNet, SerpAPI, Perenual, Trefle, Turso, JWT — все проверены

### Smart Identify v2 (2026-04-02) ✅
- PlantNet primary + SerpAPI Lens при low confidence/fallback
- Enrichment: Turso + Trefle + Wikipedia + Perenual (v2 API) — все 5 работают
- Кэш enrichment (DynamoDB, TTL 30 дней)
- Rate limits: free=3/день, anon=1/день
- Backwards compatible с сайтом

### Library → Turso DB (2026-04-02) ✅
- Library показывает растения из Turso вместо 6 хардкоженных
- Картинки от Perenual (не Wikimedia)
- Масштабируется автоматически с ростом базы

### Perenual fetcher (2026-04-02) ✅
- perenual_fetcher.py написан и протестирован
- 85 растений в базе (63 из Perenual + 22 старых)

---

## НАПОЛНЕНИЕ БАЗЫ — ЕЖЕДНЕВНЫЙ ПЛАН

### Скрипты
```
cd scripts/plant-parser
python3 sources/perenual_fetcher.py 100     # Perenual: 100/день (лимит API)
python3 sources/trefle_fetcher.py 5000      # Trefle: каркас (безлимит) — TODO написать
python3 sources/wikipedia_fetcher.py        # Wikipedia: описания — TODO написать
python3 populate.py --stats                 # Статистика — TODO написать
python3 backup.py                           # JSON backup в git
```

### График наполнения

| День | Действие | Результат |
|------|----------|-----------|
| **02.04 (сегодня)** | Perenual 63 растения ✅ | 85 в базе |
| **03.04** | Perenual +100, Trefle каркас +5000 | ~5,185 |
| **04.04** | Perenual +100, Wikipedia описания | ~5,285 |
| **05.04** | Perenual +100 | ~5,385 |
| **06.04** | Perenual +100 | ~5,485 |
| **07.04** | Perenual +100 | ~5,585 |
| **Неделя 2** | Perenual +700, Trefle +20,000 | ~26,000 |
| **Неделя 3** | Perenual +700 | ~27,000 |
| **Неделя 4** | Perenual +700, завершение 3,000 free | ~28,000+ |
| **Месяц 2** | Trefle до 100,000 каркас | 100,000+ |

### Что ещё нужно написать
- [ ] `sources/trefle_fetcher.py` — bulk import таксономии (каркас + preset care)
- [ ] `sources/wikipedia_fetcher.py` — рефакторинг из enrich_descriptions.py
- [ ] `populate.py` — главный скрипт с флагами --perenual, --trefle, --wikipedia, --stats, --backup
- [ ] Запоминание прогресса (последняя страница) для возобновления

### Текущее состояние базы
- **85 растений** в Turso (63 Perenual + 22 старых)
- **Perenual лимит:** исчерпан на 02.04, сброс завтра
- **Trefle:** не начат (fetcher не написан)
- **Wikipedia:** 25 описаний (из старого seed)

---

## TODO (по приоритету)

### 1. Наполнение базы — скрипты
- [x] perenual_fetcher.py — написан, работает
- [ ] trefle_fetcher.py — каркас 50,000+
- [ ] wikipedia_fetcher.py — описания
- [ ] populate.py — единый скрипт

### 2. Панель мониторинга (Admin Dashboard)
- Страница на сайте (plantapp.pro/admin)
- Статус сервисов, расход лимитов, ошибки
- Объём базы, % заполненности, свободное место в Turso
- Количество пользователей, identify за день

### 3. Офлайн identify (Premium фича)
- Встроенная нейросеть PlantNet-300K TFLite (~100 MB, 1,081 вид)
- Работает без интернета

### 4. Фото растений — карусель
- Несколько фото (как у Planta — swipe, zoom, рассматривать листья)
- Perenual даёт other_images[] — несколько фото на растение
- Фото увеличение по тапу (сделано для identify v4.12.1)

### 5. UI identify результатов
- Кнопка save — отдельная, не по тапу на фото
- Несколько фото в результате

### 6. Auth / Логин
- Dev auto-login, не трогать до релиза
- Позже: нормальные аккаунты
