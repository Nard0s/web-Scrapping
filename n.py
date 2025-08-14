from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# === Setup ChromeDriver ===
chrome_options = Options()
chrome_options.add_argument("--headless")  # optional: runs without opening browser
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])  # hide logs

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

# === Open site ===
driver.get("https://www.saucedemo.com/")

# === Login ===
driver.find_element(By.ID, "user-name").send_keys("standard_user")
driver.find_element(By.ID, "password").send_keys("secret_sauce")
driver.find_element(By.ID, "login-button").click()

# === Get product names ===
products = driver.find_elements(By.CLASS_NAME, "inventory_item_name")
for product in products:
    print("🛒", product.text)

# === Close browser ===
driver.quit()
