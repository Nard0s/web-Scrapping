import csv
import time
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

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
import csv

with open('tin.csv', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    tin = [row[0] for row in reader]

LICENSE_NUMBERS = ["0004385072","0004385071","0053973541","0008205440","0024247882","0004921343","0003264040","0001123047","0003160938", "0028970998"]
OUTPUT_CSV = "business_data_2.csv"
BASE_URL = "https://etrade.gov.et/business-license-checker" 
def setup_driver():
    import tempfile
    import zipfile
    import shutil
    import signal

    options = Options()
    # Chrome options for headless operation
    options.add_argument('--headless')  # Comment out to see the browser
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-images')  # Faster loading
    options.add_argument('--remote-allow-origins=*')  # Fix for Chrome 113+
    
    driver = None

    # helper: try to start chrome with given executable path
    def try_start_chrome(exe_path):
        try:
            service = Service(executable_path=exe_path)
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logging.info(f"Failed to start Chrome using {exe_path}: {e}")
            return None

    # helper: extract chromedriver from zip, return path or None
    def extract_chromedriver_from_zip(zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                candidate = None
                for member in z.namelist():
                    bn = os.path.basename(member).lower()
                    if 'chromedriver' in bn and (bn.endswith('.exe') or bn == 'chromedriver'):
                        candidate = member
                        break
                if not candidate:
                    return None
                extract_dir = tempfile.mkdtemp(prefix="chromedriver_")
                z.extract(candidate, extract_dir)
                extracted = os.path.normpath(os.path.join(extract_dir, candidate))
                # if nested, try to find file inside extract_dir
                if not os.path.exists(extracted):
                    for r, _, files in os.walk(extract_dir):
                        for f in files:
                            if 'chromedriver' in f.lower():
                                extracted = os.path.join(r, f)
                                break
                        if os.path.exists(extracted):
                            break
                try:
                    os.chmod(extracted, 0o755)
                except Exception:
                    pass
                return extracted
        except Exception as e:
            logging.info(f"Could not extract chromedriver from zip {zip_path}: {e}")
            return None

    # Approach 1: Try system chromedriver paths
    try:
        logging.info("Trying system chromedriver...")
        chromedriver_paths = [
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver",
            "./chromedriver",  # Current directory
            "C:\\chromedriver.exe"
        ]
        chromedriver_path = next((p for p in chromedriver_paths if os.path.exists(p)), None)
        if chromedriver_path:
            driver = try_start_chrome(chromedriver_path)
            if driver:
                logging.info(f"System chromedriver successful: {chromedriver_path}")
        else:
            logging.info("No system chromedriver found")
    except Exception as e:
        logging.info(f"System chromedriver failed: {e}")

    # Approach 2: Try ChromeDriverManager (no SIGALRM on Windows)
    if not driver:
        try:
            logging.info("Trying ChromeDriverManager (this may take a while)...")
            try:
                service_path = ChromeDriverManager().install()
                driver = try_start_chrome(service_path)
                if driver:
                    logging.info("ChromeDriverManager successful")
            except Exception as e:
                logging.info(f"ChromeDriverManager failed: {e}")
        except Exception as e:
            logging.info(f"ChromeDriverManager approach failed: {e}")

    # Approach 3: Search cache for chromedriver executables or zips and extract if needed
    if not driver:
        try:
            logging.info("Trying to find existing chromedriver in cache...")
            search_dirs = [
                tempfile.gettempdir(),
                os.path.expanduser("~/.wdm"),
                os.path.join(os.path.expanduser("~"), ".wdm", "drivers"),
                os.path.join(os.path.expanduser("~"), ".cache", "webdriver"),
            ]
            chromedriver_found = None
            extracted_tempdir = None

            for sd in search_dirs:
                if not sd or not os.path.exists(sd):
                    continue
                for root, _, files in os.walk(sd):
                    for fname in files:
                        if 'chromedriver' not in fname.lower():
                            continue
                        full = os.path.join(root, fname)
                        # if it's an executable already
                        if fname.lower().endswith('.exe') or os.access(full, os.X_OK):
                            chromedriver_found = full
                            break
                        # if it's a zip, try to extract
                        if fname.lower().endswith('.zip'):
                            extracted = extract_chromedriver_from_zip(full)
                            if extracted:
                                chromedriver_found = extracted
                                extracted_tempdir = os.path.dirname(extracted)
                                break
                    if chromedriver_found:
                        break
                if chromedriver_found:
                    break

            if chromedriver_found and os.path.exists(chromedriver_found):
                driver = try_start_chrome(chromedriver_found)
                if driver:
                    logging.info(f"Cached chromedriver successful: {chromedriver_found}")
                else:
                    logging.info(f"Cached chromedriver found but could not start: {chromedriver_found}")
                    # cleanup extracted files if any
                    if extracted_tempdir and os.path.isdir(extracted_tempdir):
                        try:
                            shutil.rmtree(extracted_tempdir)
                        except Exception:
                            pass
            else:
                logging.info("No cached chromedriver found")
        except Exception as e:
            logging.info(f"Cached chromedriver approach failed: {e}")

    # Final fallback: try Firefox if Chrome couldn't be started
    if not driver:
        try:
            logging.info("Attempting Firefox fallback (GeckoDriver)...")
            from selenium.webdriver.firefox.service import Service as FxService
            from selenium.webdriver.firefox.options import Options as FxOptions
            from webdriver_manager.firefox import GeckoDriverManager

            fx_options = FxOptions()
            try:
                fx_options.headless = True
            except Exception:
                pass

            fx_service = FxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=fx_service, options=fx_options)
            logging.info("Firefox fallback successful")
        except Exception as e:
            logging.info(f"Firefox fallback failed: {e}")

    if not driver:
        raise Exception("Could not initialize any Chrome driver. Please ensure Chrome is installed or that a valid chromedriver exists.")

    return driver



def check_overlay(driver):
    # check if there's an overlay backdrop and wait for it to disappear
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
        
def search_license(driver, license_no):
    try:
        check_overlay(driver)
        
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
        
        try:
            message = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "mat-snack-bar-container .mat-mdc-snack-bar-label"))
            )

            if "Business License Doesn't Exist" in message.text:
                return False, "Business License Doesn't Exist"
        except:
            pass

        return True, "Success"
    
    except Exception as e:
        logging.info(f"Error searching for license {license_no}: {str(e)}")
        return False, "Search Failed"

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
    
    # Debug: logging.info page source to see what's actually there
    logging.info("Debug: Checking page content...")
    page_text = driver.page_source
    if "Business" in page_text or "Person" in page_text:
        logging.info("Debug: Page contains business/person text")
    else:
        logging.info("Debug: Page does not contain expected business text")
    
    try:
        all_text_elements = driver.find_elements(By.TAG_NAME, "p")
        logging.info(f"Debug: Found {len(all_text_elements)} paragraph elements")

        
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


