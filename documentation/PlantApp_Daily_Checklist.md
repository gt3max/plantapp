# PlantApp — Daily Checklist

> Обновлять в начале каждой рабочей сессии. Дополнять по мере появления новых задач.

---

## 1. Токены и credentials

| Что | Где обновить | Срок жизни | Как |
|-----|-------------|------------|-----|
| iNaturalist JWT | `.env` → `INATURALIST_API_TOKEN` | 24 часа | https://www.inaturalist.org/users/api_token → скопировать |
| Perenual API | не меняется | постоянный | — |
| Plant.id API | не меняется | 30 дней trial | — |
| Cloudinary (оба) | не меняется | постоянный | — |

---

## 2. Ежедневные credits (использовать!)

| Сервис | Лимит | Скрипт | Приоритет |
|--------|-------|--------|-----------|
| **Perenual** | 100 req/день | `perenual_smart_check.py` | Конфликтные → featured → indoor |
| **iNaturalist CV** | безлимит (с JWT) | `verify_photos_batch.py` | Новые фото, непроверенные |
| **SerpAPI Google Lens** | 250/мес | ручной | Выборочная проверка фото |

---

## 3. Проверить фоновые процессы

```bash
# Сколько процессов работает
ps aux | grep python3 | grep -v grep | grep -v Dropbox | wc -l

# Статус каждого (tail output файлов)
```

- Какие завершились? Результат?
- Какие упали? Причина? Перезапустить?
- Новые конфликты появились?

---

## 4. Хранилище (Cloudinary)

```bash
# Credentials in .env — never hardcode here!
# Account 1
python3 -c "import os; from pathlib import Path; [os.environ.setdefault(k.strip(),v.strip()) for k,v in (l.split('=',1) for l in Path('.env').read_text().splitlines() if '=' in l and not l.startswith('#'))]; import urllib.request,json; r=urllib.request.urlopen(urllib.request.Request(f'https://api.cloudinary.com/v1_1/{os.environ[\"CLOUDINARY_CLOUD_NAME\"]}/usage',headers={'Authorization':'Basic '+__import__('base64').b64encode(f'{os.environ[\"CLOUDINARY_API_KEY\"]}:{os.environ[\"CLOUDINARY_API_SECRET\"]}'.encode()).decode()})); d=json.loads(r.read()); c=d.get('credits',{}); print(f'Acc1: {c.get(\"usage\",0):.1f}/{c.get(\"limit\",0):.0f}')"

# Account 2 — same approach with CLOUDINARY2_* vars
```

---

## 5. Git

- [ ] `git add` изменённые файлы
- [ ] `git commit -m "описание"`
- [ ] `git push origin flutter`

---

## 6. Статус базы (быстрая проверка)

```bash
cd /Users/maximshurygin/plantapp/scripts/plant-parser
python3 -c "
from turso_sync import turso_query
print('Plants:', turso_query('SELECT COUNT(*) as c FROM plants')[0]['c'])
print('Photos:', turso_query('SELECT COUNT(DISTINCT plant_id) as c FROM plant_images')[0]['c'])
print('Flagged photos:', turso_query(\"SELECT COUNT(DISTINCT plant_id) as c FROM plant_images WHERE image_type='flagged'\")[0]['c'])
print('Medium demand:', turso_query(\"SELECT COUNT(*) as c FROM care WHERE water_demand='Medium'\")[0]['c'])
print('Bright indirect:', turso_query(\"SELECT COUNT(*) as c FROM care WHERE light_preferred='Bright indirect light'\")[0]['c'])
print('Conflicts:', turso_query(\"SELECT COUNT(DISTINCT plant_id) as c FROM source_data WHERE source='conflict'\")[0]['c'])
"
```

---

## 7. Открытые проблемы (обновлено 2026-04-08)

### Полив
- [ ] **58% Medium demand** (11,794/20,261) — нет массового источника. Lifeform+climate раскидали часть, но 58% осталось
- [ ] **49 water conflicts** (Ellenberg vs MiFloraDB) — помечены, не разобраны
- [ ] **10 sanity flags** — lifeform vs demand (было 861, пересчитано с WCVP)
- [ ] **watering_avoid**: 4,181 (20%) — остальные пусто

### Свет
- [ ] **33% "Bright indirect light"** (6,774) — дефолт без данных
- [ ] **PPFD**: 53% заполнен, 47% нет
- [ ] **Hours**: 45% рассчитан
- [ ] **Daylight calculator** готов в GeolocationService — не в UI

### Токсичность
- [ ] **85% unknown** (~17K) — нет данных ни из одного источника
- [ ] ASPCA ~1K + TPPT ~700 + family ~1,600 = ~3,000 с данными

### Фото
- [ ] **960 растений с фото** из 20K (5%), загружаются ещё 240
- [ ] **62 + ~130 flagged/mismatch** — не разобраны
- [ ] **~1,300 error** при верификации (iNat CV timeout) — не проверены
- [ ] Cloudinary usage API не работает с новыми ключами

### Описания
- [ ] **33% без описания** (~6,700) — Wikipedia статей не существует

### Имена
- [ ] **~6,700 не проверены** через POWO/GBIF (~13,500 проверены, 0 flagged)
- [ ] **53% common name = копия scientific** (нет народного имени)

### Классификация
- [ ] **15% без WCVP** (~2,900) — гибриды/культивары, fallback по семейству

### Инфраструктура
- [ ] **PlantNet DNS мёртв** — мониторить https://plantnet.github.io/status/
- [ ] **iNaturalist JWT** — обновлять ежедневно
- [ ] **Cloudinary usage endpoint** — permissions не настроены

---

## 8. Что НЕ ДЕЛАТЬ

- Не запускать 20K batch'ей к Turso без разбивки на 500
- Не тратить Perenual credits на дикорастущие (только ID ≤ 3000, проверять локально)
- Не перезаписывать featured данные без проверки
- Не подменять виды (Hoya carnosa ≠ Hoya australis)
- Не затирать source_data и .env
