import pandas as pd

from parsing import is_true, parse_money, parse_percentage

companies = pd.read_csv("/Users/johndoe/data/companies.csv")
reviews = pd.read_csv("/Users/johndoe/data/reviews.csv")
shuttles = pd.read_excel("/tmp/shared/shuttles.xlsx")

companies["iata_approved"] = is_true(companies["iata_approved"])
companies["company_rating"] = parse_percentage(companies["company_rating"])

shuttles[["d_check_complete", "moon_clearance_complete"]] = is_true(
    shuttles[["d_check_complete", "moon_clearance_complete"]]
)
shuttles["price"] = parse_money(shuttles["price"])

shuttles["adjusted_price"] = 1.597463007 * shuttles["price"]  # uh?
