import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import schedule
import time
import requests
from bs4 import BeautifulSoup
import json
import sys

load_dotenv()  # Load EMAIL credentials from .env file

# Load credentials from environment
sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("EMAIL_PASSWORD")
# Deduplicate recipient emails to avoid sending multiple emails to the same address
recipient_emails = list(set(filter(None, [os.getenv("RECIPIENT_EMAIL"), os.getenv("RECIPIENT_EMAIL2")])))

lululemon_link_1 = "https://shop.lululemon.com/p/mens-jackets-and-outerwear/Down-For-It-All-Hoodie/_/prod9200786?color=0001"
lululemon_link_2 = "https://shop.lululemon.com/p/mens-jackets-and-outerwear/Pace-Breaker-Jacket/_/prod11670131?cid=Google_SHOP_US_NAT_EN_X_BrandShop_Incr-All_OMNI_GEN_Y24_ag-SHOP_G_US_EN_DM_M_GEN_NO_Tops-Jackets&color=0001&gad_campaignid=21471260535&gad_source=1&gbraid=0AAAAADL8Avk5CDt35HKBgpfRSuD0CpJvP&gclid=CjwKCAjwkbzEBhAVEiwA4V-yqpMcLNT4qAeAlXO9G-dH0QPZKbelVx2jrlqZrfrChowBqSPFpaclcxoCx5oQAvD_BwE&gclsrc=aw.ds&locale=en_US&sl=US&sz=S"
nike_link = "https://www.nike.com/t/unlimited-mens-repel-hooded-versatile-jacket-56pDjs/FB7551-010"
links = {}
links["lululemon"] = [lululemon_link_1, lululemon_link_2]
links["nike"] = [nike_link]


def scrape_lululemon(product_link):
    
    response = requests.get(product_link)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    name_element = soup.find("meta", attrs={'property': 'og:title'})
    price_element = soup.find('span', class_='price') 
    image = soup.find('meta', property='og:image')['content'] if soup.find('meta', property='og:image') else ''

    name = name_element.get("content") if name_element else "Product name not found"
    price = price_element.get_text(strip=True) if price_element else "Price not found"

    return name, price, image

def scrape_nike(product_link):
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(product_link, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find and parse the JSON-LD product data
    json_ld = soup.find("script", type="application/ld+json")
    data = json.loads(json_ld.string)
    image = soup.find('meta', property='og:image')['content'] if soup.find('meta', property='og:image') else ''

    # Extract name and price
    name = data.get("name") if data else "Product name not found"
    price = "$" + str(data.get("offers", {}).get("lowPrice")) + "USD" if data and "offers" in data else "Price not found"

    return name, price, image

def send_combined_email():
    all_products_info = []
    prices_for_subject = []

    for company in links:
        for link in links[company]:
            if company == "lululemon":
                name, price, image = scrape_lululemon(link)
            elif company == "nike":
                name, price, image = scrape_nike(link)
            all_products_info.append((name, price, image, link))
            prices_for_subject.append(price.replace("USD", "").strip())

    # Compose email
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = ", ".join(recipient_emails)

    subject_prices = f"{prices_for_subject[0]}/228, {prices_for_subject[1]}/168, {prices_for_subject[2]}/110" 
    message['Subject'] = f"{subject_prices} – Your Tracked Products"

    # Build email body
    html_lines = [
    "<html><body>",
    "<h2>Here are your tracked products:</h2>"
    ]

    for name, price, image, link in all_products_info:
        # Try to get product image from link preview (via Open Graph)
        card = f"""
        <div style="width: 100%; text-align: center;">
            <div style="
                display: inline-block;
                border: 1px solid #ccc;
                padding: 20px;
                margin-bottom: 20px;
                max-width: 400px;     
            ">
                <a href="{link}" target="_blank"; style="text-decoration: none;">
                    <h2>{name}</h2>
                    <p>{price}</p>
                    <img src="{image}" alt="{name}" style="width: 50%; height: 50%; border: none;" />
                </a>
            </div>
        </div>
        """

        html_lines.append(card)

    html_lines.append("</body></html>")
    html_body = "\n".join(html_lines)
    message.attach(MIMEText(html_body, 'html'))


    # Send email
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        for recipient in recipient_emails:
            server.sendmail(sender_email, recipient, message.as_string())
        server.quit()
        print("Combined email sent successfully.")
    except Exception as e:
        print("Failed to send combined email:", e)

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):  # Bundled with py2app
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def run_scheduler():
    schedule.every().day.at("21:00").do(send_combined_email)  # or use .at("21:00")
    send_combined_email()  # Send immediately for testing
    while True:
        schedule.run_pending()
        time.sleep(1)

# Run
if __name__ == '__main__':
    run_scheduler()
