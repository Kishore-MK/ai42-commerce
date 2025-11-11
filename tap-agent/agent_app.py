# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import uuid
import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import json
import time
import webbrowser
import requests
import threading
import datetime
import re
from urllib.parse import urlencode
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend
import base58

# Get Ed25519 keys from environment variables
def get_ed25519_keys_from_env():
    """Get Ed25519 keys from environment variables (Base58 format)"""
    private_key = os.getenv('ED25519_PRIVATE_KEY')
    public_key = os.getenv('ED25519_PUBLIC_KEY')
    
    if not private_key or not public_key:
        raise ValueError("ED25519_PRIVATE_KEY and ED25519_PUBLIC_KEY must be set in environment variables (Base58 format)")
    
    return private_key, public_key

# Global variable to store product extraction results across threads
_product_extraction_results = None

# Global variable to store order completion results across threads
_order_completion_results = None

def launch_with_playwright(url: str, headers: dict) -> bool:
    """Launch browser with headers using Playwright"""
    try:
        # Check if playwright is installed
        from playwright.sync_api import sync_playwright
        import threading
        import time
        
        def run_browser():
            """Run browser in a separate thread to keep it alive"""
            with sync_playwright() as p:
                # Launch browser with additional options to handle network issues
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--ignore-certificate-errors',
                        '--ignore-ssl-errors',
                        '--ignore-certificate-errors-spki-list'
                    ]
                )
                
                # Create context with signature headers applied to all requests
                context = browser.new_context(
                    extra_http_headers=headers,
                    ignore_https_errors=True,
                    viewport={'width': 1280, 'height': 720}
                )
                
                page = context.new_page()
                
                print(f"🔧 Browser context created with signature headers")
                print("📨 Signature Headers:")
                for key, value in headers.items():
                    if key == 'signature':
                        print(f"   {key}: {value[:20]}..." if len(value) > 20 else f"   {key}: {value}")
                    else:
                        print(f"   {key}: {value}")
                
                # Add request/response interceptors to handle failed API calls
                def handle_request(request):
                    # Log API calls
                    if 'api' in request.url.lower() or request.method == 'OPTIONS':
                        print(f"API Request: {request.method} {request.url}")
                
                def handle_response(response):
                    # Handle failed OPTIONS and API requests
                    if response.status >= 400:
                        print(f"Failed Request: {response.status} {response.request.method} {response.url}")
                        # Don't let failed API calls crash the browser
                        return
                
                # Set up request/response listeners
                page.on('request', handle_request)
                page.on('response', handle_response)
                
                # Handle console errors from the website
                def handle_console(msg):
                    if msg.type == 'error':
                        print(f"Console Error: {msg.text}")
                
                page.on('console', handle_console)
                
                # Navigate to the URL with error handling
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    print(f"✅ Successfully navigated to: {url}")
                    
                    # Wait a bit for the page to fully load
                    time.sleep(3)
                    
                    # Try to extract product information
                    product_info = {}
                    
                    # Common selectors for product title
                    title_selectors = [
                        'h1',
                        '[data-testid="product-title"]',
                        '.product-title',
                        '.product-name',
                        '[class*="title"]',
                        '[class*="product"]',
                        'title'
                    ]
                    
                    # Common selectors for product price
                    price_selectors = [
                        '[data-testid="price"]',
                        '.price',
                        '.product-price',
                        '[class*="price"]',
                        '[class*="cost"]',
                        '[class*="amount"]',
                        'span:has-text("$")',
                        'span:has-text("€")',
                        'span:has-text("£")'
                    ]
                    
                    # Extract product title
                    for selector in title_selectors:
                        try:
                            title_element = page.query_selector(selector)
                            if title_element:
                                title_text = title_element.inner_text().strip()
                                if title_text and len(title_text) > 3:  # Valid title
                                    product_info['title'] = title_text
                                    print(f"📦 Product Title: {title_text}")
                                    break
                        except:
                            continue
                    
                    # Extract product price
                    for selector in price_selectors:
                        try:
                            price_element = page.query_selector(selector)
                            if price_element:
                                price_text = price_element.inner_text().strip()
                                # Check if it looks like a price (contains currency symbols or numbers)
                                if price_text and any(char in price_text for char in ['$', '€', '£', '¥']) or any(char.isdigit() for char in price_text):
                                    product_info['price'] = price_text
                                    print(f"💰 Product Price: {price_text}")
                                    break
                        except:
                            continue
                    
                    # If we couldn't find specific elements, try generic extraction
                    if not product_info.get('title'):
                        try:
                            page_title = page.title()
                            if page_title:
                                product_info['title'] = page_title
                                print(f"📦 Page Title: {page_title}")
                        except:
                            pass
                    
                    if not product_info.get('price'):
                        try:
                            # Look for any text that contains currency symbols
                            all_text = page.content()
                            import re
                            price_pattern = r'[\$€£¥]\s*\d+(?:[.,]\d{2})?|\d+(?:[.,]\d{2})?\s*[\$€£¥]'
                            prices = re.findall(price_pattern, all_text)
                            if prices:
                                product_info['price'] = prices[0]
                                print(f"💰 Found Price: {prices[0]}")
                        except:
                            pass
                    
                    # Log the results and store globally
                    global _product_extraction_results
                    import datetime
                    
                    extraction_log = []
                    extraction_log.append("🛍️  PRODUCT EXTRACTION RESULTS")
                    extraction_log.append("="*50)
                    
                    if product_info.get('title'):
                        extraction_log.append(f"📦 Title: {product_info['title']}")
                        print(f"📦 Title: {product_info['title']}")
                    else:
                        extraction_log.append("❌ Title: Not found")
                        print("❌ Title: Not found")
                    
                    if product_info.get('price'):
                        extraction_log.append(f"💰 Price: {product_info['price']}")
                        print(f"💰 Price: {product_info['price']}")
                    else:
                        extraction_log.append("❌ Price: Not found")
                        print("❌ Price: Not found")
                    
                    extraction_log.append("="*50)
                    
                    # Store results globally
                    _product_extraction_results = {
                        'title': product_info.get('title'),
                        'price': product_info.get('price'),
                        'url': url,
                        'extraction_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'extraction_log': '\n'.join(extraction_log)
                    }
                    
                    print("\n" + '\n'.join(extraction_log))
                    
                    # Wait a moment before closing
                    print("⏳ Closing browser in 3 seconds...")
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"❌ Navigation or extraction error: {e}")
                
                # Close the browser automatically
                try:
                    print("🔒 Closing browser...")
                    browser.close()
                except Exception as e:
                    print(f"Error closing browser: {e}")
        
        # Start browser in a separate thread so it doesn't block Streamlit
        browser_thread = threading.Thread(target=run_browser, daemon=True)
        browser_thread.start()
        
        # Give it a moment to start
        time.sleep(2)
        
        st.success("✅ Browser launched with headers!")
        st.info("🤖 Browser will automatically extract product info and close.")
        st.warning("👀 Check the terminal/console for extraction results.")
        return True
            
    except ImportError:
        return False
    except Exception as e:
        st.error(f"Error launching browser: {str(e)}")
        return False

