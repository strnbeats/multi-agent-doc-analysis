
# Live-результаты summarizer (GigaChat) — фикстуры 01–10

**Режим:** live (`APP_MODE=real`), модель `GigaChat-3-Ultra`, дата 2026-11-06.  
**Шаг:** только `summary` (остальные агенты не оцениваются).  
**Фикстуры:** [`docs/datasets/01–10`](./datasets/).  
**Разметка must-include / must-not:** [`summarizer-annotations.md`](./summarizer-annotations.md).  
**Сырые JSON:** `internal/live-pipeline-run/*.json` (поле `summary`).

Шкала: **pass** / **partial** / **fail**.

## Сводка

| # | Фикстура | Summary | Кратко |
|---|----------|---------|--------|
| 01 | consistent-science | **pass** | Ключевой результат, без новых чисел |
| 02 | contradiction-numbers | **pass** | Три числовых расхождения |
| 03 | contradiction-dates | **pass** | Противоречивые даты, без канон-даты |
| 04 | contradiction-names | **pass** | Конференция + системные сбои имён |
| 05 | claim-vs-denial | **pass** | Маркетинг ↔ импорт/контракт |
| 06 | borderline-ambiguous | **pass** | Нюанс рекорда/роста, без hard-fail |
| 07 | clean-news-summary | **pass** | Короткий дайджест (~3 предл.) |
| 08 | rich-facts-analyzer | **pass** | Сезон + PM2.5, без дампа всех чисел |
| 09 | consistent-policy | **pass** | Программа → бюджет/охват → сроки |
| 10 | bilingual-borderline | **pass** | Расхождения RU↔EN по дате/offline/языкам |

**Итог summarizer:** **10/10 pass** (0 partial, 0 fail).

## По фикстурам

### 01 — `01-consistent-science.txt` → **pass**
- **Output:** HSP70, 42 °C, ×4,2, VER-155008, 78%→31%, «Биохимия», 2024–2025; ~3 предложения.
- **vs must-include / must-not:** ключевой результат на месте; новых чисел нет.

### 02 — `02-contradiction-numbers.txt` → **pass**
- **Output:** фиксирует 120↔70, 2,5↔2,2 млрд, 18%↔10%.
- **vs must-include / must-not:** все три расхождения; без «починки» цифр.

### 03 — `03-contradiction-dates.txt` → **pass**
- **Output:** несовпадающие даты выставки/открытия/закрытия; льгота по воскресеньям.
- **vs must-include / must-not:** противоречия дат отмечены; канонической даты нет.

### 04 — `04-contradiction-names.txt` → **pass**
- **Output:** конференция + системные несоответствия имён/должностей/рода.
- **vs must-include / must-not:** персоналии как конфликт; без «исправления» имён.

### 05 — `05-claim-vs-denial.txt` → **pass**
- **Output:** локализация/«нулевой импорт» ↔ Корея/контракт до 2026; слова ГД ↔ примечание.
- **vs must-include / must-not:** claim↔denial сохранены; планы 2027 не выданы за факт.

### 06 — `06-borderline-ambiguous.txt` → **pass**
- **Output:** 980k / ~1 млн vs 1,05 млн; «рекорд» как пик; терминал условен.
- **vs must-include / must-not:** неоднозначность удержана; нет hard-contradiction и нет голого clean.

### 07 — `07-clean-news-summary.txt` → **pass**
- **Output:** Казань, 2 года, 12 га, 1,1 млрд / 60%, 3 км, 200 саженцев, причал.
- **vs must-include / must-not:** короткий clean-дайджест; лишних конфликтов нет.

### 08 — `08-rich-facts-analyzer.txt` → **pass**
- **Output:** зима НСК 2024/25, PM2.5 75 vs норма 15, Белова/Сурков; без полного дампа температур.
- **vs must-include / must-not:** сжатие богатого фактажа; выдуманных станций нет.

### 09 — `09-consistent-policy.txt` → **pass**
- **Output:** 300 библиотек, 85 млн, 40 школ, сроки; приоритет фонду >5 лет.
- **vs must-include / must-not:** согласованная программа отражена; ложного alarm по сумме 85 нет. (Мета-замечание про критерии отбора 40 школ — вне конфликта исходника, на score шага не влияет.)

### 10 — `10-bilingual-borderline.txt` → **pass**
- **Output:** RU 1 окт / offline+3 яз. vs EN GA 15 окт / offline later / 2 яз.
- **vs must-include / must-not:** RU↔EN расхождения названы. Лёгкий уклон к EN/FAQ как «более точным» — допустимо для summary, без канонизации одной версии.


