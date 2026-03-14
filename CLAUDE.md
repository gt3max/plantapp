# CLAUDE.MD — PlantApp Mobile Application

## О проекте
PlantApp — мобильное приложение для ухода за растениями с интеграцией Polivalka (автополив).
**Цель: СОХРАНИТЬ РАСТЕНИЕ** — всё остальное вторично.

**Слоган:** "Why guess when you can measure?"

---

## Репозитории проекта

| Репо | GitHub | Назначение |
|------|--------|------------|
| **plantapp** (этот) | gt3max/plantapp | Мобильное приложение |
| polivalka-web | gt3max/polivalka-web | Cloud сайт (plantapp.pro) |
| Polivalka | gt3max/Polivalka | ESP32 firmware + Lambda + docs |

**ПРАВИЛО СИНХРОНИЗАЦИИ:** Все 3 клиента → один бэкенд (API Gateway → Lambda → DynamoDB).
- Изменил API endpoint → проверить ВСЕ клиенты
- Добавил фичу в приложение → нужен ли аналог на сайте?
- Несинхронизированные клиенты = баг

---

## Стек

```
React Native + Expo (SDK 52+)
├── expo-router         — навигация (file-based)
├── TypeScript          — типизация
├── zustand             — state management (TODO)
├── nativewind          — Tailwind для RN (TODO)
├── expo-notifications  — push-уведомления (TODO)
├── expo-image-picker   — фото растений (TODO)
├── expo-secure-store   — JWT токены (TODO)
└── expo-sqlite         — локальная база (TODO)
```

---

## Бэкенд (общий с polivalka-web)

| Endpoint | Метод | Назначение | Auth |
|----------|-------|------------|------|
| `/auth/register` | POST | Регистрация | Public |
| `/auth/login` | POST | Логин → JWT | Public |
| `/auth/verify` | POST | Подтверждение email | Public |
| `/auth/resend-code` | POST | Переотправка кода | Public |
| `/auth/refresh` | POST | Обновление JWT | Public |
| `/plants/identify` | POST | AI-идентификация (Plant.id) | Public (rate-limited) |
| `/plants/care` | POST | Информация по уходу | Public |
| `/devices/*` | Various | Управление устройствами | JWT |
| `/telemetry/*` | Various | Данные датчиков | JWT |

**API Gateway:** `https://p0833p2v29.execute-api.eu-central-1.amazonaws.com`

---

## Продуктовые принципы

1. **Информация = Действие** — каждый совет → конкретное действие/оборудование
2. **Два уровня** — основной экран + Advanced (как Sensor Mode на ESP32)
3. **Честная монетизация** — free tier работает, подписка прозрачна, Manage Subscription в Settings
4. **Группировка растений** — Sites с общими условиями (свет, температура)
5. **Try before you buy** — дай попробовать, потом предложи Premium

---

## Git Workflow

- **Ветка:** `main` (пока одна, добавим `develop` при публикации в App Store)
- **Формат коммита:** `v0.1.X: [краткое описание]`
- **Правило:** маленькие коммиты, один шаг = один коммит
- **Push:** после каждого рабочего коммита

---

## Конвенции кода

- TypeScript строго (no `any`)
- Компоненты: PascalCase (`PlantCard.tsx`)
- Утилиты/хуки: camelCase (`useAuth.ts`)
- Стили: NativeWind (Tailwind) когда подключим, до этого StyleSheet
- API вызовы: через единый `api.ts` адаптер (аналог `api-adapter.js` с сайта)
- Хранение JWT: `expo-secure-store` (не AsyncStorage!)

---

## Документация

| Документ | Путь (в репо Polivalka) |
|----------|------------------------|
| Development Plan | `documentation/PlantApp_Development/PlantApp_Development.md` |
| Competitor Analysis | `documentation/PlantApp_Development/Planta/` (40 скриншотов) |
| Friend's Plan | `documentation/PlantApp_01.03.2026.pdf` |
| Main Project Specs | `documentation/polivalka_presets_v3.xlsx` (вкладка PlantApp) |

---

## Чек-лист перед ответом

- [ ] Синхронизация: затрагивает ли изменение сайт или ESP32?
- [ ] API: endpoint существует в Lambda?
- [ ] Маленький шаг (Agile)?
- [ ] Не нарушаю цель (сохранить растение)?
- [ ] TypeScript: нет `any`?
- [ ] Git: коммит после каждого рабочего шага?
