from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import logging
import re
from urllib.parse import urlparse
import atexit
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Render kills HTTP requests after ~30 seconds — one fast attempt, email runs in background
if os.getenv("RENDER"):
    FETCH_TIMEOUT = (5, 15)
    MAX_FETCH_RETRIES = 1
else:
    FETCH_TIMEOUT = (10, 30)
    MAX_FETCH_RETRIES = 3

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize scheduler
scheduler = BackgroundScheduler()

# Global state
class ProductState:
    def __init__(self):
        self.link = ""
        self.details = {}

product_state = ProductState()
state_lock = threading.Lock()

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def fetch_product_page(url):
    """Fetch a product page with browser-like headers."""
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    if "lululemon.com" in url:
        session.get("https://shop.lululemon.com/", timeout=FETCH_TIMEOUT)
        session.headers["Referer"] = "https://shop.lululemon.com/"

    last_error = None
    for attempt in range(1, MAX_FETCH_RETRIES + 1):
        try:
            response = session.get(url, timeout=FETCH_TIMEOUT)
            return response
        except (requests.Timeout, requests.ConnectionError) as e:
            last_error = e
            logger.warning(f"Fetch attempt {attempt}/{MAX_FETCH_RETRIES} failed: {e}")

    raise last_error

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url):
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def parse_lululemon(soup):
    name_element = soup.find("meta", attrs={'property': 'og:title'})
    if not name_element:
        raise ValueError("Product name not found")

    image_element = soup.find('meta', property='og:image')
    image = image_element.get('content', '') if image_element else ''

    original_el = soup.find('span', class_='original-price')
    discounted_el = soup.find('span', class_='discounted-price')
    price_el = soup.find('span', class_='price')

    if original_el and discounted_el:
        return {
            'name': name_element.get("content"),
            'current_price': discounted_el.get_text(strip=True),
            'original_price': original_el.get_text(strip=True),
            'on_sale': True,
            'image': image,
        }

    if not price_el:
        raise ValueError("Price not found")

    return {
        'name': name_element.get("content"),
        'current_price': price_el.get_text(strip=True),
        'original_price': None,
        'on_sale': False,
        'image': image,
    }

def _nike_product(name, price, image, original_price=None):
    current_price = f"${price} USD"
    original = f"${original_price} USD" if original_price is not None else None
    return {
        'name': name,
        'current_price': current_price,
        'original_price': original,
        'on_sale': original is not None,
        'image': image or '',
    }

def _nike_prices_from_offers(offers):
    price = offers.get("price")
    original_price = offers.get("compareAtPrice") or offers.get("wasPrice")
    return price, original_price

def _nike_sku_from_url(url):
    match = re.search(r"/([A-Z0-9-]+)$", url.rstrip("/"), re.I)
    return match.group(1).upper() if match else None

def _nike_variant_matches_url(variant, url, normalized_url):
    offer_url = variant.get("offers", {}).get("url", "").rstrip("/")
    if normalized_url in offer_url or offer_url in normalized_url:
        return True
    sku = _nike_sku_from_url(url)
    if not sku:
        return False
    variant_sku = (variant.get("sku") or variant.get("mpn") or "").upper()
    return sku == variant_sku or offer_url.upper().endswith(sku)

def _enrich_nike_sale_from_next_data(soup, product):
    """JSON-LD often omits the original price — read it from Nike's page data."""
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        return product

    selected = json.loads(script.string).get("props", {}).get("pageProps", {}).get("selectedProduct")
    if not selected:
        return product

    prices = selected.get("prices", {})
    current = prices.get("currentPrice")
    initial = prices.get("initialPrice")
    if current is None or initial is None or initial <= current:
        return product

    enriched = dict(product)
    enriched["current_price"] = f"${current} USD"
    enriched["original_price"] = f"${initial} USD"
    enriched["on_sale"] = True
    return enriched

def parse_nike_next_data(soup):
    """Fallback parser using Nike's embedded page data."""
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        return None

    selected = json.loads(script.string).get("props", {}).get("pageProps", {}).get("selectedProduct")
    if not selected:
        return None

    info = selected.get("productInfo", {})
    prices = selected.get("prices", {})
    current = prices.get("currentPrice")
    if current is None:
        return None

    name = info.get("fullTitle") or info.get("title", "Product")
    image = ""
    images = selected.get("contentImages") or []
    if images:
        image = images[0].get("properties", {}).get("squarish", {}).get("url", "")

    initial = prices.get("initialPrice")
    original = initial if initial and initial != current else None
    return _nike_product(name, current, image, original)

