# CLAUDE.MD — PlantApp

## О проекте
PlantApp — мобильное приложение для ухода за растениями с интеграцией Polivalka (автополив).
**Цель: СОХРАНИТЬ РАСТЕНИЕ** — всё остальное вторично.
**Слоган:** "Why guess when you can measure?"

**ОСНОВНАЯ ДОКУМЕНТАЦИЯ:** `documentation/PlantApp_Description.md`

---

## ТРИ РЕПОЗИТОРИЯ

| Папка | GitHub | Назначение | Стек |
|-------|--------|------------|------|
| `/Users/maximshurygin/plantapp` | gt3max/plantapp | Мобильное приложение | Flutter (Dart) |
| `/Users/maximshurygin/polivalka-web` | gt3max/polivalka-web | Cloud сайт (plantapp.pro) | HTML/JS |
| `/Users/maximshurygin/Polivalka` | gt3max/Polivalka | ESP32 firmware + Lambda + docs | C, Python |

**ПРАВИЛО СИНХРОНИЗАЦИИ:** Все 3 клиента → один бэкенд (API Gateway → Lambda → DynamoDB).
- Изменил API endpoint → проверить ВСЕ клиенты
- Несинхронизированные клиенты = баг

---

## Продуктовые принципы

1. **Информация = Действие** — каждый совет → конкретное действие
2. **Два уровня** — основной экран + Advanced
3. **Честная монетизация** — free tier работает, подписка прозрачна
4. **Группировка растений** — Sites с общими условиями
5. **Try before you buy** — дай попробовать, потом предложи Premium
6. **Три источника истины** — перекрёстная проверка данных
7. **Независимость** — своя база, без vendor lock-in

---

## Git Workflow

- **Ветки:** `flutter` (приложение), `main` (старый RN, архив)
- **Формат коммита:** `vX.Y.Z: [описание]`
- **Push:** после каждого рабочего коммита
- **Маленькие шаги:** один шаг = один коммит

---

## Конвенции кода

- Dart/Flutter строго (no dynamic где возможно)
- Компоненты: PascalCase (`PlantCard`)
- Сервисы: camelCase (`plantService`)
- API вызовы: через `ApiClient` (lib/services/api_client.dart)
- Хранение JWT: SharedPreferences (dev), SecureStorage (production)

---

## Чек-лист перед ответом

- [ ] Синхронизация: затрагивает ли изменение сайт или ESP32?
- [ ] API: endpoint существует в Lambda?
- [ ] Не нарушаю цель (сохранить растение)?
- [ ] Git: коммит после каждого рабочего шага?
- [ ] Документация: обновить если структура менялась?