def complete_checkout_with_playwright(product_url: str, cart_url: str, checkout_url: str, headers: dict = None) -> tuple[bool, dict]:
    """Complete full checkout process: product page → add to cart → cart page → proceed to checkout → complete order"""
    try:
        # Check if playwright is installed
        from playwright.sync_api import sync_playwright
        import threading
        import time
        import re
        
        # Reset order completion results
        global _order_completion_results
        _order_completion_results = None
        
        # Ensure headers are provided
        if headers is None:
            headers = {}
        
        def run_full_checkout():
            """Run complete checkout process in a separate thread"""
            with sync_playwright() as p:
                # Launch browser with additional options
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--ignore-certificate-errors',
                        '--ignore-ssl-errors'
                    ]
                )
                
                # Create context with signature headers applied to all requests
                print(f"🔧 Setting up browser context with signature headers")
                context = browser.new_context(
                    extra_http_headers=headers,
                    ignore_https_errors=True,
                    viewport={'width': 1280, 'height': 720}
                )
                
                page = context.new_page()
                
                # Log headers being sent
                print("🛒 STARTING COMPLETE CHECKOUT PROCESS")
                print("="*50)
                print(f"📦 Product URL: {product_url}")
                print(f"🛒 Cart URL: {cart_url}")
                print(f"💳 Checkout URL: {checkout_url}")
                print("📨 Signature Headers:")
                for key, value in headers.items():
                    if key == 'signature':
                        print(f"   {key}: {value[:20]}..." if len(value) > 20 else f"   {key}: {value}")
                    else:
                        print(f"   {key}: {value}")
                print("="*50)
                
                try:
                    # STEP 1: Navigate to product page
                    print(f"🛍️ STEP 1: Navigating to product page: {product_url}")
                    page.goto(product_url, wait_until='domcontentloaded', timeout=30000)
                    print(f"✅ Successfully navigated to product page")
                    
                    # Wait for page to load
                    time.sleep(3)
                    
                    # STEP 2: Find and click "Add to Cart" button
                    print(f"🛒 STEP 2: Looking for 'Add to Cart' button...")
                    
                    # Common selectors for "Add to Cart" buttons
                    add_to_cart_selectors = [
                        'button:has-text("Add to Cart")',
                        'button:has-text("Add To Cart")',
                        'button:has-text("ADD TO CART")',
                        '[data-testid="add-to-cart"]',
                        '[id*="add-to-cart"]',
                        '[class*="add-to-cart"]',
                        '.add-cart',
                        '.addToCart',
                        '#addToCart',
                        'input[value*="Add to Cart"]',
                        'button[title*="Add to Cart"]',
                        '.btn-add-cart',
                        '.cart-add'
                    ]
                    
                    cart_added = False
                    for selector in add_to_cart_selectors:
                        try:
                            add_button = page.query_selector(selector)
                            if add_button and add_button.is_visible():
                                print(f"🎯 Found 'Add to Cart' button: {selector}")
                                add_button.click()
                                print(f"✅ Successfully clicked 'Add to Cart'")
                                cart_added = True
                                break
                        except Exception as e:
                            continue
                    
                    if not cart_added:
                        print("❌ Could not find 'Add to Cart' button")
                        # Try to find any button that might be add to cart
                        try:
                            all_buttons = page.query_selector_all('button')
                            for button in all_buttons[:10]:  # Check first 10 buttons
                                text = button.inner_text().lower()
                                if any(phrase in text for phrase in ['add', 'cart', 'buy', 'purchase']):
                                    print(f"🔄 Trying button with text: {text}")
                                    button.click()
                                    cart_added = True
                                    break
                        except:
                            pass
                    
                    if cart_added:
                        # Wait a moment for cart update
                        time.sleep(2)
                        print("✅ Product added to cart successfully")
                    else:
                        print("⚠️ Could not add product to cart, proceeding anyway")
                    
                    # STEP 3: Navigate to cart page
                    print(f"🛒 STEP 3: Navigating to cart page: {cart_url}")
                    page.goto(cart_url, wait_until='domcontentloaded', timeout=30000)
                    print(f"✅ Successfully navigated to cart page")
                    
                    # Wait for cart page to load
                    time.sleep(3)
                    
                    # STEP 4: Find and click "Proceed to Checkout" button
                    print(f"➡️ STEP 4: Looking for 'Proceed to Checkout' button...")
                    
                    # Common selectors for "Proceed to Checkout" buttons
                    proceed_checkout_selectors = [
                        'button:has-text("Proceed to Checkout")',
                        'button:has-text("Proceed To Checkout")',
                        'button:has-text("PROCEED TO CHECKOUT")',
                        'button:has-text("Checkout")',
                        'button:has-text("CHECKOUT")',
                        'a:has-text("Proceed to Checkout")',
                        'a:has-text("Checkout")',
                        '[data-testid="proceed-to-checkout"]',
                        '[data-testid="checkout"]',
                        '[id*="proceed-checkout"]',
                        '[id*="checkout"]',
                        '[class*="proceed-checkout"]',
                        '[class*="checkout-btn"]',
                        '.proceed-checkout',
                        '.checkout-proceed',
                        '#proceedToCheckout',
                        '#checkout',
                        '.btn-checkout',
                        'input[value*="Checkout"]',
                        'button[title*="Checkout"]'
                    ]
                    
                    checkout_proceeded = False
                    for selector in proceed_checkout_selectors:
                        try:
                            proceed_button = page.query_selector(selector)
                            if proceed_button and proceed_button.is_visible():
                                print(f"🎯 Found 'Proceed to Checkout' button: {selector}")
                                proceed_button.click()
                                print(f"✅ Successfully clicked 'Proceed to Checkout'")
                                checkout_proceeded = True
                                break
                        except Exception as e:
                            continue
                    
                    if not checkout_proceeded:
                        print("❌ Could not find 'Proceed to Checkout' button")
                        # Try to find any button that might be proceed to checkout
                        try:
                            all_buttons = page.query_selector_all('button, a')
                            for button in all_buttons[:15]:  # Check first 15 buttons/links
                                text = button.inner_text().lower()
                                if any(phrase in text for phrase in ['proceed', 'checkout', 'continue', 'next']):
                                    print(f"🔄 Trying button with text: {text}")
                                    button.click()
                                    checkout_proceeded = True
                                    break
                        except:
                            pass
                    
                    if checkout_proceeded:
                        # Wait for navigation to checkout page
                        time.sleep(3)
                        print("✅ Successfully proceeded to checkout")
                    else:
                        print("⚠️ Could not proceed to checkout, trying direct navigation")
                        # Fallback: navigate directly to checkout page
                        print(f"🛒 STEP 4b: Direct navigation to checkout: {checkout_url}")
                        page.goto(checkout_url, wait_until='domcontentloaded', timeout=30000)
                    
                    # STEP 5: We should now be on the checkout page
                    print(f"✅ Now on checkout page (current URL: {page.url})")
                    
                    # Wait for checkout page to load
                    time.sleep(3)
                    
                    # STEP 5: Fill out checkout form
                    print(f"📝 STEP 5: Filling out comprehensive checkout form...")
                    
                    # Comprehensive checkout form data
                    checkout_info = {
                        # Contact Information
                        'email': 'john.doe@example.com',
                        'phone': '+1-555-0123',
                        
                        # Shipping Address
                        'firstName': 'John',
                        'lastName': 'Doe',
                        'company': 'Example Company Inc.',
                        'address1': '123 Main Street',
                        'address2': 'Suite 456',
                        'city': 'New York',
                        'state': 'NY',
                        'zipCode': '10001',
                        'country': 'United States',
                        
                        # Payment Information
                        'cardNumber': '4111111111111111',
                        'expiryDate': '12/25',
                        'cvv': '123',
                        'nameOnCard': 'John Doe',
                        
                        # Additional Options
                        'specialInstructions': 'Ed25519 Base58 signature authentication sample order'
                    }
                    
                    # Comprehensive form field selectors
                    form_selectors = {
                        'email': ['#email', '[name="email"]', '[type="email"]'],
                        'phone': ['#phone', '[name="phone"]', '[type="tel"]'],
                        'firstName': ['#firstName', '[name="firstName"]'],
                        'lastName': ['#lastName', '[name="lastName"]'],
                        'company': ['#company', '[name="company"]'],
                        'address1': ['#address1', '[name="address1"]'],
                        'address2': ['#address2', '[name="address2"]'],
                        'city': ['#city', '[name="city"]'],
                        'state': ['#state', '[name="state"]'],
                        'zipCode': ['#zipCode', '#zip', '[name="zip"]'],
                        'country': ['#country', '[name="country"]'],
                        'cardNumber': ['#cardNumber', '[name="cardNumber"]'],
                        'expiryDate': ['#expiryDate', '[name="expiryDate"]'],
                        'cvv': ['#cvv', '[name="cvv"]'],
                        'nameOnCard': ['#nameOnCard', '[name="nameOnCard"]'],
                        'specialInstructions': ['#specialInstructions', '[name="specialInstructions"]']
                    }
                    
                    # Fill form fields
                    fields_filled = 0
                    for field, value in checkout_info.items():
                        for selector in form_selectors.get(field, []):
                            try:
                                element = page.query_selector(selector)
                                if element and element.is_visible() and element.is_enabled():
                                    element.fill(value)
                                    print(f"✅ Filled {field}: {value}")
                                    fields_filled += 1
                                    break
                            except:
                                continue
                    
                    print(f"📊 Successfully filled {fields_filled} out of {len(checkout_info)} fields")
                    
                    # Wait for form validation
                    time.sleep(3)
                    
                    # Find and click submit button
                    print(f"🔄 Looking for submit/complete order button...")
                    
                    submit_selectors = [
                        'button[type="submit"]',
                        'button:has-text("Complete Order")',
                        'button:has-text("Place Order")',
                        '[data-testid="submit-order"]',
                        '#submit'
                    ]
                    
                    submit_clicked = False
                    for selector in submit_selectors:
                        try:
                            button = page.query_selector(selector)
                            if button and button.is_visible() and button.is_enabled():
                                print(f"🎯 Found submit button: {selector}")
                                button.click()
                                print(f"✅ Successfully clicked submit button")
                                submit_clicked = True
                                break
                        except:
                            continue
                    
                    if submit_clicked:
                        print("✅ Order submission initiated")
                        
                        # Wait for success page
                        time.sleep(5)
                        
                        # Extract order ID
                        order_id = None
                        order_info = {}
                        
                        try:
                            # Look for order ID on success page
                            order_selectors = [
                                'span:has-text("Order #")',
                                '[data-testid*="order"]',
                                '.order-number'
                            ]
                            
                            for selector in order_selectors:
                                try:
                                    element = page.query_selector(selector)
                                    if element:
                                        text = element.inner_text().strip()
                                        order_match = re.search(r'([A-Z0-9-]+)', text)
                                        if order_match:
                                            order_id = order_match.group(1)
                                            order_info = {
                                                'order_id': order_id,
                                                'success_page_url': page.url,
                                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                                            }
                                            print(f"✅ Extracted order ID: {order_id}")
                                            break
                                except:
                                    continue
                        except Exception as e:
                            print(f"⚠️ Order ID extraction error: {e}")
                        
                        # Store results globally
                        global _order_completion_results
                        if order_id:
                            _order_completion_results = order_info
                        else:
                            _order_completion_results = {
                                'error': 'Order ID not found',
                                'final_url': page.url,
                                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                    else:
                        print("❌ Could not submit order")
                    
                    # Wait before closing
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"❌ Checkout error: {e}")
                
                # Close browser
                try:
                    browser.close()
                except:
                    pass
        
        # Start checkout in separate thread
        checkout_thread = threading.Thread(target=run_full_checkout, daemon=True)
        checkout_thread.start()
        checkout_thread.join(timeout=120)
        
        if _order_completion_results:
            if 'error' in _order_completion_results:
                return False, _order_completion_results
            else:
                return True, _order_completion_results
        else:
            return False, {'error': 'Checkout process failed', 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')}
            
    except Exception as e:
        return False, {'error': f'Checkout error: {str(e)}', 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')}

def create_ed25519_signature(authority: str, path: str, keyid: str, nonce: str, created: int, expires: int, tag: str) -> tuple[str, str]:
    """Create HTTP Message Signature using Ed25519 with Base58 encoding following RFC 9421"""
    try:
        print(f"🔐 Creating Ed25519 signature with Base58 encoding...")
        print(f"🌐 Authority: {authority}")
        print(f"📍 Path: {path}")
        
        # Create signature parameters string
        signature_params = f'("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="ed25519"; nonce="{nonce}"; tag="{tag}"'
        
        # Create the signature base string
        signature_base_lines = [
            f'"@authority": {authority}',
            f'"@path": {path}',
            f'"@signature-params": {signature_params}'
        ]
        signature_base = '\n'.join(signature_base_lines)
        
        print(f"🔐 Ed25519 Signature Base String:\n{signature_base}")
        
        # Load Ed25519 keys from environment variables (Base58 format)
        try:
            ed25519_private_base58, ed25519_public_base58 = get_ed25519_keys_from_env()
            print(f"🔑 Using Ed25519 keys from environment variables (Base58)")
        except ValueError as e:
            print(f"❌ Ed25519 keys not found in environment: {e}")
            st.error(f"Ed25519 keys not configured. Please add ED25519_PRIVATE_KEY and ED25519_PUBLIC_KEY to your .env file (Base58 format).")
            return "", ""
        
        # Decode Base58 private key to bytes
        private_bytes = base58.b58decode(ed25519_private_base58)
        print("Private bytes Length: ",len(private_bytes))
        # Ed25519 private keys should be 32 bytes
        if len(private_bytes) != 32:
            raise ValueError(f"Ed25519 private key must be 32 bytes, got {len(private_bytes)} bytes")
        
        # Load private key
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        
        print(f"🔑 Using Ed25519 Private Key (Base58): {ed25519_private_base58[:20]}...")
        print(f"🔑 Using Ed25519 Public Key (Base58): {ed25519_public_base58[:20]}...")
        
        # Sign with Ed25519
        signature = private_key.sign(signature_base.encode('utf-8'))
        
        # Encode signature to Base58
        signature_base58 = base58.b58encode(signature)
        print("Base Signature: ",signature_base58)
        # Format headers
        signature_input_header = f'sig2=("@authority" "@path"); created={created}; expires={expires}; keyId="{keyid}"; alg="ed25519"; nonce="{nonce}"; tag="{tag}"'
        signature_header = f'sig2=:{signature_base58}:'
        
        print(f"✅ Created Ed25519 signature (Base58)")
        print(f"📤 Signature-Input: {signature_input_header}")
        print(f"🔒 Signature (Base58): {signature_header}")
        
        return signature_input_header, signature_header
        
    except Exception as e:
        print(f"❌ Error creating Ed25519 signature: {str(e)}")
        st.error(f"Error creating Ed25519 signature: {str(e)}")
        return "", ""

def parse_url_components(url: str) -> tuple[str, str]:
    """Parse URL to extract authority and path components"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        # Authority is the host (and port if not default)
        authority = parsed.netloc
        
        # Path includes the path and query parameters
        path = parsed.path
        if parsed.query:
            path += f"?{parsed.query}"
        
        return authority, path
    except Exception as e:
        st.error(f"Error parsing URL: {str(e)}")
        return "", ""

def main():
    st.set_page_config(
        page_title="TAP Agent - Ed25519 Base58",
        page_icon="🔐",
        layout="wide"
    )
    
    st.title("🔐 TAP Agent - Ed25519 Base58")
    st.markdown("Generate Ed25519 Base58 signatures and launch sample merchant interactions")
    
    # Configuration Section
    st.header("⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        agent_name = st.text_input(
            "Agent Id",
            value="1",
            help="Id of this TAP agent"
        )
        
        reference_url = st.text_input(
            "Merchant URL",
            value="http://localhost:3001/product/1",
            help="URL of the sample merchant product details page"
        )
    
    # Initialize session state
    if 'ed25519_private_key' not in st.session_state:
        st.session_state.ed25519_private_key = ""
    if 'ed25519_public_key' not in st.session_state:
        st.session_state.ed25519_public_key = ""
    if 'product_details' not in st.session_state:
        st.session_state.product_details = None
    if 'input_data' not in st.session_state:
        # Generate default values only once
        import time
        nonce = str(uuid.uuid4())
        created = int(time.time())
        expires = created + 8 * 60  # 8 minutes from now
        keyId = "primary-ed25519"
        tag = "agent-browser-auth"
        
        # Parse URL into authority and path components
        authority, path = parse_url_components(reference_url)
        
        default_input = {
            "nonce": nonce,
            "created": created,
            "expires": expires,
            "keyId": keyId,
            "tag": tag,
            "authority": authority,
            "path": path
        }
        st.session_state.input_data = json.dumps(default_input, indent=2)
    
    # Load Ed25519 keys if not already loaded
    if not st.session_state.ed25519_private_key or not st.session_state.ed25519_public_key:
        try:
            ed25519_private_key, ed25519_public_key = get_ed25519_keys_from_env()
            st.session_state.ed25519_private_key = ed25519_private_key
            st.session_state.ed25519_public_key = ed25519_public_key
        except ValueError:
            st.warning("⚠️ Ed25519 keys not configured in environment variables")
    
    with col2:
        st.subheader("Input Data")
        st.caption("Input data that will be signed before sending to the sample merchant")
        st.code(st.session_state.input_data, language="json", line_numbers=False)
        
        # Reset button
        if st.button("🔄 Reset to Default JSON"):
            import time
            nonce = str(uuid.uuid4())
            created = int(time.time())
            expires = created + 8 * 60  # 8 minutes from now
            keyId = "primary-ed25519"
            tag = "agent-browser-auth"
            
            # Parse URL into authority and path components
            authority, path = parse_url_components(reference_url)

            default_input = {
                "nonce": nonce,
                "created": created,
                "expires": expires,
                "keyId": keyId,
                "tag": tag,
                "authority": authority,
                "path": path
            }
            st.session_state.input_data = json.dumps(default_input, indent=2)
            st.rerun()
    
    # Display algorithm info
    st.info("🚀 **Ed25519 with Base58 encoding** - Fast, secure, and modern signature algorithm using Base58 encoding for keys and signatures.")
    
    # Action Selection
    st.subheader("🎯 Action Selection")
    action_choice = st.radio(
        "Choose an action:",
        options=["Product Details", "Checkout"],
        index=0,
        help="Select whether to fetch product details or complete a checkout process.",
        horizontal=True
    )
    
    # Update input data based on action choice
    def update_input_data_with_action():
        """Update input data when merchant URL or action changes"""
        import time
        
        keyId = "primary-ed25519"
        
        # Determine tag based on action choice
        if action_choice == "Product Details":
            tag = "agent-browser-auth"
        else:  # Checkout
            tag = "agent-payer-auth"
        
        # Parse URL into authority and path components
        authority, path = parse_url_components(reference_url)
        
        # Parse current input data to preserve nonce, created, expires if they exist
        try:
            current_data = json.loads(st.session_state.input_data)
            nonce = current_data.get('nonce', str(uuid.uuid4()))
            created = current_data.get('created', int(time.time()))
            expires = current_data.get('expires', created + 8 * 60)
        except (json.JSONDecodeError, KeyError):
            nonce = str(uuid.uuid4())
            created = int(time.time())
            expires = created + 8 * 60
        
        # Create updated input data
        updated_input = {
            "nonce": nonce,
            "created": created,
            "expires": expires,
            "keyId": keyId,
            "tag": tag,
            "authority": authority,
            "path": path
        }
        
        return json.dumps(updated_input, indent=2)
    
    # Check if we need to update input data
    expected_input_data = update_input_data_with_action()
    if st.session_state.input_data != expected_input_data:
        try:
            current_parsed = json.loads(st.session_state.input_data)
            expected_parsed = json.loads(expected_input_data)
            
            # Update if keyId, authority, path, or tag have changed
            if (current_parsed.get('keyId') != expected_parsed.get('keyId') or 
                current_parsed.get('authority') != expected_parsed.get('authority') or
                current_parsed.get('path') != expected_parsed.get('path') or
                current_parsed.get('tag') != expected_parsed.get('tag')):
                st.session_state.input_data = expected_input_data
                st.rerun()
        except json.JSONDecodeError:
            st.session_state.input_data = expected_input_data
            st.rerun()
    
    # Launch Section
    st.header("🚀 Launch")
    
    # Check if keys are available
    if not st.session_state.ed25519_private_key:
        st.warning("Please configure Ed25519 keys in your .env file first (Base58 format)")
        launch_disabled = True
    else:
        launch_disabled = False
    
    # Dynamic button based on selection
    if action_choice == "Product Details":
        button_text = "📦 Fetch Product Details"
        button_help = "Create RFC 9421 Ed25519 Base58 signature and fetch product details"
        tag_value = "agent-browser-auth"
    else:  # Checkout
        button_text = "🛒 Complete Checkout"
        button_help = "Create RFC 9421 Ed25519 Base58 signature and complete checkout"
        tag_value = "agent-payer-auth"
    
    # Launch button
    if st.button(button_text, type="primary", disabled=launch_disabled, help=button_help):
        if st.session_state.ed25519_private_key:
            import time
            spinner_text = f"Creating RFC 9421 Ed25519 Base58 signature and {'fetching product details' if action_choice == 'Product Details' else 'completing checkout'}..."
            
            with st.spinner(spinner_text):
                # Parse current input data
                try:
                    parsed_json = json.loads(st.session_state.input_data)
                    nonce = parsed_json.get('nonce', str(uuid.uuid4()))
                    created = parsed_json.get('created', int(time.time()))
                    expires = parsed_json.get('expires', created + 8 * 60)
                    tag = parsed_json.get('tag', tag_value)
                except json.JSONDecodeError:
                    st.error("Invalid JSON format in input data")
                    nonce = str(uuid.uuid4())
                    created = int(time.time())
                    expires = created + 8 * 60
                    tag = tag_value
                
                # Parse URL components
                print(f"🔍 Attempting to parse URL: '{reference_url}'")
                authority, path = parse_url_components(reference_url)
                print(f"🔍 Parse result - Authority: '{authority}', Path: '{path}'")
                
                if authority and path:
                    # Create RFC 9421 Ed25519 Base58 signature
                    signature_input_header, signature_header = create_ed25519_signature(
                        authority=authority,
                        path=path,
                        keyid="primary-ed25519",
                        nonce=nonce,
                        created=created,
                        expires=expires,
                        tag=tag
                    )

                    print(f"Signature Algorithm: ed25519 (Base58)")
                    print(f"Signature input String:\n{signature_input_header}")
                    print(f"Signature String:\n{signature_header}")

                    if signature_input_header and signature_header:
                        # Create headers
                        headers = {
                            'Signature-Input': signature_input_header,
                            'Signature': signature_header
                        }
                        
                        if action_choice == "Product Details":
                            # Fetch product details
                            if launch_with_playwright(reference_url, headers):
                                st.success("✅ Product extraction started!")
                                st.info("🔄 Please wait for extraction to complete")
                                
                                # Wait for results
                                import time
                                max_wait_time = 10
                                check_interval = 1
                                waited = 0
                                
                                while waited < max_wait_time:
                                    time.sleep(check_interval)
                                    waited += check_interval
                                    
                                    global _product_extraction_results
                                    if _product_extraction_results:
                                        st.session_state.product_details = _product_extraction_results
                                        st.rerun()
                                        break
                                
                                if not _product_extraction_results:
                                    st.warning("⏳ Extraction taking longer than expected")
                            else:
                                st.error("❌ Failed to launch browser")
                        else:  # Checkout
                            # Complete checkout
                            product_url = reference_url
                            
                            from urllib.parse import urlparse
                            parsed = urlparse(reference_url)
                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                            cart_url = f"{base_url}/cart"
                            checkout_url = f"{base_url}/checkout"
                            
                            print(f"🛒 Attempting checkout with Ed25519 Base58 signature...")
                            print(f"📄 Product URL: {product_url}")
                            print(f"🛒 Cart URL: {cart_url}")
                            print(f"💳 Checkout URL: {checkout_url}")
                            
                            success, order_info = complete_checkout_with_playwright(product_url, cart_url, checkout_url, headers)
                            
                            if success and order_info:
                                st.success("🎉 Checkout completed successfully!")
                                
                                if order_info.get('order_id'):
                                    st.markdown("### 📋 Order Confirmation")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric("Order ID", order_info['order_id'])
                                        st.write(f"**Completed At:** {order_info.get('timestamp', 'Unknown')}")
                                    
                                    with col2:
                                        st.write(f"**Success Page:** [View]({order_info.get('success_page_url', '#')})")
                                
                                    with st.expander("🔍 Full Order Details"):
                                        st.json(order_info)
                                else:
                                    st.warning("Order placed but order ID not extracted")
                                    if order_info:
                                        with st.expander("Debug Information"):
                                            st.json(order_info)
                            else:
                                st.error("❌ Checkout failed")
                                if order_info and 'error' in order_info:
                                    st.error(f"Error: {order_info['error']}")
                    else:
                        st.error("❌ Failed to create signature")
                else:
                    st.error("❌ Failed to parse URL components")
    
    # Product Details Section
    if st.session_state.product_details:
        st.header("📦 Product Details")
        
        # Clear button
        if st.button("🗑️ Clear Product Details"):
            st.session_state.product_details = None
            st.rerun()
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.product_details.get('title'):
                st.subheader("📦 Product Title")
                st.write(st.session_state.product_details['title'])
            else:
                st.subheader("📦 Product Title")
                st.write("❌ Not found")
        
        with col2:
            if st.session_state.product_details.get('price'):
                st.subheader("💰 Product Price")
                st.write(st.session_state.product_details['price'])
            else:
                st.subheader("💰 Product Price")
                st.write("❌ Not found")
        
        # Extraction details
        with st.expander("🔍 Extraction Details"):
            extraction_time = st.session_state.product_details.get('extraction_time', 'Unknown')
            st.write(f"**Extraction Time:** {extraction_time}")
            st.write(f"**URL:** {st.session_state.product_details.get('url', 'Unknown')}")
            if st.session_state.product_details.get('extraction_log'):
                st.text_area("Extraction Log", value=st.session_state.product_details['extraction_log'], height=150)

if __name__ == "__main__":
    main()