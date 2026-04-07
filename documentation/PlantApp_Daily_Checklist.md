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

## 7. Открытые проблемы (обновлять)

- [ ] **Полив**: 63% Medium demand — нет массового источника для раскидывания
- [ ] **Свет**: 40% "Bright indirect light" дефолт
- [ ] **Фото**: 947/4,084 indoor с фото (23%), хранилище ограничено
- [ ] **Имена**: 17,700 не проверены через POWO/GBIF
- [ ] **62 flagged фото** — разобрать вручную
- [ ] **49 water conflicts** — Ellenberg vs MiFloraDB
- [ ] **861 sanity flags** — preset vs demand конфликты
- [ ] **PlantNet DNS** — мониторить https://plantnet.github.io/status/

---

## 8. Что НЕ ДЕЛАТЬ

- Не запускать 20K batch'ей к Turso без разбивки на 500
- Не тратить Perenual credits на дикорастущие (только ID ≤ 3000, проверять локально)
- Не перезаписывать featured данные без проверки
- Не подменять виды (Hoya carnosa ≠ Hoya australis)
- Не затирать source_data и .env
