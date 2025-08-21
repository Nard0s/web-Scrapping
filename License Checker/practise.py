from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==== Chrome setup ====
chrome_options = Options()
# chrome_options.add_argument("--headless")  
# chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])


license_no = input("Enter TIN/license number: ")
# print("started")

# driver = webdriver.Chrome()
# driver.get("https://www.google.com")

# print("Browser title:", driver.title)
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

driver.get("file:///C:/Users/previ/Desktop/RedCloud%20Data/practice.html") 
driver.find_element(By.ID, "default-search").send_keys(license_no)
driver.find_element(By.ID, "submit").click()
try:
    name = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//div[@id='name']/h1"))
    ).text
    name_v = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//div[@id='name']/p"))
    ).text
    age = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//div[@id='age']/h1"))
    ).text
    age_v = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//div[@id='age']/p"))
    ).text
    print(name, name_v  )
    print(age, age_v )
except Exception as e:
    print("Timed out waiting for message to appear.")
driver.quit()