def parse_nike(soup, url):
    scripts = soup.find_all("script", type="application/ld+json")
    if not scripts:
        raise ValueError("Product data not found on Nike page")

    normalized_url = url.rstrip("/")
    sku = _nike_sku_from_url(url)
    image_element = soup.find("meta", property="og:image")
    image = image_element.get("content", "") if image_element else ""

    for script in scripts:
        data = json.loads(script.string)
        items = data if isinstance(data, list) else [data]

        for item in items:
            if item.get("@type") == "ProductGroup":
                name = item.get("name", "Product name not found")
                variants = item.get("hasVariant") or []

                for variant in variants:
                    if not _nike_variant_matches_url(variant, url, normalized_url):
                        continue
                    price, original_price = _nike_prices_from_offers(variant.get("offers", {}))
                    if price is not None:
                        return _nike_product(
                            name, price, variant.get("image") or image, original_price
                        )

                if sku:
                    product = parse_nike_next_data(soup)
                    if product:
                        return product
                    raise ValueError(
                        f"Could not find color/style {sku} on this Nike page. "
                        "Open the exact product in your browser and copy the full URL."
                    )

            if item.get("@type") == "Product":
                name = item.get("name", "Product name not found")
                price, original_price = _nike_prices_from_offers(item.get("offers", {}))
                if price is not None:
                    return _nike_product(name, price, item.get("image") or image, original_price)

    raise ValueError("Price not found on Nike page")

def parse_product_details(url, soup):
    if "nike.com" in url:
        try:
            product = parse_nike(soup, url)
            return _enrich_nike_sale_from_next_data(soup, product)
        except ValueError as e:
            if "Could not find color/style" in str(e):
                raise
            product = parse_nike_next_data(soup)
            if product:
                return product
            raise
    return parse_lululemon(soup)

def fetch_and_parse_product(url):
    """Fetch and parse a product URL without relying on global state."""
    response = fetch_product_page(url)
    if response.status_code == 404:
        raise ValueError(
            "Product not found on Nike. Open the product in your browser "
            "and copy the full URL from the address bar."
        )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    return parse_product_details(url, soup)

def get_product_details(force_refresh=False):
    """Fetch and parse product details. Returns a product dict."""
    try:
        if not product_state.link:
            raise ValueError("Product link not set")

        if (
            not force_refresh
            and product_state.details.get("name")
            and product_state.details.get("_cached_link") == product_state.link
        ):
            return {
                "name": product_state.details["name"],
                "current_price": product_state.details["current_price"],
                "original_price": product_state.details.get("original_price"),
                "on_sale": product_state.details.get("on_sale", False),
                "image": product_state.details.get("image", ""),
            }

        response = fetch_product_page(product_state.link)
        if response.status_code == 404:
            raise ValueError(
                "Product not found on Nike. Open the product in your browser "
                "and copy the full URL from the address bar."
            )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        product = parse_product_details(product_state.link, soup)
        product_state.details = {
            **product,
            "price": product["current_price"],
            "_cached_link": product_state.link,
        }
        return product
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        logger.error(f"Error fetching product details: {str(e)}")
        raise ValueError(
            f"The store blocked this request (HTTP {status}). "
            "Lululemon often blocks automated requests — try a Nike link to test, "
            "or run the app from a personal network instead of work Wi‑Fi/VPN."
        ) from e
    except requests.Timeout as e:
        logger.error(f"Error fetching product details: {str(e)}")
        raise ValueError(
            "The store took too long to respond. Wait a moment and try again."
        ) from e
    except requests.RequestException as e:
        logger.error(f"Error fetching product details: {str(e)}")
        raise ValueError(f"Could not reach the product page: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error in get_product_details: {str(e)}")
        raise

