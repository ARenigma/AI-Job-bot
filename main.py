import os
import re
import json
import time
import base64
import subprocess
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pdfplumber


linkedin_username = os.getenv("LINKEDIN_EMAIL")
linkedin_password = os.getenv("LINKEDIN_PASSWORD")

if not linkedin_username or not linkedin_password:
    print("Error: LinkedIn credentials not found in environment variables.")
else:
    print("Credentials loaded from environment variables.")

config = load_config()
linkedin_email = os.getenv(config["linkedin_email_env"])
linkedin_password = os.getenv(config["linkedin_password_env"])    

# Configuration
CONFIG = {
    "job_title": "Data Analyst", 
    "locations": ["India", "Remote"],
    "min_salary": 1600000,
    "job_type": ["Remote", "Hybrid"],
    "job_duration": "Full Time",
    "resume_path": "resume.pdf",
    "linkedin_credentials": "secrets.enc",  # Encrypted credentials file
    "rate_limit_delay": 10,  # Delay in seconds between requests
    "max_retries": 3,  # Max retries for failed operations
}

# Generate a key for encryption (store this securely)
ENCRYPTION_KEY = b'your-encryption-key-here'  # Replace with a securely generated key
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_credentials(username, password):
    """Encrypt LinkedIn credentials"""
    credentials = f"{username}:{password}"
    encrypted = cipher_suite.encrypt(credentials.encode())
    with open(CONFIG['linkedin_credentials'], 'wb') as f:
        f.write(encrypted)

def decrypt_credentials():
    """Decrypt LinkedIn credentials"""
    with open(CONFIG['linkedin_credentials'], 'rb') as f:
        encrypted = f.read()
    decrypted = cipher_suite.decrypt(encrypted).decode()
    return decrypted.split(':')

def parse_resume(pdf_path):
    """Extract text from PDF resume with error handling"""
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error parsing resume: {e}")
        return None

def generate_cover_letter(resume_text, job_desc, config):
    """Use Ollama to generate personalized cover letter with retry logic"""
    prompt = f"""
    Generate a concise, personalized cover letter using this resume:
    {resume_text[:2000]}
    
    For this job description:
    {job_desc[:2000]}
    
    Requirements:
    - Address hiring manager
    - 3 short paragraphs max
    - Match resume experience to job requirements
    - Include {config['job_title']} and {config['locations'][0]}
    - Professional tone
    """
    
    for attempt in range(CONFIG['max_retries']):
        try:
            cmd = f"ollama run llama3 '{prompt}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Attempt {attempt + 1} failed. Retrying...")
                time.sleep(CONFIG['rate_limit_delay'])
        except Exception as e:
            print(f"Error generating cover letter: {e}")
    return None

def generate_resume(resume_text, job_desc):
    """Tailor resume using AI with retry logic"""
    prompt = f"""
    Modify this resume for the following job description:
    {job_desc[:2000]}
    
    Original resume:
    {resume_text[:2000]}
    
    Instructions:
    - Prioritize relevant experience
    - Add keywords from job description
    - Keep formatting simple
    - Remove irrelevant sections
    """
    
    for attempt in range(CONFIG['max_retries']):
        try:
            cmd = f"ollama run llama3 '{prompt}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Attempt {attempt + 1} failed. Retrying...")
                time.sleep(CONFIG['rate_limit_delay'])
        except Exception as e:
            print(f"Error generating resume: {e}")
    return None

def apply_to_job(cover_letter, tailored_resume, job_url):
    """Automate LinkedIn job application with error handling and rate limiting"""
    username, password = decrypt_credentials()
    
    # Initialize Selenium WebDriver
    driver = webdriver.Chrome()  # Ensure ChromeDriver is installed
    driver.get("https://www.linkedin.com/login")
    
    try:
        # Login to LinkedIn
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        # Navigate to job URL
        driver.get(job_url)
        time.sleep(CONFIG['rate_limit_delay'])
        
        # Click "Easy Apply" button
        easy_apply_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Easy Apply')]"))
        )
        easy_apply_button.click()
        
        # Fill out application form (example implementation)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//textarea[@name='coverLetter']"))).send_keys(cover_letter)
        
        # Upload tailored resume
        resume_input = driver.find_element(By.XPATH, "//input[@type='file']")
        resume_input.send_keys(os.path.abspath("tailored_resume.pdf"))  # Save tailored_resume as PDF first
        
        # Submit application
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit Application')]"))
        )
        submit_button.click()
        
        print(f"Successfully applied to job: {job_url}")
        
    except (TimeoutException, NoSuchElementException) as e:
        print(f"Error applying to job: {e}")
    finally:
        driver.quit()

def main():
    # Parse resume
    resume_text = parse_resume(CONFIG['resume_path'])
    if not resume_text:
        print("Failed to parse resume. Exiting.")
        return
    
    # Example job listing (replace with actual job scraping logic)
    job_listings = [
        {
            "title": "Software Engineer",
            "location": "New York",
            "salary": 130000,
            "type": "Remote",
            "description": "Looking for a skilled software engineer...",
            "url": "https://www.linkedin.com/jobs/view/1234567890"
        }
    ]
    
    # Filter jobs
    filtered_jobs = [job for job in job_listings if filter_job_listing(job, CONFIG)]
    
    # Process each job
    for job in filtered_jobs:
        print(f"Processing: {job['title']}")
        
        # Generate documents
        cover_letter = generate_cover_letter(resume_text, job['description'], CONFIG)
        tailored_resume = generate_resume(resume_text, job['description'])
        
        if cover_letter and tailored_resume:
            # Save tailored resume as PDF (example implementation)
            with open("tailored_resume.pdf", "w") as f:
                f.write(tailored_resume)
            
            # Apply to job
            apply_to_job(cover_letter, tailored_resume, job['url'])
            time.sleep(CONFIG['rate_limit_delay'])  # Rate limiting

if __name__ == "__main__":
    main()