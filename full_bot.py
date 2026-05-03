import pyautogui
import pytesseract
import time
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

while True:
    img = pyautogui.screenshot(region=(150,180,700,420))
    text = pytesseract.image_to_string(img)

    print("OCR READ:")
    print(text[:500])
    print("----------")

    match = re.search(r'([A-Z])', text)

    if match:
        print("Found letter:", match.group(1))

    time.sleep(2)