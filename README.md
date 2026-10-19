# Citora AI Analytic

Платформа для загрузки Excel-данных в Snowflake, их преобразования с помощью
dbt и последующего анализа через AI-агента.

## Архитектура

```text
GitHub repository
├── Python-код загрузки
├── YAML-контракты Excel
├── SQL-инфраструктура
├── dbt-проект
├── YAML-каталог метрик
└── конфигурация AI-агента
          │
          │ Snowflake Git integration
          ▼
Snowflake Git repository clone
          │
          ├── Python IMPORTS для stored procedure
          ├── YAML-контракт структуры Excel
          ├── SQL через EXECUTE IMMEDIATE FROM
          └── dbt project

Excel-файл
    │
    ▼
Snowflake internal stage
    │
    ▼
Python stored procedure
    │ проверка по YAML-контракту
    ▼
Snowflake RAW
    │
    ▼
dbt-трансформации
    │
    ▼
Snowflake ANALYTICS
    │
    ▼
YAML-каталог метрик
    │
    ▼
AI-агент для аналитики
```

## Источники и ответственность

### GitHub

GitHub является единственным источником версий для:

- Python-кода;
- YAML-контрактов входных файлов;
- Snowflake SQL;
- dbt-моделей и тестов;
- каталога метрик;
- конфигурации аналитического агента.

### Snowflake

В Snowflake находятся:

- Git repository clone, синхронизированный с GitHub;
- internal stage для входных Excel-файлов;
- Python stored procedure для загрузки;
- RAW- и ANALYTICS-таблицы;
- dbt project и вычислительные ресурсы;
- задачи запуска и история выполнения.

Excel-файлы не хранятся в GitHub, поскольку это входные данные, а не код или
конфигурация.

## Обновление версии в Snowflake

После merge в выбранную ветку Snowflake получает изменения командой:

```sql
ALTER GIT REPOSITORY CITORA.PLATFORM.CITORA_REPO FETCH;
```

SQL-файлы из репозитория можно выполнять непосредственно в Snowflake:

```sql
EXECUTE IMMEDIATE FROM
  @CITORA.PLATFORM.CITORA_REPO/branches/main/snowflake/01_infrastructure.sql;
```

Python stored procedure импортирует обработчики из Git repository clone, без
локальной сборки ZIP и без отдельного stage для Python-кода.

## Основные принципы

- Структура каждого Excel-файла описывается в версионируемом YAML-контракте.
- Перед загрузкой Excel проверяется на соответствие контракту.
- Исходные данные загружаются в RAW без бизнес-преобразований.
- Очистка и бизнес-правила реализуются в dbt.
- Доступные агенту метрики и измерения явно описываются в YAML.
- Агент имеет доступ только на чтение к подготовленным аналитическим данным.
- Изменения попадают в Snowflake только после merge и синхронизации Git clone.

## Этапы разработки

1. Настроить GitHub-репозиторий и Snowflake Git integration.
2. Создать Snowflake Git repository clone.
3. Создать internal stage для Excel и схемы RAW/ANALYTICS.
4. Зарегистрировать Python stored procedure из файлов Git repository clone.
5. Загрузить Excel и проверить RAW-таблицу.
6. Перенести существующую Python-трансформацию в dbt.
7. Добавить dbt-тесты качества данных.
8. Создать YAML-каталог метрик.
9. Настроить аналитического AI-агента.
10. Настроить регулярный запуск и мониторинг.

## Статус

Проект создаётся поэтапно. Каждый компонент согласовывается перед реализацией.
