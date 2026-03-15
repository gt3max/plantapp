# PlantApp — Конкурентный анализ: Planta

> Дата: 15.03.2026
> Статус: живой документ, обновляется по мере анализа

---

## 1. Planta — профиль компании

| Метрика | Значение |
|---------|----------|
| Основана | 2017, Vaxholm, Швеция |
| Основатели | Tove Westlund, Martin Wählby |
| Пользователей | ~10M (2025) |
| Растений в приложении | 40M |
| Выручка | ~$200-300K/мес (~$3.6M/год) |
| Команда | 15 человек, полностью удалённая |
| Финансирование | $0. Bootstrapped. Без инвесторов |
| Цена подписки | $7.99/мес или $35.99/год |
| Языков | 10 |
| Стран | 55 |
| Рост | 1M (2020) → 3.3M (2021) → 6M (2022) → 10M (2025) |
| App Store рейтинг | 4.8 |
| #3 Top Grossing | House & Home (2025) |

**Вывод:** $3.6M/год, 15 человек, 0 инвесторов — очень прибыльный bootstrapped бизнес. Рынок доказан.

---

## 2. Демография пользователей

### Кто использует plant care apps

| Параметр | Данные |
|----------|--------|
| Возраст | Gen Z (18-24) + Millennials (25-40) |
| Пол | ~70% женщины |
| Растений дома | Gen Z: в среднем 10 на квартиру |
| Самоидентификация | 7 из 10 миллениалов — "plant parent" |
| Характеристика | Чаще LGBTQ, чаще бездетные |
| Средние траты на растения | $120/год |
| Рынок indoor plants | $20.68B (2024) → $30.25B (2032) |

**"Plant parent"** — не хобби, а эмоциональная связь. Растение = забота о живом существе. Тревога за растение = тревога за ребёнка.

### Топ-рынки Planta

| Рынок | Почему |
|-------|--------|
| **США** | Основной. Крупнейший рынок houseplants |
| **UK** | Второй. App of the Day в UK App Store |
| **Австралия, Новая Зеландия** | App of the Day. Тёплый климат |
| **Скандинавия** | Домашний рынок, но маленький |
| **Германия, Нидерланды** | Сильная культура комнатных растений |
| **Азия** (Индия, Сингапур, Япония) | Экспансия 2020-2021, малая доля |

### Три сегмента пользователей

**A. "Тревожный новичок" (~70%)**
- Купил монстеру в IKEA, не знает что делать
- Гуглит "how often to water monstera" → 50 противоречивых ответов
- Скачивает Planta чтобы кто-то сказал "полей в среду"
- Ключевая потребность: снять тревогу, простая инструкция
- Платит? Нет. Retention ~15%

**B. "Коллекционер" (~25%)**
- 10-30 растений дома, знает основы
- Нужен учёт: что где стоит, когда поливал
- Identify — чтобы узнать точное название
- Ключевая потребность: каталог + трекинг
- Платит? Часть — да, за Identify + расширенный уход

**C. "Энтузиаст" (~5%)**
- Знает разницу между Philodendron gloriosum и melanochrysum
- Интересуется PPFD, субстратами, размножением
- Planta слишком примитивна
- Ключевая потребность: точные данные
- Платит? Да, но разочаровывается быстро

**Главный инсайт:** Planta зарабатывает на сегменте B (коллекционеры) через paywall на Identify. 70% пользователей не платят. Энтузиасты — самые лояльные, но Planta их не удовлетворяет.

---

## 3. Реальные отзывы пользователей

### Довольные (4-5 звёзд)

> **JigokuShoujoXIV** ★★★★★: "I have around 40 houseplants and this has been a god send... blows them all out the water."

> **Boomsgirl** ★★★★★: "I absolutely LOVE it! My plants have been thriving ever since!"

> **Emma Damato** ★★★★: "I'm super grateful for Planta because I could never keep up with my 47 plants."

> **Heartisanite** ★★★★: "Keeps me on track when overwhelmed."

> **Thehowlingwool** ★★★★: "Happy to pay for the premium version."

**Паттерн довольных:** коллекционеры с 30-50 растениями. Нужна напоминалка. Не AI, не диагностика — "скажи мне когда полить".

