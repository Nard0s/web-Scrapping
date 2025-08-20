import csv
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,                     # log level
    format="%(asctime)s [%(levelname)s] %(message)s",  # log format
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),  # write to file
        logging.StreamHandler()                            # also logging.info to console
    ]
)

# Configuration
import csv

with open('tin.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    tin = [row[0] for row in reader]

LICENSE_NUMBERS = tin[:10]
OUTPUT_CSV = "business_data_1.csv"
WEBDRIVER_PATH = "/snap/bin/brave"  # e.g., "chromedriver" if in PATH
BASE_URL = "https://etrade.gov.et/business-license-checker"  # Replace with actual URL

def setup_driver():
    options = Options()
    
    # Firefox options for headless operation
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-images')  # Faster loading
    options.add_argument('--disable-javascript')  # If you don't need JS
    
    # Try multiple approaches to get the Firefox driver
    geckodriver_paths = [
    r"C:\Program Files\geckodriver\geckodriver.exe",
    r"C:\Program Files (x86)\geckodriver\geckodriver.exe",
    r"C:\WebDrivers\geckodriver.exe",
    r".\geckodriver.exe"  # current directory
    ]

    driver = None
    
    # Approach 1: Try to find system geckodriver first (fastest, no download)
    if not driver:
        try:
            logging.info("Trying system geckodriver...")
            # Check common locations for geckodriver
            geckodriver_paths = [
                "/usr/bin/geckodriver",
                "/usr/local/bin/geckodriver",
                "/snap/bin/geckodriver",
                "./geckodriver"  # Current directory
            ]
            
            geckodriver_path = next((p for p in geckodriver_paths if os.path.exists(p)), None)
            
            if geckodriver_path:
                service = Service(executable_path=geckodriver_path)
                driver = webdriver.Firefox(service=service, options=options)
                logging.info(f"System geckodriver successful: {geckodriver_path}")
            else:
                logging.info("No system geckodriver found")
        except Exception as e:
            logging.info(f"System geckodriver failed: {e}")
    
    # Approach 2: Try GeckoDriverManager with timeout (may hang on slow networks)
    if not driver:
        try:
            logging.info("Trying GeckoDriverManager (this may take a while)...")
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("GeckoDriverManager download timed out")
            
            # Set a timeout for the download
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(60)  # 60 second timeout for download
            
            try:
                service = Service(GeckoDriverManager().install())
                signal.alarm(0)  # Cancel timeout
                driver = webdriver.Firefox(service=service, options=options)
                logging.info("GeckoDriverManager successful")
            except TimeoutError:
                logging.info("GeckoDriverManager timed out - network may be slow")
                signal.alarm(0)  # Cancel timeout
            except Exception as e:
                signal.alarm(0)  # Cancel timeout
                logging.info(f"GeckoDriverManager failed: {e}")
                
        except Exception as e:
            logging.info(f"GeckoDriverManager approach failed: {e}")
    
    # Approach 3: Try to find existing geckodriver in cache
    if not driver:
        try:
            logging.info("Trying to find existing geckodriver in cache...")
            # Check if webdriver_manager has already downloaded something
            import tempfile
            
            # Look for existing geckodriver in temp directories
            temp_dirs = [tempfile.gettempdir(), os.path.expanduser("~/.wdm")]
            geckodriver_found = None
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    # Look for geckodriver files
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if 'geckodriver' in file.lower():
                                geckodriver_path = os.path.join(root, file)
                                if os.access(geckodriver_path, os.X_OK):
                                    geckodriver_found = geckodriver_path
                                    break
                        if geckodriver_found:
                            break
                    if geckodriver_found:
                        break
            
            if geckodriver_found:
                logging.info(f"Found cached geckodriver: {geckodriver_found}")
                service = Service(executable_path=geckodriver_found)
                driver = webdriver.Firefox(service=service, options=options)
                logging.info("Cached geckodriver successful")
            else:
                logging.info("No cached geckodriver found")
        except Exception as e:
            logging.info(f"Cached geckodriver approach failed: {e}")
    
    if not driver:
        raise Exception("Could not initialize any Firefox driver. Please ensure Firefox is installed.")
    
    return driver

def search_license(driver, license_no):
    try:
        # First, check if there's an overlay backdrop and wait for it to disappear
        try:
            overlay = driver.find_element(By.CSS_SELECTOR, "div.cdk-overlay-backdrop.cdk-overlay-backdrop-showing")
            if overlay.is_displayed():
                logging.info(f"Waiting for overlay to disappear...")
                # Wait for overlay to disappear
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "div.cdk-overlay-backdrop.cdk-overlay-backdrop-showing"))
                )
                time.sleep(1)  # Small delay to ensure overlay is gone
        except:
            pass  # No overlay found, continue normally
        
        # Also check for and close any popup modals that might be open
        try:
            popup_close_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Close'], .close, .modal-close, [data-dismiss='modal']")
            for close_btn in popup_close_buttons:
                if close_btn.is_displayed():
                    logging.info("Found popup modal, closing it...")
                    close_btn.click()
                    time.sleep(1)
        except:
            pass  # No popups found, continue normally
        
        # Find search input and button
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='licenseNo']"))
        )
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        
        # Clear and enter license number
        search_input.clear()
        search_input.send_keys(license_no)
        
        # Try to click the button, if it fails due to overlay, use JavaScript click
        try:
            search_button.click()
        except Exception as click_error:
            if "ElementClickInterceptedError" in str(click_error):
                logging.info(f"Button click intercepted, trying JavaScript click...")
                driver.execute_script("arguments[0].click();", search_button)
            else:
                raise click_error
        
        # Wait for results to load
        time.sleep(3)  # Increased wait time for results
        
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
    
    # Wait for the page to fully load and show results
    time.sleep(2)
    
    # Debug: logging.info page source to see what's actually there
    logging.info("Debug: Checking page content...")
    page_text = driver.page_source
    if "Business" in page_text or "Person" in page_text:
        logging.info("Debug: Page contains business/person text")
    else:
        logging.info("Debug: Page does not contain expected business text")
    
    # Try multiple approaches to find the data
    try:
        # Approach 1: Look for common patterns
        all_text_elements = driver.find_elements(By.TAG_NAME, "p")
        logging.info(f"Debug: Found {len(all_text_elements)} paragraph elements")

        if len(all_text_elements) != 28:
            return False
            
        
        for elem in all_text_elements:
            text = elem.text.strip()
            if text:
                logging.info(f"Debug: Found text: {text[:100]}...")
                
                # Extract Business/Person Name English
                if "Business / Person Name English" in text or "Business/Person Name English" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        if next_elem:
                            data["Business/Person Name English"] = next_elem.text.strip()
                            logging.info(f"Debug: Found Business Name English: {data['Business/Person Name English']}")
                    except:
                        pass
                
                # Extract TIN
                if "TIN" in text or "Tin" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        if next_elem:
                            data["TIN"] = next_elem.text.strip()
                            logging.info(f"Debug: Found TIN: {data['TIN']}")
                    except:
                        pass
                
                # Extract Registered No
                if "Registered No" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        if next_elem:
                            data["Registered No"] = next_elem.text.strip()
                            logging.info(f"Debug: Found Registered No: {data['Registered No']}")
                    except:
                        pass
                
                # Extract Capital
                if "Capital" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        if next_elem:
                            data["Capital"] = next_elem.text.strip()
                            logging.info(f"Debug: Found Capital: {data['Capital']}")
                    except:
                        pass
                
                # Extract Registered Date
                if "Registered Date" in text:
                    try:
                        next_elem = elem.find_element(By.XPATH, "following-sibling::*")
                        if next_elem:
                            data["Registered Date"] = next_elem.text.strip()
                            logging.info(f"Debug: Found Registered Date: {data['Registered Date']}")
                    except:
                        pass

                # Extract Legal Condition
                if "Legal Condition" in text:
                    siblings = elem.find_elements(By.XPATH, "following-sibling::*")
                    for sib in siblings:
                        txt = sib.text.strip()
                        if txt:  # first non-empty
                            data["Legal Condition"] = txt
                            logging.info(f"Debug: Found Legal Condition: {data['Legal Condition']}")
                            break
                        
    except Exception as e:
        logging.info(f"Debug: Error in main extraction: {e}")

    
    logging.info(f"Debug: Final extracted data: {data}")
    return data

