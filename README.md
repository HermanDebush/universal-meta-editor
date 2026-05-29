# Universal Meta Editor

> Edit the metadata of Office documents, Windows executables, HTML pages and shortcuts — without Microsoft Office, without going online.
>
> Редактор метаданных документов Office, программ Windows, HTML-страниц и ярлыков — без Microsoft Office и без подключения к интернету.

![SNN PROJECT](https://img.shields.io/badge/SNN-PROJECT-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![Offline](https://img.shields.io/badge/Offline-100%25-brightgreen)
![UI](https://img.shields.io/badge/UI-RU%20%7C%20EN-orange)

**Язык документа:** [🇷🇺 Русский](#-русский) · [🇬🇧 English](#-english)

---

## 🇷🇺 Русский

**Universal Meta Editor** — настольное приложение для просмотра и изменения метаданных файлов разных типов. Работает полностью оффлайн, не загружает файлы в сеть и никогда не меняет оригинал — изменения всегда сохраняются в новую копию.

Интерфейс доступен на **двух языках (Русский / English)** — переключатель в правом верхнем углу. Выбор запоминается между запусками.

Проект разработан **СНН PROJECT** (Союз Независимых Наработок).

### ✨ Основные возможности

| Возможность | Описание |
|---|---|
| 📄 Метаданные Office | Автор, заголовок, тема, ключевые слова, даты создания/изменения, число ревизий и др. |
| 🖥 Версия и описание программ | Поля VERSIONINFO в `.exe` / `.dll` (FileDescription, FileVersion, CompanyName…) |
| 🌐 Метаданные HTML | `<title>`, description, keywords, author, viewport + теги Open Graph |
| 🔗 Параметры ярлыков | Объект, аргументы, рабочая папка, комментарий, значок, стиль окна |
| 🗂 Временные метки файла | Даты создания / изменения / доступа, видимые в проводнике Windows |
| 🌍 Два языка интерфейса | Русский и English с мгновенным переключением и сохранением выбора |

### ⚙️ Дополнительные функции

- **Перетаскивание (drag & drop)** — бросьте файл прямо в окно
- **Календарь с выбором даты и времени** — визуальный выбор с прокруткой колесом мыши
- **Подсказка времени** — минуты автоматически переводятся в формат `= 14ч 3м`
- **Безопасная запись** — оригинал никогда не изменяется, результат пишется в новый файл
- **Красивые модальные окна** ошибок и предупреждений + всплывающие уведомления
- **Полностью оффлайн** — никаких загрузок, облаков и телеметрии

### 🖥 Функции для EXE / DLL *(только Windows)*

- Редактирование ресурса **VERSIONINFO**: описание, версия файла и продукта, компания, авторские права, имя файла, внутреннее имя, комментарии
- Редактирование **манифеста приложения (XML)** прямо в программе:
  - `requestedExecutionLevel` — `asInvoker` / `highestAvailable` / `requireAdministrator`
  - `dpiAware` / `dpiAwareness` — управление масштабированием на HiDPI-экранах
- Запись ресурсов выполняется через Windows API (`BeginUpdateResource`), в **копию** файла

### 🌐 Функции для HTML

- Чтение и запись `<title>`, `description`, `keywords`, `author`, `viewport`
- Теги **Open Graph**: `og:title`, `og:description`, `og:type`
- Автоопределение кодировки страницы (`charset`, только для чтения)

### 🔗 Функции для ярлыков (.lnk)

- Редактирование поля **«Объект»**, которое Windows 11 часто **запрещает менять** в свойствах ярлыка
- Аргументы командной строки, рабочая папка, комментарий-подсказка, значок (путь,индекс)
- Стиль окна: **Обычное / Развёрнутое / Свёрнутое**
- Встроенный **бинарный разбор формата** `[MS-SHLLINK]` — корректно читает кириллицу как в Unicode-ярлыках (UTF-16 LE), так и в старых ANSI-ярлыках (cp1251), без искажений кодировки

### 📦 Поддерживаемые форматы

| Тип | Расширения |
|---|---|
| Word | `.docx` `.docm` |
| Excel | `.xlsx` `.xlsm` |
| PowerPoint | `.pptx` `.pptm` |
| Visio | `.vsdx` |
| Программы Windows | `.exe` `.dll` `.sys` `.scr` |
| Веб-страницы | `.html` `.htm` |
| Ярлыки | `.lnk` |

### 🚀 Установка и запуск

```bash
git clone https://github.com/HermanDebush/universal-meta-editor.git
cd universal-meta-editor
pip install -r requirements.txt
python main.py
```

Запуск без окна консоли (Windows): двойной клик по **`run.bat`**.
Открыть файл сразу: `python main.py путь/к/файлу.docx`.

**Требования:** Python 3.10+, `customtkinter`. Microsoft Office не нужен.

### 🔨 Сборка .exe и установщика

```bash
pyinstaller UniversalMeta.spec          # → dist/UniversalMetaEditor.exe
# затем (Inno Setup):  installer/setup.iss → dist/installer/UniversalMetaEditor_Setup.exe
```

---

## 🇬🇧 English

**Universal Meta Editor** is a desktop app for viewing and editing the metadata of many file types. It works fully offline, never uploads your files, and never modifies the original — every change is written to a new copy.

The interface is available in **two languages (Russian / English)** — switch it from the top-right corner. Your choice is remembered between launches.

Developed by **СНН PROJECT** (Union of Independent Works).

### ✨ Core features

| Feature | Description |
|---|---|
| 📄 Office metadata | Author, title, subject, keywords, created/modified dates, revision count, and more |
| 🖥 Program version & description | VERSIONINFO fields in `.exe` / `.dll` (FileDescription, FileVersion, CompanyName…) |
| 🌐 HTML metadata | `<title>`, description, keywords, author, viewport + Open Graph tags |
| 🔗 Shortcut properties | Target, arguments, working directory, comment, icon, window style |
| 🗂 File timestamps | Created / modified / accessed dates shown in Windows Explorer |
| 🌍 Two UI languages | Russian and English with instant switching and a saved preference |

### ⚙️ Additional functions

- **Drag & drop** — drop a file straight onto the window
- **Date + time picker** — visual calendar with mouse-wheel navigation
- **Time hint** — minutes are auto-formatted as `= 14h 3m`
- **Safe write** — the original is never touched; output goes to a new file
- **Polished modal dialogs** for errors/warnings + slide-in toast notifications
- **Fully offline** — no uploads, no cloud, no telemetry

### 🖥 EXE / DLL functions *(Windows only)*

- Edit the **VERSIONINFO** resource: description, file & product version, company, copyright, original filename, internal name, comments
- Edit the **application manifest (XML)** in-app:
  - `requestedExecutionLevel` — `asInvoker` / `highestAvailable` / `requireAdministrator`
  - `dpiAware` / `dpiAwareness` — HiDPI scaling control
- Resources are patched via the Windows API (`BeginUpdateResource`) into a **copy** of the file

### 🌐 HTML functions

- Read and write `<title>`, `description`, `keywords`, `author`, `viewport`
- **Open Graph** tags: `og:title`, `og:description`, `og:type`
- Automatic page charset detection (`charset`, read-only)

### 🔗 Shortcut (.lnk) functions

- Edit the **“Target”** field that Windows 11 often **blocks** in the shortcut properties dialog
- Command-line arguments, working directory, tooltip comment, icon (path,index)
- Window style: **Normal / Maximized / Minimized**
- Built-in **binary `[MS-SHLLINK]` parser** — correctly reads Cyrillic from both Unicode shortcuts (UTF-16 LE) and legacy ANSI shortcuts (cp1251), with no mojibake

### 📦 Supported formats

| Type | Extensions |
|---|---|
| Word | `.docx` `.docm` |
| Excel | `.xlsx` `.xlsm` |
| PowerPoint | `.pptx` `.pptm` |
| Visio | `.vsdx` |
| Windows programs | `.exe` `.dll` `.sys` `.scr` |
| Web pages | `.html` `.htm` |
| Shortcuts | `.lnk` |

### 🚀 Install & run

```bash
git clone https://github.com/HermanDebush/universal-meta-editor.git
cd universal-meta-editor
pip install -r requirements.txt
python main.py
```

Run without a console window (Windows): double-click **`run.bat`**.
Open a file directly: `python main.py path/to/file.docx`.

**Requirements:** Python 3.10+, `customtkinter`. No Microsoft Office needed.

### 🔨 Build .exe and installer

```bash
pyinstaller UniversalMeta.spec          # → dist/UniversalMetaEditor.exe
# then (Inno Setup):  installer/setup.iss → dist/installer/UniversalMetaEditor_Setup.exe
```

---

## 🗂 Project structure

```
universal-meta-editor/
│
├── main.py                  # Entry point
├── run.bat                  # Launch without a console window (Windows)
├── UniversalMeta.spec       # PyInstaller build recipe
├── requirements.txt
├── LICENSE
│
├── assets/
│   ├── icon.png             # Source icon
│   └── icon.ico             # Multi-size Windows icon (taskbar / title bar / installer)
│
├── installer/
│   └── setup.iss            # Inno Setup script
│
├── core/
│   ├── i18n.py              # RU/EN translations, language detection & config.json
│   ├── models.py            # CoreMeta, AppMeta, FormatInfo dataclasses
│   ├── formats.py           # Format detection by extension
│   ├── reader.py            # Read Office metadata from ZIP
│   ├── writer.py            # Patch XML and repack ZIP
│   ├── pe_meta.py           # PE VERSIONINFO + manifest read/write
│   ├── html_meta.py         # HTML <meta> / Open Graph read/write
│   ├── lnk_meta.py          # .lnk binary reader + WScript.Shell writer
│   └── file_times.py        # Read/write filesystem timestamps
│
└── gui/
    ├── app.py               # Main window, language switcher, save logic
    ├── widgets.py           # FieldRow, DateField, SectionLabel
    ├── calendar_picker.py   # Dark date + time picker
    ├── error_dialog.py      # Modal error / warning / info dialog
    └── toast.py             # Slide-in toast notifications
```

## 🛡 Лицензия / License

**MIT License** — [полный текст / full text](LICENSE)

Copyright (c) 2026 СНН PROJECT

Данная лицензия разрешает лицам, получившим копию данного программного обеспечения и сопутствующей документации (в дальнейшем именуемыми «Программное Обеспечение»), безвозмездно использовать Программное Обеспечение без ограничений, включая неограниченное право на использование, копирование, изменение, слияние, публикацию, распространение, сублицензирование и/или продажу копий Программного Обеспечения, а также лицам, которым предоставляется данное Программное Обеспечение, при соблюдении следующих условий:

Указанное выше уведомление об авторском праве и данные условия должны быть включены во все копии или значимые части данного Программного Обеспечения.

ПРОГРАММНОЕ ОБЕСПЕЧЕНИЕ ПРЕДОСТАВЛЯЕТСЯ «КАК ЕСТЬ», БЕЗ КАКИХ-ЛИБО ГАРАНТИЙ, ЯВНО ВЫРАЖЕННЫХ ИЛИ ПОДРАЗУМЕВАЕМЫХ, ВКЛЮЧАЯ ГАРАНТИИ ТОВАРНОЙ ПРИГОДНОСТИ, СООТВЕТСТВИЯ ПО ЕГО КОНКРЕТНОМУ НАЗНАЧЕНИЮ И ОТСУТСТВИЯ НАРУШЕНИЙ, НО НЕ ОГРАНИЧИВАЯСЬ ИМИ. НИ В КАКОМ СЛУЧАЕ АВТОРЫ ИЛИ ПРАВООБЛАДАТЕЛИ НЕ НЕСУТ ОТВЕТСТВЕННОСТИ ПО КАКИМ-ЛИБО ИСКАМ, ЗА УЩЕРБ ИЛИ ПО ИНЫМ ТРЕБОВАНИЯМ, В ТОМ ЧИСЛЕ, ПРИ ДЕЙСТВИИ КОНТРАКТА, ДЕЛИКТЕ ИЛИ ИНОЙ СИТУАЦИИ, ВОЗНИКШИМ ИЗ ИЛИ В СВЯЗИ С ПРОГРАММНЫМ ОБЕСПЕЧЕНИЕМ ИЛИ ИСПОЛЬЗОВАНИЕМ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ ИЛИ ИНЫМИ ДЕЙСТВИЯМИ С ПРОГРАММНЫМ ОБЕСПЕЧЕНИЕМ.

---
*Developed by Herman | СНН PROJECT*
*https://projectsnn.com/hub*
