from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Паспорт бота.docx"

SECTIONS = [
    ("Паспорт бота", 1),
    ("Название бота", 2),
    ("Бот-консультант по портфолио и услугам.", 0),
    ("Цель и задачи", 2),
    ("Цель: автоматизировать первичное общение с потенциальными клиентами, быстро рассказывать об опыте, проектах и услугах, а также подводить пользователя к заявке или личному контакту.", 0),
    ("Задачи:", 0),
    ("- Отвечать на команду /start и запускать понятный сценарий знакомства.", 0),
    ("- Показывать разделы: опыт, проекты, услуги, контакты/заявка.", 0),
    ("- Снижать количество повторяющихся ручных ответов.", 0),
    ("- Помогать пользователю сформулировать запрос на услугу.", 0),
    ("Целевая аудитория", 2),
    ("Потенциальные клиенты, которым нужно быстро понять опыт исполнителя, посмотреть примеры проектов, узнать перечень услуг и оставить заявку.", 0),
    ("Функции для пользователя бота", 2),
    ("Функция 1 — приветствие и навигация через /start. Потребность: быстро понять, что умеет бот.", 0),
    ("Функция 2 — раздел «Опыт». Потребность: оценить компетенции и подход исполнителя.", 0),
    ("Функция 3 — раздел «Проекты». Потребность: увидеть примеры работ и практическую пользу.", 0),
    ("Функция 4 — раздел «Услуги». Потребность: узнать, с какими задачами можно обратиться.", 0),
    ("Функция 5 — раздел «Контакты / заявка». Потребность: понять, как связаться и какие данные отправить.", 0),
    ("Функции для владельца бота", 2),
    ("Функция 1 — автоматизация первичных ответов. Потребность: экономить время на типовых вопросах.", 0),
    ("Функция 2 — единая структура презентации услуг. Потребность: последовательно показывать клиентам важную информацию.", 0),
    ("Функция 3 — подготовка пользователя к заявке. Потребность: получать более понятные обращения.", 0),
    ("Сценарии использования", 2),
    ("Сценарий 1. Первое знакомство: пользователь отправляет /start, бот приветствует и показывает меню.", 0),
    ("Сценарий 2. Изучение опыта и проектов: пользователь выбирает раздел, бот показывает краткое описание и оставляет меню доступным.", 0),
    ("Сценарий 3. Выбор услуги: пользователь открывает услуги и понимает, подходит ли предложение под его задачу.", 0),
    ("Сценарий 4. Контакт или заявка: бот подсказывает, какие данные отправить для начала обсуждения.", 0),
    ("Инструменты и интеграции", 2),
    ("Telegram Bot API — работа бота в Telegram.", 0),
    ("Python — язык реализации каркаса.", 0),
    ("python-telegram-bot — обработка команд, кнопок и сообщений.", 0),
    ("python-dotenv — загрузка настроек из .env без хардкода секретов.", 0),
    ("BotFather — создание бота и получение токена.", 0),
    ("Ограничения и риски", 2),
    ("Ограничения: каркас не хранит заявки в базе данных, не отправляет уведомления владельцу и не подключен к ИИ. Реальная проверка требует токен BotFather.", 0),
    ("Риски: утечка токена, остановка процесса бота, необходимость заменить обобщенную информацию на реальные данные владельца перед публикацией.", 0),
]


def paragraph(text: str, level: int = 0) -> str:
    style = ""
    if level == 1:
        style = '<w:pPr><w:pStyle w:val="Title"/></w:pPr>'
    elif level == 2:
        style = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
    return f"<w:p>{style}<w:r><w:t>{escape(text)}</w:t></w:r></w:p>"


def main() -> None:
    document = "".join(paragraph(text, level) for text, level in SECTIONS)
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{document}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr></w:body>
</w:document>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
</w:styles>'''

    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles)

    print(f"Создан файл: {OUTPUT.name}")


if __name__ == "__main__":
    main()