### Недовольные (1-3 звезды)

> **EmilyClair2255** ★★★: "Planta told me to water a dracaena once a month... lol."

> **Xenajade** ★★: "Half of my plants are dying... I've been using Planta for about a month now."

> **Royal Wee** ★★★: "Planta used to work wonderfully... suddenly I have a very laggy, buggy app."

> **Aracely** ★★★: "You can't personalize dates — one thing that doesn't make sense."

> **Adayday** ★★★: "I almost don't want to recommend any new plant owners use Planta."

> **Amelia** ★★: "I was misled to think my subscription would be $3 a month... whole amount debited immediately."

### Систематические проблемы из обзоров

| Проблема | Суть |
|----------|------|
| **Перелив** | Приложение говорит "поливай" — пользователь слепо поливает, не проверяя почву → корни гниют |
| **Нельзя менять расписание** | Жёсткие даты, нет персонализации под климат. Калифорния 90°F = не то же что Швеция |
| **Identify неточный** | "Plant ID will get it wrong 9 times out of 10" + paywall |
| **Удобрения generic** | "All purpose fertilizer" для всех → сжигает корни |
| **Paywall на базовое** | Identify, light meter, диагностика — за $36/год |
| **Баги, лаги** | "Laggy, buggy app", задачи не записываются |
| **Списание после отмены** | Charge after cancel |

**Фундаментальная проблема Planta:** приложение НЕ МОЖЕТ знать реальную влажность почвы. Все рекомендации — это guess на основе "погода + тип + окно". Пользователи слепо доверяют → растения гибнут.

---

## 4. Что продаёт Planta (и что из этого реально)

### Plant Identify — база
- Основная фича, закрыта paywall после 1-3 бесплатных попыток
- Один источник (модель — неизвестно какая)
- Точность спорная: "9 из 10 неверно" (отзывы)
- **Наш ответ:** бесплатно, неограниченно, 2 источника (PlantNet + SerpAPI), кросс-проверка

### Dr. Planta AI — GPT обёртка
- Обёртка над GPT-4 Vision с промптом "ты ботаник"
- Себестоимость: ~$0.01-0.03/запрос
- 200K запросов/мес = $2-6K/мес (1-3% выручки)
- Продаётся как уникальная разработка, а это commodity
- **Наш ответ:** то же самое + реальные данные сенсора (если есть устройство)

### Персонализация (локация, свет, сезон)
- Ручной ввод: location → indoor/outdoor, light → 4 кнопки
- Пользователь НЕ ЗНАЕТ какой у него свет. "Bright indirect" = что?
- Пользователь НЕ БУДЕТ обновлять при перестановке
- Результат: "Water every 7 days" — guess, не персонализация
- **Наш ответ:** PPFD через камеру (измерение > угадывание), геолокация → автоматическая сезонность

### "Спокойствие в отпуске" — блеф
- "Plant sitter" — делись растениями с другом (он получает уведомления)
- Vacation mode — реже шлёт напоминания
- Push: "Your Monstera needs water" — а ты на Бали
- **Notification на телефоне НЕ поливает растение**
- **Наш ответ (с устройством):** Polivalka поливает автоматически, push: "Polivalka полила Monstera 12ml, moisture 65%"
- **Без устройства:** тот же блеф что у Planta. Честно признаём

### Комьюнити
- Форум, фото, обсуждения — социальный замок
- Люди остаются не из-за напоминалки, а потому что "свой клуб"
- Retention-машина
- **У нас этого нет и в MVP не будет — честный gap**

---

## 5. Сравнительная таблица (честная)

