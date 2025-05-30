def process_wine_data(wine_data):
    """
    Process wine data to extract specific columns.
    
    Args:
        wine_data (list): List of wine dictionaries from the JSON data
        
    Returns:
        list: List of dictionaries with selected columns
    """
    processed_data = []
    
    for item in wine_data:
        if item["data_type"] == "vintage":
            wine = item["data"]
            processed_wine = {
                "id": wine["id"],
                "title": wine["title"],
                "user_rating": wine["user_rating"],
                "user_rating_count": wine["user_rating_count"],
                "region": wine["region"],
                "country": wine["country"],
                "price": wine["shopping_prices"][0]["price_amount"] if wine["shopping_prices"] else None
            }
            processed_data.append(processed_wine)
    
    return processed_data