def extract_address_data(driver):
    address_data = {
        "Region": "",
        "Zone": "",
        "Sub City/Woreda": "",
        "Kebele": "",
        "House No.": "",
        "Mobile Phone": "",
        "Regular Phone": ""
    }

    # Helper to attempt waiting for an element, fallback to empty string
    def get_text_by_xpath(xpath, timeout=3):
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return elem.text.strip()
        except TimeoutException:
            return ""
        except Exception:
            return ""

    # Use explicit waits per field (short timeouts)
    address_data["Region"] = get_text_by_xpath("//p[contains(text(), 'Region')]/following-sibling::p")
    address_data["Zone"] = get_text_by_xpath("//p[contains(text(), 'Zone')]/following-sibling::p")
    address_data["Sub City/Woreda"] = get_text_by_xpath("//p[contains(text(), 'Sub City/Woreda')]/following-sibling::p")
    address_data["Kebele"] = get_text_by_xpath("//p[contains(text(), 'Kebele')]/following-sibling::p")
    address_data["House No."] = get_text_by_xpath("//p[contains(text(), 'House No.')]/following-sibling::p")
    address_data["Mobile Phone"] = get_text_by_xpath("//p[contains(text(), 'Mobile Phone')]/following-sibling::p")
    address_data["Regular Phone"] = get_text_by_xpath("//p[contains(text(), 'Regular Phone')]/following-sibling::p")

    return address_data


