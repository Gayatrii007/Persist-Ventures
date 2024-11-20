from telegram import Update
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import Application, CommandHandler, CallbackContext
import logging
import instaloader
import tweepy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import csv

# Logging setup
logging.basicConfig(level=logging.INFO)
import os
import re

TELEGRAM_TOKEN = Telegram_Token
TWITTER_BEARER_TOKEN = BEARER_TOKEN

import time

import requests
from bs4 import BeautifulSoup

def search_google(query):
    """
    Perform a Google search using Selenium and return the top results.
    """
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    # Set up Selenium WebDriver options
    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    url = f"https://www.google.com/search?q={query}"
    driver.get(url)

    try:
        # Wait for results to load (use an explicit wait)
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.tF2Cxc'))
        )

        results = []
        # Locate and parse results
        for result in driver.find_elements(By.CSS_SELECTOR, 'div.tF2Cxc'):
            try:
                title = result.find_element(By.CSS_SELECTOR, 'h3').text
                link = result.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                snippet_element = result.find_elements(By.CSS_SELECTOR, '.VwiC3b')
                snippet = snippet_element[0].text if snippet_element else "No snippet available"
                results.append({'title': title, 'link': link, 'snippet': snippet})
            except Exception as e:
                print(f"Error parsing result: {e}")
                continue

    except Exception as e:
        print(f"Error loading Google search results: {e}")
        results = []

    finally:
        driver.quit()

    return results

TELEGRAM_TOKEN = os.getenv("Telegram_Token")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Start Command Handler
async def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    await update.message.reply_text("Hello! I am your bot. How can I help you today?")

async def handle_input(update, context):
    user_input = update.message.text.strip()
    if not user_input:
        await update.message.reply_text("Please provide a search term.")
        return
    await update.message.reply_text(f"Searching Google for: {user_input}...")
    
    # Perform a Google search
    results = search_google(user_input)
    
    if results:
        # Format results as a message
        response = "Here are the top search results:\n\n"
        for result in results[:5]:  # Limit to top 5 results
            response += f"Title: {result['title']}\n"
            response += f"Link: {result['link']}\n"
            response += f"Snippet: {result['snippet']}\n\n"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("No results found. Try a different query.")

# Scrape Command Handler
async def scrape(update: Update, context: CallbackContext):
    """Handle the /scrape command."""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /scrape <username> <platform>")
        return

    username = context.args[0]
    platform = context.args[1].lower()

    if platform not in ["instagram", "tiktok", "twitter"]:
        await update.message.reply_text("Supported platforms: Instagram, TikTok, Twitter")
        return

    await update.message.reply_text(f"Scraping {platform} profile for {username}...")

    try:
        # Scrape the relevant profile
        if platform == "instagram":
            email = scrape_instagram(username)
        elif platform == "tiktok":
            email = scrape_tiktok(username)
        elif platform == "twitter":
            email = scrape_twitter(username)

        # Save the result in CSV
        if email:
            await update.message.reply_text(f"Found email: {email}")
            save_to_csv(username, platform, email)  # Save data to CSV
        else:
            await update.message.reply_text("No email found.")
    except Exception as e:
        await update.message.reply_text(f"Error occurred: {str(e)}")

# Instagram Scraping
def scrape_instagram(username: str) -> str:
    loader = instaloader.Instaloader()

    try:
        # Load session or login
        loader.load_session_from_file('username')  # Replace with your username
    except FileNotFoundError:
        try:
            loader.login('username', 'password')  # Replace with your credentials
            loader.save_session_to_file()  # Save session for reuse
        except Exception as e:
            print(f"Login failed: {e}")
            return None

    try:
        # Fetch the profile and extract bio
        profile = instaloader.Profile.from_username(loader.context, username)
        bio = profile.biography
        email = extract_email_from_text(bio)  # Extract email if present
        return email
    except Exception as e:
        print(f"Failed to scrape Instagram: {e}")
        return None


# TikTok Scraping (using Selenium)
def scrape_tiktok(username: str) -> str:
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    url = f"https://www.tiktok.com/@{username}"
    driver.get(url)

    try:
        bio_element = driver.find_element(By.XPATH, "//div[@data-e2e='user-bio']")
        bio = bio_element.text
        email = extract_email_from_text(bio)
    finally:
        driver.quit()

    return email

# Twitter Scraping (using Tweepy)
def scrape_twitter(username: str) -> str:
    try:
        # Initialize the client with your bearer token
        client = tweepy.Client(bearer_token=BEARER_TOKEN)

        # Fetch the user's details
        response = client.get_user(username=username, user_fields=["description"])

        if response.data:
            bio = response.data.description
            if bio:
                return extract_email_from_text(bio)
            else:
                print("No description found for this user.")
                return None
        else:
            print("User not found or API error.")
            return None

    except tweepy.TweepyException as e:
        print(f"Twitter scraping failed: {e}")
        return None


# Email Extraction using regex
def extract_email_from_text(text: str) -> str:
    email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_regex, text)
    return match.group(0) if match else None

# Save scraped data to CSV
def save_to_csv(username: str, platform: str, email: str):
    # CSV file path
    csv_file = "scraped_data.csv"

    # Check if the file exists
    file_exists = False
    try:
        with open(csv_file, mode='r'):
            file_exists = True
    except FileNotFoundError:
        pass

    # Open the CSV file in append mode
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        fieldnames = ["Username", "Platform", "Email"]  # Columns for the CSV
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write the header only if the file is new
        if not file_exists:
            writer.writeheader()

        # Write the scraped data into the CSV
        writer.writerow({"Username": username, "Platform": platform, "Email": email})

# Main function to run the bot
def main():
    application = Application.builder().token("TELEGRAM_TOKEN").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("scrape", scrape))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()

