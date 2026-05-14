import pytesseract
import pdfplumber
from docx import Document
from pdf2image import convert_from_path
import os
from PIL import Image

# Пути к утилитам
pytesseract.pytesseract.tesseract_cmd = r"D:\Programs\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"D:\Programs\poppler\Library\bin"

def extract_text_from_docx(filepath):
    """Извлекает текст из DOCX"""
    try:
        doc = Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text
    except Exception as e:
        print(f"Ошибка чтения DOCX {filepath}: {e}")
        return ""

def extract_text_from_pdf(filepath):
    """Извлекает текст из PDF — сначала пробует текстовый, потом OCR"""
    try:
        # Пробуем текстовый PDF
        with pdfplumber.open(filepath) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        if text.strip():
            print(f"  PDF текстовый — извлечено {len(text)} символов")
            return text
        
        # Если текста нет — это скан, используем OCR
        print(f"  PDF скан — запускаем OCR...")
        images = convert_from_path(filepath, poppler_path=POPPLER_PATH)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img, lang="rus+eng") + "\n"
        print(f"  OCR завершён — извлечено {len(text)} символов")
        return text
        
    except Exception as e:
        print(f"Ошибка чтения PDF {filepath}: {e}")
        return ""

def extract_text_from_attachment(filepath):
    """Универсальный экстрактор текста из вложения"""
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(filepath)
    elif ext in [".txt"]:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        print(f"  Неподдерживаемый формат: {ext}")
        return ""

def test_extraction():
    """Тест извлечения текста"""
    test_dir = r"C:\workmind\storage\test_attachments"
    if not os.path.exists(test_dir):
        print(f"Папка {test_dir} не найдена")
        return
    
    for filename in os.listdir(test_dir):
        filepath = os.path.join(test_dir, filename)
        print(f"\nОбрабатываем: {filename}")
        text = extract_text_from_attachment(filepath)
        if text:
            print(f"Первые 300 символов:\n{text[:300]}")
        else:
            print("Текст не извлечён")

if __name__ == "__main__":
    test_extraction()