def format_price_html(product):
    """Format price line for email — strikethrough original + sale price when on sale."""
    if product.get('on_sale') and product.get('original_price'):
        return f"""
                    <p>
                        <span style="text-decoration: line-through; color: #888;">{product['original_price']}</span>
                        <span style="color: #00c853; font-weight: bold; font-size: 1.2em;"> {product['current_price']}</span>
                    </p>
                    <p style="color: #d32f2f; font-weight: bold; margin: 0;">ON SALE</p>"""
    return f"""
                    <p style="font-size: 1.2em; font-weight: bold; margin: 0;">
                        {product['current_price']}
                        <span style="color: #666; font-size: 0.85em; font-weight: bold;"> · NOT ON SALE</span>
                    </p>"""

def email_subject_for_product(product):
    if product.get('on_sale') and product.get('original_price'):
        current = product['current_price'].replace('USD', '').strip()
        original = product['original_price'].replace('USD', '').strip()
        return f"{current} / {original} – Your Tracked Product is on sale"
    return f"{product['current_price'].replace('USD', '').strip()} – Your Tracked Product"

def build_product_email_html(products):
    """Build HTML email body with product cards."""
    html_lines = [
        "<html><body style='margin: 0; padding: 0; font-family: Arial, sans-serif;'>",
        "<h2 style='text-align: center;'>Here is your tracked product:</h2>",
    ]

    for product in products:
        price_html = format_price_html(product)
        link = product['link']
        name = product['name']
        image = product['image']
        card = f"""
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center"
               style="border: 1px solid #ccc; max-width: 400px; width: 100%; margin: 0 auto 20px;">
          <tr>
            <td style="padding: 20px; text-align: center;">
              <h2 style="margin: 0 0 12px; font-size: 20px; color: #111;">
                <a href="{link}" target="_blank" style="text-decoration: none; color: #111;">{name}</a>
              </h2>
              {price_html}
              <a href="{link}" target="_blank" style="text-decoration: none; display: block; margin-top: 16px;">
                <img src="{image}" alt="{name}"
                     style="display: block; max-width: 200px; width: 100%; height: auto; margin: 0 auto; border: none;" />
              </a>
            </td>
          </tr>
        </table>
        """
        html_lines.append(card)

    html_lines.append("</body></html>")
    return "\n".join(html_lines)

