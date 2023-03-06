def is_true(x):
    return x == "t"


def parse_percentage(x):
    x = x.str.replace("%", "")
    return x.astype(float) / 100


def parse_money(x):
    x = x.str.replace("$", "", regex=False).str.replace(",", "", regex=False)
    return x.astype(float)
