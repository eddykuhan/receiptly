/**
 * Utility for categorizing receipt items based on their names.
 * Uses pattern matching to classify items when backend category is not available.
 */
export class ItemCategorizationUtil {
    /**
     * Categorize an item based on its name using pattern matching.
     * Prioritizes backend category if available.
     * 
     * @param item - Receipt item with name and optional category
     * @returns Category name
     */
    static categorizeItem(item: { name: string; category?: string }): string {
        // Use backend category if available
        if (item.category) {
            return item.category;
        }

        // Otherwise, categorize based on item name (case-insensitive)
        const name = (item.name || '').toLowerCase();

        // Beverages
        if (name.match(/\b(water|drink|juice|tea|coffee|coke|pepsi|sprite|milk|latte|cappuccino|smoothie|soda|mineral)\b/)) {
            return 'Beverages';
        }

        // Snacks & Confectionery
        if (name.match(/\b(chips|crisp|biscuit|cookie|wafer|chocolate|candy|sweet|snack|popcorn|nuts|crackers)\b/)) {
            return 'Snacks';
        }

        // Personal Care
        if (name.match(/\b(shampoo|soap|toothpaste|toothbrush|tissue|napkin|wipes|cream|lotion|sanitizer|deodorant|perfume|razor|pad)\b/)) {
            return 'Personal Care';
        }

        // Household & Cleaning
        if (name.match(/\b(detergent|cleaner|soap|dishwash|bleach|softener|sponge|mop|bag|foil|wrap|plastic)\b/)) {
            return 'Household';
        }

        // Fresh Produce
        if (name.match(/\b(apple|banana|orange|grape|mango|vegetable|onion|garlic|potato|tomato|carrot|cabbage|lettuce)\b/)) {
            return 'Fresh Produce';
        }

        // Meat & Seafood
        if (name.match(/\b(chicken|beef|pork|fish|prawn|lamb|meat|salmon|tuna)\b/)) {
            return 'Meat & Seafood';
        }

        // Bakery & Bread
        if (name.match(/\b(bread|bun|roll|cake|pastry|donut|croissant|bagel)\b/)) {
            return 'Bakery';
        }

        // Dairy & Eggs
        if (name.match(/\b(milk|cheese|butter|yogurt|egg|cream|dairy)\b/)) {
            return 'Dairy & Eggs';
        }

        // Frozen Foods
        if (name.match(/\b(frozen|ice cream|nugget|fries)\b/)) {
            return 'Frozen Foods';
        }

        // Condiments & Sauces
        if (name.match(/\b(sauce|ketchup|mayo|mustard|vinegar|oil|soy|chili|paste)\b/)) {
            return 'Condiments';
        }

        // Rice, Noodles & Pasta
        if (name.match(/\b(rice|noodle|pasta|vermicelli|mee|maggi|instant)\b/)) {
            return 'Rice & Noodles';
        }

        // Default category
        return 'Groceries';
    }

    /**
     * Get all available category names
     */
    static getAllCategories(): string[] {
        return [
            'Beverages',
            'Snacks',
            'Personal Care',
            'Household',
            'Fresh Produce',
            'Meat & Seafood',
            'Bakery',
            'Dairy & Eggs',
            'Frozen Foods',
            'Condiments',
            'Rice & Noodles',
            'Groceries'
        ];
    }
}
