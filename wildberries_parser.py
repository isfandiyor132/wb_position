# -*- coding: utf-8 -*-
from selenium.webdriver.common.by import By
from selenium import webdriver
import os

def wildberries_parser(key_phrase, find_link):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    browser = webdriver.Chrome(executable_path="chromedriver", chrome_options=chrome_options)

    position = []
    titles = []

    key_phrase = list(map(str, key_phrase.split("|")))[1:-1]
        
    for p in range(len(key_phrase)):
        stop = False
        rng = 0

        for i in range(1 ,11):
            if not stop:
                if i == 1:
                    url = f"https://www.wildberries.ru/catalog/0/search.aspx?sort=popular&search={key_phrase[p].strip()}"
                else:
                    url = f"https://www.wildberries.ru/catalog/0/search.aspx?page={i}&sort=popular&search={key_phrase[p].strip()}"
                browser.get(url)
                browser.implicitly_wait(2)

                blocks = browser.find_elements(By.CLASS_NAME, "j-card-item")
                if len(blocks) > 0:
                    for j in range(len(blocks)):
                        rng += 1
                        link = str(blocks[j].get_attribute("data-popup-nm-id"))
                        if find_link.strip() == link:
                            position.append(rng)
                            titles.append(key_phrase[p].strip())
                            stop = True
                            break
                else:
                    break
            else:
                break

    return titles, position