def send_email(recipient_email, force_refresh=False, product=None, product_link=None):
    """Send email with error handling"""
    try:
        sender_email = os.environ.get('SENDER_EMAIL')
        sender_password = os.environ.get('EMAIL_PASSWORD')

        if not sender_email or not sender_password:
            raise ValueError("Email credentials not properly configured")

        link = (product_link or product_state.link or "").strip()
        if not link:
            raise ValueError("Please set a product link first")

        if product is None:
            logger.info(f"Fetching product details for link: {link}")
            with state_lock:
                product_state.link = link
                product = get_product_details(force_refresh=force_refresh)
        product = dict(product)
        product['link'] = link

        logger.info(f"Product details fetched: {product_state.details}")

        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient_email
        message['Subject'] = email_subject_for_product(product)

        html_body = build_product_email_html([product])
        message.attach(MIMEText(html_body, 'html'))

        logger.info(f"Attempting to send email to {recipient_email}")
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
            
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error: {str(e)}")
        raise ValueError("Invalid email credentials. Please check your Gmail app password.")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error: {str(e)}")
        raise ValueError(f"Failed to send email: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise ValueError(f"Unexpected error: {str(e)}")

def send_email_background(recipient_email, force_refresh=False):
    """Send email without blocking the HTTP response (Render 30s limit)."""
    def _run():
        try:
            send_email(recipient_email, force_refresh=force_refresh)
        except Exception as e:
            logger.error(f"Background email failed for {recipient_email}: {e}")

    threading.Thread(target=_run, daemon=False).start()

def _send_tracked_email(recipient_email, product_link, product):
    """Send email and schedule daily updates (runs in background on Render)."""
    try:
        send_email(recipient_email, product=product, product_link=product_link)
        with state_lock:
            if not scheduler.running:
                scheduler.add_job(
                    send_email, 'cron', hour=15, minute=23,
                    kwargs={
                        'recipient_email': recipient_email,
                        'force_refresh': True,
                        'product_link': product_link,
                    },
                )
                scheduler.start()
        logger.info(f"Email sent for {recipient_email}: {product['name']}")
    except Exception as e:
        logger.error(f"Background email failed for {recipient_email} ({product_link}): {e}")

def _track_product_background(recipient_email, product_link):
    """Legacy wrapper — scrape then email (used if product not pre-fetched)."""
    try:
        logger.info(f"Background track started for {product_link}")
        product = fetch_and_parse_product(product_link)
        with state_lock:
            product_state.link = product_link
            product_state.details = {
                **product,
                "price": product["current_price"],
                "_cached_link": product_link,
            }
        _send_tracked_email(recipient_email, product_link, product)
        logger.info(f"Background track complete for {recipient_email}: {product['name']}")
    except Exception as e:
        logger.error(f"Background track failed for {recipient_email} ({product_link}): {e}")

@app.route('/')
def home():
    """Homepage route"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/schedule-email', methods=['POST'])
@limiter.limit("5 per minute")
def schedule_email():
    """Schedule email with validation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        recipient_email = data.get('recipient_email')
        if not recipient_email or not validate_email(recipient_email):
            return jsonify({'error': 'Invalid email address'}), 400

        if not product_state.link:
            return jsonify({'error': 'Please set a product link first'}), 400

        get_product_details(force_refresh=True)
        send_email_background(recipient_email)

        if not scheduler.running:
            scheduler.add_job(
                send_email, 'cron', hour=15, minute=23,
                kwargs={'recipient_email': recipient_email, 'force_refresh': True},
            )
            scheduler.start()
            
        return jsonify({
            'message': 'Email sent successfully and scheduled for daily updates',
            'product': public_product_details(),
        }), 200
    except Exception as e:
        logger.error(f"Error scheduling email: {str(e)}")
        return jsonify({'error': str(e)}), 500

def public_product_details():
    """Product details for API responses (omit internal cache keys)."""
    return {k: v for k, v in product_state.details.items() if not k.startswith('_')}

@app.route('/track-product', methods=['POST'])
@limiter.limit("5 per minute")
def track_product():
    """Update link, scrape once, send email, and schedule — single request for Render."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        recipient_email = data.get('recipient_email')
        product_link = data.get('productLink')

        if not recipient_email or not validate_email(recipient_email):
            return jsonify({'error': 'Invalid email address'}), 400
        product_link = (product_link or "").strip()
        if not product_link or not validate_url(product_link):
            return jsonify({'error': 'Invalid product link'}), 400

        if os.getenv("RENDER"):
            product = fetch_and_parse_product(product_link)
            with state_lock:
                product_state.link = product_link
                product_state.details = {
                    **product,
                    "price": product["current_price"],
                    "_cached_link": product_link,
                }
            threading.Thread(
                target=_send_tracked_email,
                args=(recipient_email, product_link, product),
                daemon=False,
            ).start()
            return jsonify({
                'message': (
                    f"Tracking {product['name']}! Email arriving in 1–2 minutes."
                ),
                'async': True,
                'product': {
                    **product,
                    'price': product['current_price'],
                },
            }), 202

        with state_lock:
            product = fetch_and_parse_product(product_link)
            product_state.link = product_link
            product_state.details = {
                **product,
                "price": product["current_price"],
                "_cached_link": product_link,
            }

        try:
            send_email(recipient_email, product=product, product_link=product_link)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': f"Failed to send email: {str(e)}"}), 500

        if not scheduler.running:
            scheduler.add_job(
                send_email, 'cron', hour=15, minute=23,
                kwargs={
                    'recipient_email': recipient_email,
                    'force_refresh': True,
                    'product_link': product_link,
                },
            )
            scheduler.start()

        return jsonify({
            'message': 'Email sent successfully and scheduled for daily updates',
            'product': public_product_details(),
        }), 200
    except Exception as e:
        logger.error(f"Error tracking product: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/update-product-link', methods=['POST'])
@limiter.limit("5 per minute")
def update_product_link():
    """Update product link with validation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        new_link = data.get('productLink')
        if not new_link or not validate_url(new_link):
            return jsonify({'error': 'Invalid product link'}), 400

        product_state.link = new_link
        product_state.details.clear()

        # Test the link immediately (also caches details for the email step)
        get_product_details(force_refresh=True)
        
        return jsonify({'message': 'Product link updated successfully'}), 200
    except Exception as e:
        logger.error(f"Error updating product link: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Register scheduler shutdown
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    # Use environment variable for port
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)