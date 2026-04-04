# PlantApp — TODO / Полный список задач

> Обновлено: 2026-04-03

---

## 🔴 КРИТИЧНОЕ (блокирует релиз)

### База растений
- [ ] Завершить текущие 7 процессов обогащения
- [ ] Cross-check качества на 10 популярных растениях (verify.py)
- [ ] Perenual ежедневно +100 до 3,000 (месяц)
- [ ] Missouri BG полный проход 8,000 (несколько ночей)
- [ ] Проблемные поля: companions, used_for, PPFD — решение после исчерпания бесплатных

### Идентификатор → База связка
- [ ] Проверить: identify растение → карточка из Turso → все секции отображаются?
- [ ] Что показывается если растения нет в базе? Достаточно ли preset?
- [ ] Enrichment при identify — Turso + Trefle + Wikipedia + Perenual работает?

### Монетизация
- [ ] Определить модель: Free (3 identify/день, 5 растений) vs Premium ($4.99/мес)
- [ ] Что за paywall: AI Doctor, офлайн, безлимит растений, безлимит identify?
- [ ] StoreKit / RevenueCat интеграция
- [ ] Manage Subscription в Settings (наш принцип — не прятать)
- [ ] Trial: "7 days free, NO charge until day 8"

### App Store / Google Play — подготовка к ревью
- [ ] Apple Developer Program ($99/год) — зарегистрироваться
- [ ] Google Play Console ($25) — зарегистрироваться

