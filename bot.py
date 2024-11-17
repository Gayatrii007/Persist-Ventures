from telegram import Update
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import Application, CommandHandler, CallbackContext
import logging
import instaloader
import tweepy
from selenium import webdriver
from selenium.webdriver.common.by import By
import csv
import re
import os

# Logging setup
logging.basicConfig(level=logging.INFO)
import os

import requests
from bs4 import BeautifulSoup
import re

TELEGRAM_TOKEN = "YOUR_TOKEN_NUMBER"
TWITTER_BEARER_TOKEN = "TOKEN_BEARER"

def scrape_emails(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.text, 'html.parser')
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", soup.text)
    return list(set(emails))  # Remove duplicates

# Example Usage
query = "fashion influencers email site:instagram.com"
print(scrape_emails(query))

TELEGRAM_TOKEN = os.getenv("YOUR_TOKEN_NUMBER")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Start Command Handler
async def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    await update.message.reply_text("Hello! I am your bot. How can I help you today?")

async def handle_input(update, context):
    user_input = update.message.text
    await update.message.reply_text(f"Searching for: {user_input}")
    
    # Call your scraping function
    query = f"{user_input} site:instagram.com"
    emails = scrape_emails(query)
    
    if emails:
        update.message.reply_text(f"Found emails: {', '.join(emails)}")
    else:
        update.message.reply_text("No emails found. Try a different query.")
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

    # Log in to Instagram (provide your credentials here)
    loader.context.log("Logging in to Instagram...")
    try:
        loader.login('gilehrii', 'qwertyuiop123')  # Replace with your actual Instagram username and password
    except Exception as e:
        print(f"Login failed: {e}")
        return None

    # Now, load the profile after logging in
    try:
        profile = instaloader.Profile.from_username(loader.context, username)
        bio = profile.biography
        # Extract email from bio using regex
        email = extract_email_from_text(bio)
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
    client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
    user = client.get_user(username=username, user_fields=["description"])
    bio = user.data.description
    email = extract_email_from_text(bio)
    return email

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
    application = Application.builder().token("7875405403:AAGY479kstuypz053t_ULPqiQvA0GyxgY88").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("scrape", scrape))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()

