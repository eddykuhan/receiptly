
import requests
import json
import urllib.parse

def fetch_products_by_category_graphql(category_id, page_size=48, current_page=1):
    """
    Fetch products from Mydin using GraphQL API.

    Args:
        category_id (int): Category ID to fetch products from
        page_size (int): Number of products per page
        current_page (int): Page number to fetch

    Returns:
        dict: API response containing products
    """
    url = "https://myapi.mydin.my/magento/products"

    # GraphQL query structure based on the working example
    query_body = [
        {
            "filter": {
                "category_id": {
                    "eq": str(category_id)
                }
            },
            "pageSize": page_size,
            "currentPage": current_page,
            "sort": {
                "position": "ASC"
            }
        },
        {
            "products": "products-custom-query",
            "metadata": {
                "fields": """
aggregations(filter: { category: { includeDirectChildrenOnly: true } }) {
    attribute_code
    count
    label
    options {
        count
        label
        value
    }
}
page_info {
    current_page
    page_size
    total_pages
}
total_count
sort_fields {
    default
    options {
        label
        value
    }
}
items {
    id
    sku
    mfgCode
    url_key
    name
    custom_productdescription
    custom_productname
    image {
        url
        label
    }
    thumbnail {
        url
        label
    }
    tier_prices {
        qty
        value
    }
    price_tiers {
        quantity
        discount {
            amount_off
            percent_off
        }
    }
    price_range {
        minimum_price {
            final_price {
                currency
                value
            }
            regular_price {
                currency
                value
            }
        }
        maximum_price {
            final_price {
                currency
                value
            }
            regular_price {
                currency
                value
            }
        }
    }
    ... on ConfigurableProduct {
        configurable_options {
            attribute_code
        }
        variants {
            attributes {
                code
                label
                uid
            }
            product {
                salable_quantity
                quantity
                sku
                price_range {
                    minimum_price {
                        final_price {
                            currency
                            value
                        }
                        regular_price {
                            currency
                            value
                        }
                    }
                    maximum_price {
                        final_price {
                            currency
                            value
                        }
                        regular_price {
                            currency
                            value
                        }
                    }
                }
                tier_prices {
                    qty
                    value
                }
            }
        }
    }
    ... on SimpleProduct {
        salable_quantity
        quantity
        sku
    }
    ... on BundleProduct {
        sku
        items {
            options {
                product {
                    sku
                    salable_quantity
                    quantity
                }
            }
        }
    }
}
"""
            }
        },
        {}
    ]

    # Encode the query body as URL parameter
    body_json = json.dumps(query_body)
    params = {
        'body': body_json
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Origin": "https://mydin.my",
        "Referer": "https://mydin.my/",
        "Content-Type": "application/json"
    }

    print(f"Fetching products for category: {category_id}")
    print(f"Page: {current_page}, Size: {page_size}")

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            return data
        else:
            print(f"Error response: {resp.text[:500]}")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None

def extract_items_from_graphql_response(response_data):
    """
    Extract individual product items from the GraphQL API response.

    Args:
        response_data (dict): Response from GraphQL API

    Returns:
        list: List of individual product items
    """
    items = []

    if not response_data:
        print("No response data")
        return items

    try:
        # The GraphQL response structure: data -> products -> items
        if 'data' in response_data and 'products' in response_data['data']:
            products_data = response_data['data']['products']

            if 'items' in products_data:
                product_items = products_data['items']
                print(f"Found {len(product_items)} product items")

                for item in product_items:
                    items.append(item)

                # Also print pagination info if available
                if 'page_info' in products_data:
                    page_info = products_data['page_info']
                    print(f"Page: {page_info.get('current_page')}/{page_info.get('total_pages')}")
                    print(f"Total products: {products_data.get('total_count', 'Unknown')}")

            else:
                print("No 'items' key in products data")
                print("Available keys:", list(products_data.keys()))
        else:
            print("Unexpected response structure")
            print("Response keys:", list(response_data.keys()))
            if 'data' in response_data:
                print("Data keys:", list(response_data['data'].keys()))

    except Exception as e:
        print(f"Error extracting items: {e}")

    return items