def click_view_button(driver):
    try:
        # Find and click the first "view" button
        view_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[mat-stroked-button][color='primary']"))
        )
        view_button.click()
        time.sleep(2)  # Wait for details to load
        return True
    except (NoSuchElementException, TimeoutException):
        return False

def save_to_csv(data, filename):
    if not data:
        return
        
    # Get all possible fieldnames from all records
    fieldnames = set()
    for record in data:
        fieldnames.update(record.keys())
    
    fieldnames = sorted(fieldnames)
    
    with open(filename, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        # writer.writeheader()
        if csvfile.tell() == 0:   # pointer is at beginning → file is empty
            writer.writeheader()
        writer.writerows(data)

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
        time.sleep(0.5)  # Let menu render

        # Select "English" option from the dropdown
        english_option = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'English')]"))
        )
        english_option.click()

        # Wait for page reload/translation
        time.sleep(2)

        logging.info("✅ Language changed to English.")
        return True

    except Exception as e:
        logging.info(f"❌ Failed to change language: {e}")
        return False

def safely_extract_main_data(driver, attempt=0, limit=3):
    current_iter = attempt
    if attempt >= limit:
        return {"Status": "Unable to get details"}
    main_data = extract_main_data(driver)
    if not main_data:
        safely_extract_main_data(driver, current_iter+1)
    return main_data
    