| Фича | Planta | PlantApp (без устройства) | PlantApp (с устройством) |
|------|--------|---------------------------|--------------------------|
| Identify | Платно, 1 источник | **Бесплатно, 2 источника** | **Бесплатно, 2 источника** |
| База видов | ~25K | Цель 100K+ (Turso) | Цель 100K+ |
| Свет | 4 кнопки (guess) | **PPFD камера (измерение)** | **PPFD камера + сенсор** |
| Полив | Расписание (guess) | Расписание (guess) | **Сенсор (реальные данные)** |
| AI-диагностика | "Dr. Planta" (GPT) | То же (GPT/Claude) | **GPT/Claude + данные сенсора** |
| Автополив | Нет | Нет | **Polivalka** |
| Отпуск | Блеф (notification) | Блеф (notification) | **Реальный автополив** |
| Комьюнити | **Есть, сильное** | Нет (gap) | Нет (gap) |
| Геймификация | Нет | **Челленджи, grow guides** | **Челленджи + данные сенсора** |
| Вирусность | Органическая (комьюнити) | **Kits + челленджи + share** | **Kits + результаты** |
| Офлайн | Не работает | **Premium: полная база** | **Premium: полная база** |
| Цена | $36/год (paywall) | **Бесплатно, Premium extras** | **Бесплатно, Premium extras** |
| Баги | Лаги, жёсткие даты | Свежий стек (Expo SDK 54) | Свежий стек |

### Где мы сильнее (без устройства)
1. Identify — бесплатно + точнее (2 источника)
2. PPFD через камеру — измерение vs 4 кнопки
3. Цена — бесплатно vs $36/год paywall
4. Офлайн база — Premium, уникальная фича
5. Геймификация — челленджи, grow guides (потенциально)

### Где мы слабее (без устройства)
1. Комьюнити — нет, у Planta есть
2. База видов — у них 25K готовых, у нас 0 пока
3. Полив без устройства — тот же guess что у Planta
4. 10M пользователей vs 0 — brand awareness

### Где мы в другой лиге (с устройством)
- Реальные данные влажности/температуры
- Автоматический полив
- Спокойствие в отпуске — реальное, не блеф
- AI-диагностика с данными сенсора

---

## 6. Стратегические выводы

### Вход на рынок (без устройства)
- **Identify бесплатно** — убираем главный paywall Planta
- **PPFD камерой** — реальное измерение > 4 кнопки
- **Челленджи** — вирусная механика, которой нет у Planta
- **Офлайн база** — Premium, уникально
- Полив = тот же guess, честно признаём

### Удержание (с устройством)
- Пользователь попробовал бесплатное → купил Polivalka → получил реальные данные
- Переход от guess к measurement — quality jump
- Тут Planta не конкурент вообще

### Обход комьюнити
- Не копируем форум (долго, дорого, поздно)
- Вместо "обсуждай" → "делай": челленджи, grow guides, share результатов
- Грибной kit, "вырасти базилик за 30 дней", сезонные цветы
- Действие вместо обсуждения

### Целевая аудитория — та же
- English-first (USA, UK, Australia)
- Молодые (18-40), городские, "plant parents"
- Тревожные новички (70%) — бесплатный Identify + PPFD
- Коллекционеры (25%) — каталог + устройство
- Энтузиасты (5%) — PPFD, данные, precision farming

---

## Источники

- [FloralDaily — Planta digital advice](https://www.floraldaily.com/article/9401586/planta-offers-new-and-experienced-plant-parents-digital-advice/)
- [PRWeb — Planta reaches 6M users](https://www.prweb.com/releases/planta-the-plant-app-reaches-6-million-users-and-launches-new-discover-feature-862944738.html)
- [Social.plus — How Planta grew community](https://www.social.plus/customer-story/planta)
- [Garden Pals — Houseplant Statistics 2024](https://gardenpals.com/houseplant-statistics/)
- [CivicScience — Gen Z Houseplant Ownership](https://civicscience.com/gen-z-houseplant-ownership-stems-from-the-desire-to-care-for-something-alive/)
- [Terrarium Tribe — Houseplant Statistics 2026](https://terrariumtribe.com/houseplant-statistics/)
- [GardenCenterMag — Swedish plant care app](https://www.gardencentermag.com/news/how-this-swedish-plant-care-app-planta-can-help-plant-parents-at-any-stage/)
- [JustUseApp — Planta Reviews](https://justuseapp.com/en/app/1410126781/planta-keep-your-plants-alive/reviews)
- [App Store — Planta Reviews](https://apps.apple.com/us/app/id1410126781?see-all=reviews)
- [EcoCation — Top 5 Free Plant Care Apps](https://ecocation.org/best-free-plant-care-apps/)
