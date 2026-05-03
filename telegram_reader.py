from selenium import webdriver
from selenium.webdriver.common.by import By
import pyautogui
import pygetwindow as gw
import time
import re

# =========================
# OPEN TELEGRAM WEB
# =========================
driver = webdriver.Chrome()
driver.get("https://web.telegram.org/")

print("Login to Telegram Web and open your group chat...")
time.sleep(25)   # time for login

# =========================
# WORD COPIER BUTTON COORDS
# =========================
buttons = {
    'a': (282,224), 'b': (372,224), 'c': (462,224), 'd': (550,224),
    'e': (640,224), 'f': (728,224), 'g': (818,224), 'h': (904,224),
    'i': (995,224), 'j': (1084,224),

    'k': (282,298), 'l': (372,298), 'm': (462,298), 'n': (550,298),
    'o': (640,298), 'p': (728,298), 'q': (818,298), 'r': (904,298),
    's': (995,298), 't': (1084,298),

    'u': (282,372), 'v': (372,372), 'w': (462,372),
    'x': (550,372), 'y': (640,372), 'z': (728,372)
}

BOT_USERNAME = "@on9wordchainbot"
last_done = ""

# =========================
# MAIN LOOP
# =========================
while True:
    try:
        msgs = driver.find_elements(By.XPATH, "//div[contains(@class,'message')]")

        if msgs:
            last = msgs[-1]
            text = last.get_attribute("innerText").strip()

            print("Latest:", text)

            # only react to bot message
            if BOT_USERNAME in text.lower():

                # detect requested letter
                match = re.search(r'with\s+([A-Z])', text, re.I)

                if match:
                    letter = match.group(1).lower()

                    # stop duplicate replies
                    if text != last_done:

                        print("Need letter:", letter)

                        # =========================
                        # SWITCH TO WORD COPIER WINDOW
                        # =========================
                        chrome_windows = gw.getWindowsWithTitle("Chrome")

                        if len(chrome_windows) >= 2:
                            chrome_windows[0].activate()
                            time.sleep(1)

                        # click letter button
                        if letter in buttons:
                            x, y = buttons[letter]
                            pyautogui.click(x, y)

                            time.sleep(0.5)

                            # =========================
                            # BACK TO TELEGRAM
                            # =========================
                            driver.switch_to.window(driver.current_window_handle)
                            time.sleep(1)

                            # paste + send
                            pyautogui.hotkey("ctrl", "v")
                            pyautogui.press("enter")

                            print("Sent word for:", letter)

                            last_done = text

    except Exception as e:
        print("Error:", e)

    time.sleep(2)