**До подачи на ревью (Apple очень строгие, реджект с 1-го раза — норма):**
- [ ] App Icon (1024x1024 + adaptive для Android)
- [ ] Splash Screen
- [ ] Screenshots для App Store (6.7", 6.5", 5.5") — на каждом языке
- [ ] App Store description + keywords (ASO) — на каждом языке
- [ ] Privacy Policy страница на plantapp.pro (ОБЯЗАТЕЛЬНО, без неё = реджект)
- [ ] Terms of Service страница
- [ ] Возрастной рейтинг (заполнить анкету Apple)
- [ ] Категория в App Store: Lifestyle или Education

**TestFlight бета (минимум 2 недели до подачи):**
- [ ] Внутреннее тестирование (мы + друг)
- [ ] Внешнее тестирование (10-20 человек)
- [ ] Crash-free rate > 99%
- [ ] Все экраны работают без ошибок
- [ ] Identify работает стабильно
- [ ] Все карточки растений отображаются корректно

**Типичные причины реджекта (готовиться заранее):**
- [ ] Crashes при ревью → TestFlight + Crashlytics
- [ ] "Not enough content" → база должна быть заполнена, не пустые экраны
- [ ] IAP не через StoreKit → подписки ТОЛЬКО через Apple
- [ ] Login required без гостевого доступа → обеспечить guest mode или demo
- [ ] Broken links → проверить все URL (privacy policy, support email)
- [ ] Placeholder content → убрать все "Coming soon", "TODO", placeholder
- [ ] Missing functionality → AI Doctor placeholder = потенциальный реджект, либо убрать либо пометить "Future update"
- [ ] Camera/Location permissions → объяснить зачем (Light Meter, Geolocation)
- [ ] IPv6 compatibility → Lambda/API должен работать через IPv6
- [ ] Dark mode → хотя бы не ломаться в dark mode

**После подачи:**
- [ ] Ожидание: 24-48 часов (первая подача до 7 дней)
- [ ] При реджекте: читаем feedback, фиксим, подаём снова
- [ ] Может потребоваться 3-5 итераций

---

## 🟡 ВАЖНОЕ (нужно до релиза)

### Приложение — UI/UX
- [ ] Identify результаты: кнопка save отдельно от фото
- [ ] Identify: несколько фото в результате (API даёт 3)
- [ ] Фото карусель на карточке растения (Perenual other_images)
- [ ] Library: cold start Lambda 2-3 сек — показать skeleton/loader
- [ ] Popular plants хардкод — убрать из кода (данные уже в Turso)
- [ ] Пустые секции — скрывать или показывать "No data"?

### Android
- [ ] Протестировать на Android устройстве
- [ ] Проверить все экраны
- [ ] Camera / Light Meter на Android
- [ ] Push notifications на Android

### Бэкенд
- [ ] Deploy script (deploy_lambdas.py) сбрасывает TURSO_AUTH_TOKEN — починить
- [ ] Lambda warmup ping (CloudWatch Events каждые 5 мин) — бесплатно

### Качество данных
- [ ] verify.py — скрипт перепроверки (запрос всех источников заново, сравнение с Turso)
- [ ] Перепроверка 6 popular plants с Perenual + NC State + Missouri BG
- [ ] Insects vs Diseases — разделение работает, проверить корректность

### Data Sources
- [x] 12 источников в Settings
- [ ] Attribution links на сайте (plantapp.pro/about или footer)

---

## 🟢 ПОСЛЕ РЕЛИЗА

### AI Doctor
- [ ] Диагностика болезней по фото (Plant.id Health Assessment API или Claude Vision)
- [ ] Problems & Pests раздел (данные собираем уже — NC State, GardenersWorld, ASPCA)

**Каталог болезней/вредителей (disease_catalog):**
- [ ] Таблица `disease_catalog`: name, type (pest/disease), image_url, description, symptoms, treatment
- [ ] ~30-50 основных записей (Aphids, Spider mites, Root rot, Powdery mildew, Mealybugs, etc.)
- [ ] Фото из Wikipedia Commons (19/20 есть, бесплатные, open license)
- [ ] Описание + симптомы из Wikipedia API
- [ ] Лечение — дополнить из NC State / GardenersWorld / ручная курация
- [ ] Связь с растениями через common_pests / common_problems (уже парсим)
- [ ] НЕ нужны отдельные фото для каждого растения — тля одинаковая на всех

### История ухода
- [ ] Кнопка "Я полил" на карточке растения
- [ ] Запоминание: когда полил, удобрил, пересадил
- [ ] Timeline ухода за растением
- [ ] Напоминание: "Пора полить — последний раз X дней назад"
- [ ] Связка с reminders

### Офлайн
- [ ] Identify: PlantNet-300K TFLite модель (~100 MB, 1,081 вид)
- [ ] База на устройстве (Premium): SQLite ~300 МБ
- [ ] Работает без интернета

### Admin Dashboard
- [ ] Страница на сайте (plantapp.pro/admin)
- [ ] Статус сервисов (PlantNet ✅/❌, SerpAPI, etc.)
- [ ] Расход лимитов (PlantNet 45/500, SerpAPI 12/250)
- [ ] Объём базы, % заполненности, свободное место Turso
- [ ] Количество пользователей, identify за день
- [ ] Ошибки за 24ч

### Расширение базы
- [ ] Perenual Premium ($30/мес) → +7,000 с полным care
- [ ] ИИ генерация (companions, used_for, PPFD) → $0.40/3,000 растений
- [ ] Trefle до 100K каркас
- [ ] PPFD из научной литературы для топ-100

### Локализация (12-15 языков)
- [ ] Flutter intl + flutter_localizations
- [ ] UI тексты (~200 строк) на все языки
- [ ] Языки: English, Russian, German, Spanish, French, Portuguese, Italian, Chinese, Japanese, Korean, Turkish, Arabic, Hindi, Polish, Dutch
- [ ] App Store listing на каждом языке
- [ ] Описания растений — английский по умолчанию, переводить по мере роста

### Функции
- [ ] Группировка растений (Sites) — Принцип 4
- [ ] Vacation mode
- [ ] Community features
- [ ] Shared care (семья)
- [ ] Weather-based watering adjustments

---

## ТЕКУЩИЕ ПРОЦЕССЫ (04.04, ночь)

| Процесс | Статус | Что делает | Hit rate |
|---------|--------|-----------|----------|
| NC State (20,000) | 🔄 **search-based** | difficulty, growth, height, soil, pests, problems, propagation, origin, pH, edibility | **100%** (search API) |
| POWO (10,000) | 🔄 работает | origin, order, synonyms, lifecycle | ~50% |
| Permapeople Web (181 стр) | 🔄 работает | good/bad companions, propagation, edible_parts, used_for | ~20% match |
| GardenersWorld (10,000) | 🔄 **multi-URL** | pests, problems, pruning, propagation, soil, watering, fertilizer | ~60% |
| ASPCA (70 стр) | 🔄 **+severity** | toxicity_symptoms, toxicity_severity, toxic_to_pets | Авторитетный |

### Завершены ранее
| Trefle | ✅ done | Каркас 20,197 растений (water, light, temp, humidity, toxic) |
| Wikipedia | ✅ done | Описания 3,779 растений |
| Xiaomi | ✅ done | PPFD, humidity_min для 352 растений |

### Инфраструктура качества (04.04)
- [x] Схема расширена: care 37→68 колонок, plants +3 (origin, order, synonyms)
- [x] verify.py — cross-source верификация (NC State × POWO × Wikipedia × Turso)
- [x] reconcile.py — consensus engine (confirmed/majority/conflict/fuzzy_match)
- [x] source_data + reconciled таблицы
- [ ] Перевести парсеры на store_source_data() → reconcile (после текущего прогона)

---

## ВЫПОЛНЕНО ✅

- About → Details (04-01)
- Smart Identify v2 — 3 ID + 5 enrichment источников (04-02)
- Library → Turso DB вместо хардкода (04-02)
- 12 fetchers написаны: Perenual, Trefle, Wikipedia, Xiaomi, NC State, Missouri BG, POWO, GardenersWorld, Almanac, Permapeople Web, Permapeople API, ASPCA (04-02—03)
- 6 popular plants 17/17 в Turso (04-02)
- NULL bug fix (04-03)
- Settings: 12 Data Sources (04-03)
- Инструкции на сайте исправлены: 12V, Online tab, tube (04-03)
- Бэкап 20,197 растений (04-03)
- JWT secret sync (04-01)
- Light Meter ported from RN (04-01)
- Journal tab + camera button (04-01)
- WateringChart, MonthBar (04-01)
