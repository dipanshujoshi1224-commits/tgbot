import pyautogui
import pytesseract
import time

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

while True:
    img = pyautogui.screenshot(region=(150,180,700,420))
    text = pytesseract.image_to_string(img)

    print(text)
    print("-----")

    time.sleep(2)