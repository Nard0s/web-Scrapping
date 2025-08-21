from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# ==== Chrome setup ====
chrome_options = Options()
chrome_options.add_argument("--headless")  
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])



license_no = input("Enter TIN/license number: ")



driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)
WebDriverWait(driver, 60).until(
    EC.presence_of_element_located((By.TAG_NAME, "body"))
)

time.sleep(60)

input_field = WebDriverWait(driver, 60).until(
    EC.visibility_of_element_located(
        (By.XPATH, "//input[@placeholder='License No or TIN']")
    )
)
input_field.send_keys(license_no)

driver.get("https://etrade.gov.et/business-license-checker") 
driver.find_element(By.ID, "default-search").send_keys(license_no)
submit_button = WebDriverWait(driver, 60).until(
    EC.element_to_be_clickable((By.XPATH, "//button[text()='Search']"))
)
submit_button.click()

try:
    divs = WebDriverWait(driver, 60).until(
        EC.presence_of_all_elements_located((By.XPATH, "//div[p and span]"))
    )

    for div in divs:
        key = div.find_element(By.TAG_NAME, "p").text
        value = div.find_element(By.TAG_NAME, "span").text
        print(key, value)
except:
    print("No results found or timed out waiting for elements.")
driver.quit()
