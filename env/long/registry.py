"""Long-horizon domains by name, so the runner and the gold builder treat
them uniformly."""

from env.long import pay, shop

DOMAINS = {
    "shop": {"module": shop, "tools": shop.ShopTools},
    "pay": {"module": pay, "tools": pay.PayTools},
}
