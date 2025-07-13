import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ToolRentalTest(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.driver.get("http://localhost:5000/register")

    def test_user_registration(self):
        driver = self.driver
        driver.find_element(By.NAME, "name").send_keys("Test User")
        driver.find_element(By.NAME, "email").send_keys("test@example.com")
        driver.find_element(By.NAME, "password").send_keys("password123")
        driver.find_element(By.NAME, "zip_code").send_keys("12345")
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        self.assertIn("Welcome, Test User", driver.page_source)

    def tearDown(self):
        self.driver.quit()

if __name__ == "__main__":
    unittest.main()
