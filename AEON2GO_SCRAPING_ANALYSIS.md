# AEON2GO SCRAPING ANALYSIS

## Executive Summary

**Aeon2Go** (https://myaeon2go.com/) employs aggressive anti-bot protection and does **NOT expose public APIs** for product data scraping. The website is heavily protected with DataDome CAPTCHA and bot detection systems that block automated access attempts.

## Technical Architecture

### Platform
- **Framework**: Unknown (heavily protected)
- **Anti-Bot Protection**: DataDome CAPTCHA system
- **Access Control**: Geographic blocking and bot detection
- **URL Structure**: `https://myaeon2go.com/`

### Data Access Patterns

#### ❌ No Public APIs Found
- **Main Site Blocked**: 403 Forbidden with CAPTCHA challenge
- **API Endpoints**: All common patterns return 404/403 errors
- **No JSON Feeds**: No structured data exports discovered
- **No Documentation**: No public API documentation found

#### ✅ Protection Mechanisms Identified

**1. DataDome CAPTCHA**
- Advanced bot detection system
- Blocks automated requests based on:
  - IP address reputation
  - Request patterns
  - JavaScript execution
  - Browser fingerprinting

**2. Geographic Blocking**
- May restrict access based on location
- Cloud-based IP addresses flagged as suspicious

**3. Rate Limiting**
- Aggressive request throttling
- Session-based access control

#### 🔍 Discovered API Endpoint (Protected)

**Product Listing API Found:**
```
URL: https://myaeon2go.com/api/product/ples
Parameters:
- getSmartBrand=true    # Include smart brand data
- isCarousel=true       # Carousel display format
- inStockOnly=true      # Only in-stock products
- limit=200            # Maximum results
- excludeVariants=     # Variant exclusion filter
- serviceType=         # Service type filter
- skipProduct=false    # Include product data
- gid=1066            # Group/Category ID (1066 = specific category)
- pleType=softCategory # Product listing entity type
```

**Status:** Protected by DataDome CAPTCHA - returns 403 Forbidden

### API Endpoint Discovery

**Discovered Endpoint**: `https://myaeon2go.com/api/product/ples`

**Parameters**:
- `getSmartBrand=true` - Include smart brand information
- `isCarousel=true` - Carousel display format
- `inStockOnly=true` - Filter to in-stock items only
- `limit=200` - Maximum 200 products per request
- `excludeVariants=` - Empty (no variants excluded)
- `serviceType=` - Empty (no service type filter)
- `skipProduct=false` - Include products
- `gid=1066` - Category/group ID (likely "Baby & Kids" or similar)
- `pleType=softCategory` - Product listing entity type

**Response Structure**: Unknown (blocked by CAPTCHA)

**Access Status**: 403 Forbidden - Protected by DataDome CAPTCHA

## Investigation Results

### Network Analysis
```
Main Page: https://myaeon2go.com/
Status: 403 Forbidden
Response: DataDome CAPTCHA challenge
```

### API Endpoint Testing
All tested endpoints returned errors:
- `/api/` → 403 Forbidden
- `/graphql` → 404 Not Found
- `/rest/` → 404 Not Found
- `/mobile/` → 404 Not Found
- `/v1/`, `/v2/`, `/v3/` → 404 Not Found

### API Testing Results

**Test File**: `test_aeon2go_api.py` created and executed

**Test Results**:
- **Total Requests**: 6 (1 main test + 5 category variations)
- **Successful Requests**: 0
- **Blocked by CAPTCHA**: 6 (100%)
- **Error Rate**: 0%

**Conclusion**: All API endpoints are completely inaccessible due to DataDome protection. The discovered `/api/product/ples` endpoint exists but requires CAPTCHA verification for all requests.

### External Research
- **No GitHub Repositories**: No public code or API documentation
- **No Stack Overflow**: No developer discussions or API usage
- **No Technical Blogs**: No integration guides or API documentation
- **App Store Info**: Limited app descriptions, no API details

## Scraping Feasibility Assessment

### ❌ Not Recommended for API-Based Scraping

**Technical Barriers:**
1. **CAPTCHA Protection**: DataDome blocks all automated access
2. **No API Endpoints**: No structured data access methods
3. **Geographic Restrictions**: May require specific IP ranges
4. **Session Management**: Complex authentication requirements

**Legal/Ethical Considerations:**
1. **Terms of Service**: Likely prohibit automated scraping
2. **Anti-Bot Measures**: Deliberately designed to prevent scraping
3. **Fair Use**: High-volume requests would be detected and blocked

### ✅ Alternative Approaches (If Scraping Required)

**1. Residential Proxies**
```python
# Using residential proxies to bypass geo-blocking
import requests
from residential_proxy import ResidentialProxy

proxy = ResidentialProxy()
response = requests.get("https://myaeon2go.com/", proxies=proxy.get_proxy())
```

**2. Browser Automation with CAPTCHA Solving**
```python
# Using Selenium with CAPTCHA solving services
from selenium import webdriver
from captcha_solver import CaptchaSolver

driver = webdriver.Chrome()
solver = CaptchaSolver()
# Complex setup required for DataDome bypass
```

**3. Mobile App Reverse Engineering**
```python
# Decompiling Android/iOS app for API endpoints
# Requires APK/IPA analysis tools
# May violate app store terms
```

## Comparison with Other Retailers

| Retailer | API Type | Scraping Difficulty | Protection Level |
|----------|----------|-------------------|------------------|
| **Lotus's** | REST API | ⭐⭐⭐⭐⭐ (Very Easy) | ⭐⭐ (Basic) |
| **Mydin** | GraphQL API | ⭐⭐⭐⭐⭐ (Very Easy) | ⭐⭐ (Basic) |
| **Sunshine Online** | No API | ⭐⭐ (Very Hard) | ⭐⭐⭐ (Moderate) |
| **Aeon2Go** | No API | ⭐ (Impossible) | ⭐⭐⭐⭐⭐ (Extreme) |

## Recommendation

**Completely avoid Aeon2Go** for automated price comparison due to:
- Enterprise-grade anti-bot protection (DataDome)
- No public API access
- High technical complexity
- Legal risks of bypassing protection

**Focus resources on retailers with proper APIs** (Lotus's, Mydin) for reliable, scalable price comparison data.

## Investigation Timeline

1. **Initial Access**: Main page blocked with 403/CAPTCHA
2. **Network Analysis**: 6 requests captured, all CAPTCHA-related
3. **API Testing**: Common endpoint patterns tested - all failed
4. **Specific API Discovery**: User provided `/api/product/ples` endpoint
5. **API Testing**: Endpoint confirmed but protected by CAPTCHA
6. **External Research**: GitHub, Stack Overflow, Medium searched - no results
7. **Alternative Domains**: Aeon Malaysia sites tested - also protected

## Conclusion

Aeon2Go represents the **most protected e-commerce platform** encountered, with enterprise-level bot detection that makes automated access practically impossible. **However, a legitimate product API endpoint was discovered** (`/api/product/ples`) that suggests Aeon2Go does have structured data access internally, but it's locked behind DataDome protection.

Unlike Sunshine Online's traditional OpenCart setup, Aeon2Go uses modern anti-bot technology that would require significant resources to bypass. The API endpoint structure suggests they have a well-designed backend system, but public access is completely blocked.

For a production price comparison system, Aeon2Go should be excluded from the scope due to technical infeasibility and the high risk of detection/blocking.