def test_graphql_api():
    """
    Test the GraphQL API with a sample category ID.
    """
    # Test with category ID 54 (from the example URL)
    category_id = 1222

    response = fetch_products_by_category_graphql(category_id, page_size=10, current_page=1)

    if response:
        items = extract_items_from_graphql_response(response)
        print(f"\nTotal items extracted: {len(items)}")

        if items:
            print("\nFirst item details:")
            print(json.dumps(items[0], indent=2)[:1000] + "...")

            # Show some basic info
            print(f"\nSample product names:")
            for i, item in enumerate(items[:5]):
                name = item.get('name', 'Unknown')
                sku = item.get('sku', 'Unknown')
                price_info = item.get('price_range', {}).get('minimum_price', {}).get('final_price', {})
                price = price_info.get('value', 'N/A')
                currency = price_info.get('currency', 'MYR')
                print(f"  {i+1}. {name} (SKU: {sku}) - {currency} {price}")
    else:
        print("Failed to fetch data")

def fetch_categories_graphql(category_ids=None):
    """
    Fetch categories from Mydin using GraphQL API.

    Args:
        category_ids (list): List of category IDs to fetch. If None, fetches main categories.

    Returns:
        dict: API response containing categories
    """
    url = "https://myapi.mydin.my/magento/categories"

    # Default category IDs from the example (main navigation categories)
    if category_ids is None:
        category_ids = [2101, 1222, 1513, 881, 2371, 1924, 2164, 1807, 1401, 765]

    # GraphQL query structure for categories
    query_body = [
        {
            "filters": {
                "ids": {
                    "in": category_ids
                }
            }
        },
        {
            "categories": "categories-custom-query",
            "metadata": {
                "fields": """
items {
    id
    image
    name
    category_bm_name
    url_key
    meta_title
    product_count
    children {
        id
        image
        name
        category_bm_name
        url_key
        meta_title
        product_count
    }
}
"""
            }
        },
        {}
    ]

    # Encode the query body as URL parameter
    body_json = json.dumps(query_body)
    params = {
        'body': body_json
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Origin": "https://mydin.my",
        "Referer": "https://mydin.my/",
        "Content-Type": "application/json"
    }

    print(f"Fetching categories: {category_ids}")

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            return data
        else:
            print(f"Error response: {resp.text[:500]}")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None

def extract_categories_from_response(response_data):
    """
    Extract category items from the GraphQL API response.

    Args:
        response_data (dict): Response from GraphQL API

    Returns:
        list: List of category items
    """
    categories = []

    if not response_data:
        print("No response data")
        return categories

    try:
        # The GraphQL response structure: data -> categories -> items
        if 'data' in response_data and 'categories' in response_data['data']:
            categories_data = response_data['data']['categories']

            if 'items' in categories_data:
                category_items = categories_data['items']
                print(f"Found {len(category_items)} category items")

                for item in category_items:
                    categories.append(item)

                    # Also add children categories
                    children = item.get('children', [])
                    if children:
                        print(f"Category '{item.get('name')}' has {len(children)} subcategories")
                        for child in children:
                            child['parent_id'] = item.get('id')
                            child['parent_name'] = item.get('name')
                            categories.append(child)

            else:
                print("No 'items' key in categories data")
                print("Available keys:", list(categories_data.keys()))
        else:
            print("Unexpected response structure")
            print("Response keys:", list(response_data.keys()))

    except Exception as e:
        print(f"Error extracting categories: {e}")

    return categories

def test_categories_api():
    """
    Test the Categories GraphQL API.
    """
    response = fetch_categories_graphql()

    if response:
        categories = extract_categories_from_response(response)
        print(f"\nTotal categories extracted: {len(categories)}")

        if categories:
            print("\nMain categories:")
            main_categories = [cat for cat in categories if 'parent_id' not in cat]
            for i, cat in enumerate(main_categories[:10]):  # Show first 10
                name = cat.get('name', 'Unknown')
                bm_name = cat.get('category_bm_name', '')
                product_count = cat.get('product_count', 0)
                children_count = len(cat.get('children', []))
                print(f"  {i+1}. {name} ({bm_name}) - {product_count} products, {children_count} subcategories")

            print("\nSample subcategories:")
            subcategories = [cat for cat in categories if 'parent_id' in cat]
            for i, cat in enumerate(subcategories[:5]):  # Show first 5
                name = cat.get('name', 'Unknown')
                parent = cat.get('parent_name', 'Unknown')
                product_count = cat.get('product_count', 0)
                print(f"  {i+1}. {name} (under {parent}) - {product_count} products")
    else:
        print("Failed to fetch categories")

if __name__ == "__main__":
    print("=== Testing Categories API ===")
    test_categories_api()

    print("\n=== Testing Products API ===")
    test_graphql_api()
