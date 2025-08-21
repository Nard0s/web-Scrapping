import csv
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Configuration
with open('tin.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    tin = [row[0] for row in reader]

LICENSE_NUMBERS = tin[:10]
OUTPUT_CSV = r"C:\Users\previ\Desktop\RedCloud Data\business_data_1.csv"
def save_to_csv(data, filename):
    if not data:
        return
    fieldnames = set()
    for record in data:
        fieldnames.update(record.keys())
    fieldnames = sorted(fieldnames)

    try:
        with open(filename, mode='a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerows(data)
    except Exception as e:
        logging.info(f"❌ Failed to save CSV: {e}")


BASE_URL = "https://etrade.gov.et/business-license-checker"

def setup_driver():
    options = Options()
    
    # Chrome options for headless operation
    options.add_argument('--headless=new')  # modern headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--blink-settings=imagesEnabled=false')  # disable images

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("✅ ChromeDriver setup successful")
        return driver
    except Exception as e:
        logging.info(f"❌ ChromeDriver setup failed: {e}")
        raise

def change_language_to_english(driver):
    """
    Clicks the language switcher and changes the website language to English.
    This only runs if the current language is not already English.
    """
    wait = WebDriverWait(driver, 10)

    try:
        # Check if language button text is already "English"
        try:
            lang_button_text = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.mat-mdc-menu-trigger .iso"))
            ).text.strip()

            if "English" in lang_button_text:
                logging.info("🌐 Language is already English — no change needed.")
                return True
        except TimeoutException:
            logging.info("⚠️ Could not detect current language text — attempting change anyway.")

        # Click the language menu button
        lang_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mat-mdc-menu-trigger"))
        )
        lang_button.click()
        time.sleep(0.5)

        # Select "English" option
        english_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'English')]"))
        )
        english_option.click()

        time.sleep(2)
        logging.info("✅ Language changed to English.")
        return True

    except Exception as e:
        logging.info(f"❌ Failed to change language: {e}")
        return False

# ---------------- Your existing helper functions ---------------- #

def search_license(driver, license_no):
    try:
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='licenseNo']"))
        )
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        
        search_input.clear()
        search_input.send_keys(license_no)

        try:
            search_button.click()
        except:
            driver.execute_script("arguments[0].click();", search_button)

        time.sleep(3)
        return True
    except Exception as e:
        logging.info(f"Error searching for license {license_no}: {str(e)}")
        return False

def extract_main_data(driver):
    data = {
        "Business/Person Name English": "",
        "Legal Condition": "",
        "TIN": "",
        "Registered No": "",
        "Capital": "",
        "Registered Date": ""
    }
    time.sleep(2)
    try:
        all_text_elements = driver.find_elements(By.TAG_NAME, "p")
        if len(all_text_elements) != 28:
            return False
        for elem in all_text_elements:
            text = elem.text.strip()
            if text:
                if "Business / Person Name English" in text or "Business/Person Name English" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        data["Business/Person Name English"] = next_elem.text.strip()
                    except:
                        pass
                if "TIN" in text or "Tin" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        data["TIN"] = next_elem.text.strip()
                    except:
                        pass
                if "Registered No" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        data["Registered No"] = next_elem.text.strip()
                    except:
                        pass
                if "Capital" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        data["Capital"] = next_elem.text.strip()
                    except:
                        pass
                if "Registered Date" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        data["Registered Date"] = next_elem.text.strip()
                    except:
                        pass
                if "Legal Condition" in text:
                    siblings = elem.find_elements(By.XPATH, "following-sibling::*")
                    for sib in siblings:
                        txt = sib.text.strip()
                        if txt:
                            data["Legal Condition"] = txt
                            break
    except Exception as e:
        logging.info(f"Error in main extraction: {e}")

    return data

def safely_extract_main_data(driver, attempt=0, limit=3):
    if attempt >= limit:
        return {"Status": "Unable to get details"}
    main_data = extract_main_data(driver)
    if not main_data:
        return safely_extract_main_data(driver, attempt+1, limit)
    return main_data

def save_to_csv(data, filename):
    if not data:
        return
    fieldnames = set()
    for record in data:
        fieldnames.update(record.keys())
    fieldnames = sorted(fieldnames)

    with open(filename, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if csvfile.tell() == 0:
            writer.writeheader()
        writer.writerows(data)

# ---------------- Main ---------------- #

def main():
    driver = setup_driver()
    logging.info("Driver setup successful")
    all_data = []
    last_processed_tin = ""
    
    try:
        driver.get(BASE_URL)
        logging.info(f"Navigating to: {BASE_URL}")
        time.sleep(3)

        if not change_language_to_english(driver):
            logging.info("⚠️ Proceeding without language change — may affect results.")
        
        for i, license_no in enumerate(LICENSE_NUMBERS):
            last_processed_tin = license_no
            logging.info(f"\n--- Processing license {i+1}/{len(LICENSE_NUMBERS)}: {license_no} ---")
            record = {"License Number": license_no}
            
            if not search_license(driver, license_no):
                record["Status"] = "Search failed"
                all_data.append(record)
                continue
            
            time.sleep(2)
            
            try:
                no_license_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'No license')]")
                if no_license_elements:
                    record["Status"] = "No license found"
                    all_data.append(record)
                    continue
            except:
                pass
                
            main_data = safely_extract_main_data(driver)
            record.update(main_data)

            record["Status"] = "Success"
            all_data.append(record)
            
            if i < len(LICENSE_NUMBERS) - 1:
                time.sleep(2)
            
            if len(all_data) >= 5:
                save_to_csv(all_data, OUTPUT_CSV)
                all_data = []
            
        save_to_csv(all_data, OUTPUT_CSV)
        logging.info(f"\n🎉 Data collection completed! Saved to {OUTPUT_CSV}")
        
    except Exception as e:
        logging.info(f"❌ Error: {str(e)}")
    finally:
        driver.quit()
        logging.info("✅ Browser closed successfully")

if __name__ == "__main__":
    main()