def main():
    driver = setup_driver()
    logging.info("Driver setup successful")
    all_data = []
    last_processed_tin = ""
    
    try:
        driver.get(BASE_URL)
        logging.info(f"Navigating to: {BASE_URL}")
        time.sleep(3)  # Wait for page to fully load

        # Change language if needed
        if not change_language_to_english(driver):
            logging.info("⚠️ Proceeding without language change — may affect results.")
        
        for i, license_no in enumerate(LICENSE_NUMBERS):
            last_processed_tin = license_no
            logging.info(f"\n--- Processing license {i+1}/{len(LICENSE_NUMBERS)}: {license_no} ---")
            record = {"License Number": license_no}
            
            # Try to search for the license
            if not search_license(driver, license_no):
                record["Status"] = "Search failed"
                all_data.append(record)
                logging.info(f"❌ Search failed for license: {license_no}")
                continue
            
            # Wait a bit more for the page to settle after search
            time.sleep(2)
            
            # Check if "No license" message appears
            try:
                no_license_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'No license')]")
                if no_license_elements:
                    record["Status"] = "No license found"
                    all_data.append(record)
                    logging.info(f"ℹ️ No license found for: {license_no}")
                    continue
            except Exception as e:
                logging.info(f"Warning checking for 'No license' message: {e}")
                pass
                
            # Extract main data
            logging.info(f"Extracting main data for license: {license_no}")
            main_data = safely_extract_main_data(driver)
            record.update(main_data)

            
            record["Status"] = "Success"
            all_data.append(record)
            logging.info(f"✅ Successfully processed license: {license_no}")
            
            # Small delay between searches to avoid overwhelming the server
            if i < len(LICENSE_NUMBERS) - 1:  # Don't delay after the last one
                time.sleep(2)
            
            if len(all_data) >= 5:
                save_to_csv(all_data, OUTPUT_CSV)
                all_data = []
            
        save_to_csv(all_data, OUTPUT_CSV)
        logging.info(f"\n🎉 Counter: Last Processed TIN: {last_processed_tin}")
        logging.info(f"\n🎉 Data collection completed! Saved to {OUTPUT_CSV}")
        logging.info(f"📊 Total records processed: {len(all_data)}")
        
    except Exception as e:
        logging.info(f"\n❌ Counter: Last Processed TIN: {last_processed_tin}")
        logging.info(f"❌ An error occurred: {str(e)}")
        import traceback
        traceback.logging.info_exc()
    finally:
        logging.info("🔄 Closing browser...")
        driver.quit()
        logging.info("✅ Browser closed successfully")

if __name__ == "__main__":
    main()