def click_view_button(driver):
    try:
        # Find and click the first "view" button
        view_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[mat-stroked-button][color='primary']"))
        )
        try:
            view_button.click()
        except Exception as click_err:
            # If overlay intercepts, try JS click
            logging.info(f"Click intercepted, trying JS click: {click_err}")
            driver.execute_script("arguments[0].click();", view_button)

        # Wait for the details/address labels to appear (these can load asynchronously)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//p[contains(text(), 'Region') or contains(text(), 'Zone') or contains(text(), 'Kebele') or contains(text(), 'Mobile Phone') or contains(text(), 'House No.')]"
                    )
                )
            )
            time.sleep(0.5)  # small stabilization pause
            return True
        except TimeoutException:
            logging.info("Timed out waiting for address/details panel after clicking view")
            return False

    except (NoSuchElementException, TimeoutException) as e:
        logging.info(f"No view button found or clickable: {e}")
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
      
    

def main():
    total_records_processed = 0
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
            record = {}
            record = {"License Number": license_no}
            
            # Try to search for the license
            search_status, message = search_license(driver, license_no)
            if not search_status and message == "Search Failed":
                record["Status"] = message
                all_data.append(record)
                logging.info(f"❌ Search failed for license: {license_no}")
                continue
            
            if not search_status and message == "Business License Doesn't Exist":
                record["Status"] = message
                all_data.append(record)
                logging.info(f"❌ Business License Doesn't Exist: {license_no}")
                continue
            
            record["Status"] = message

            # Wait a bit more for the page to settle after search
            time.sleep(2)

            check_overlay(driver)
            
            # Extract main data
            logging.info(f"Extracting main data for license: {license_no}")
            main_data = extract_main_data(driver)
            record.update(main_data)


            # Try to click view button and get address details
            logging.info(f"Attempting to get address data for license: {license_no}")
            if click_view_button(driver):
                address_data = extract_address_data(driver)
                record.update(address_data)
                logging.info(f"✅ Address data extracted for license: {license_no}")
            else:
                logging.info(f"⚠️ Could not get address view for license: {license_no}")
                record["Status"] = "Address Data Not Found"


            
            all_data.append(record)
            logging.info(f"✅ Successfully processed license: {license_no}")
            
            # Small delay between searches to avoid overwhelming the server
            if i < len(LICENSE_NUMBERS) - 1:  # Don't delay after the last one
                time.sleep(2)
            

            if len(all_data) >= 5:
                save_to_csv(all_data, OUTPUT_CSV)
                logging.info(f"\n🎉 Counter: Last Saved Business Data: {all_data[-1]}")
                total_records_processed += len(all_data)
                all_data = []
            
        save_to_csv(all_data, OUTPUT_CSV)
        logging.info(f"\n🎉 Counter: Last Processed TIN: {last_processed_tin}")
        logging.info(f"\n🎉 Data collection completed! Saved to {OUTPUT_CSV}")
        logging.info(f"📊 Total records processed: {total_records_processed}")
        
    except Exception as e:
        logging.info(f"\n❌ Counter: Last Processed TIN: {last_processed_tin}")
        logging.exception(f"❌ An error occurred: {e}")
    finally:
        logging.info("🔄 Closing browser...")
        try:
            if driver:
                driver.quit()
                logging.info("✅ Browser closed successfully")
            else:
                logging.info("No driver to close")
        except Exception as e:
            logging.info(f"Error closing driver: {e}")

# Entry point so the script actually runs when invoked directly
if __name__ == "__main__":
    main()
