# Data sources by market

APIs and MCP servers a buyer's agent can read for prices, offers,
reviews, price history and deals, worldwide. Pick the rows for the
profile's markets; a market with no row uses the generic steps in
SKILL.md. Checked 2026-10-19 with one test search each; a row checked
more than six months ago is tried first, and dropped from the answer
when it fails.

## Rules for every row

- **Read-only.** Use search and read tools only. Cart, checkout,
  payment, watch and posting tools are out of scope, even when the same
  server offers them.
- **Keys are the user's.** A "key" or "OAuth" row needs the user to sign
  up and set the key, or connect the server, themselves. Never sign up
  for them. Without the key, skip the row and say so.
- **Links.** Affiliate links are labelled. Quote the plain product URL
  (the row says how to get it) unless the row says its terms require
  the link unchanged.
- **Terms.** Several sources ban training on their data, bulk copying,
  or caching beyond the conversation. Read for this purchase only, keep
  no copies, and credit a source that asks for it.
- **Hosted MCP** rows: connect the URL as an MCP server in the agent, or
  send JSON-RPC over HTTP (`initialize`, `tools/list`, then
  `tools/call`) when it is keyless.
- **"Origin unverified"** means the source doesn't say how it collects
  prices. Use it beside a second source, never alone.
- **Never a source that gets around bot checks**: TLS fingerprint
  spoofing, stealth or headless browsers, captcha or cookie-challenge
  solving, rotating or residential proxies. The excluded list names the
  ones found.

## Any market

| Source | Gives | Access | Notes |
|---|---|---|---|
| OneFindMe (`https://onefindme.com/mcp`, REST `/api/search`) | AliExpress and eBay listings that ship to a country, in its currency with shipping; 21 query languages | Hosted MCP, keyless | Affiliate links: follow the redirect to `aliexpress.com/item/<id>.html`. AliExpress affiliate program and eBay Browse API |
| eBay Browse API | Listings, price, shipping, seller feedback; US, UK, DE, FR, IT, ES, AU, CA and more | Free key, about 5,000 calls a day | Shown listings must be at most 6 hours old; terms ban ML training and price modelling |
| AliExpress affiliate API | Product search by ship-to country, currency, language | Free affiliate app key | Plain URL `aliexpress.com/item/<id>.html` |
| CashbackPro (`https://cashbackpro.org/api/mcp`) | AliExpress promo codes and price after cashback | Hosted MCP, keyless | Affiliate; plain URL from `product_id` |
| Coreplex (`coreplex.ai`, coreplexMcp) | Live catalogs of Shopify stores, official-store flag, return policies | Hosted MCP, keyless | Any currency; useful where a country has no other source |
| WEM (`https://wem3.ai/api/mcp`) | Offers from Awin feeds and retailers, `verify_offer` with evidence | Hosted MCP, keyless | Affiliate (disclosed); 6 categories |
| GotCashback (`https://mcp.gotcashback.com`) | Cashback rates across 112 portals, gift-card stacking | Hosted MCP, keyless public tools | 42 countries |
| ProofPrice (`https://proofprice.com/api/mcp`) | Benchmark prices from official statistics (ONS and others) | Hosted MCP, keyless | 30+ countries, many in Africa. Typical prices, not offers |
| Open Prices (`prices.openfoodfacts.org/api/v1/prices`) | Crowdsourced shelf and receipt prices with place and date | Keyless | Sparse outside France; ODbL, credit it |
| Open Food Facts (`/api/v2/product/<barcode>`) | Food and cosmetic composition, no prices | Keyless; custom User-Agent | Prefer barcode reads; search is rate-limited |
| Whale Coupons (`https://whalecoupons.co/mcp`) | Codes issued by independent and Shopify stores | Hosted MCP, keyless | Affiliate shop links |
| Vistoya (`https://api.vistoya.com/mcp`) | Fashion across brands, stock per size | Hosted MCP, keyless | Terms require its `vistoya.com/p/<id>` link unchanged |
| Carat Hunter (`https://carathunter.com/mcp`) | Diamond prices tracked across retailers | Hosted MCP, keyless | No affiliate links |
| Foxfind (`https://foxfind.ing/mcp`), GameDeal.eu | PC game prices | Hosted MCP, keyless | |
| Etsy Open API v3 | Handmade and vintage listings, shop and listing reviews | Free key after app review | Etsy's own MCP only serves API docs |
| Keepa API | Amazon price and rank history, about 11 Amazon sites | Paid key (from about EUR 49 a month) | Best Amazon price history |
| ZooData (APIClaw) | Amazon price, rank and rating history; 12 Amazon sites | Paid key, 1,000 free credits | Origin unverified |
| Amazon Creators API | Amazon offers and deals, about 22 marketplaces | Associates account with 10 sales in 30 days | Most buyers can't qualify; PA-API 5 is shut down |
| BuyWhere (`https://api.buywhere.ai/mcp`) | Merchant price snapshots, deepest in US and Singapore | Hosted MCP, keyless, 1,000 calls a day | Low trust: its top hit was 4 months old and implausible |

## North America

| Source | Gives | Access | Notes |
|---|---|---|---|
| ShopSavvy (`https://api.shopsavvy.com/mcp`) | Offers at many US retailers, price history since 2011 | Hosted MCP keyless (per-IP limit); key from USD 49 a month | Reads retailer markup, merchant feeds and data partners |
| Channel3 (`https://mcp.trychannel3.com`) | Multi-retailer offers, 30-day history, 100M products | Hosted MCP, keyless | Commission model |
| LMK.today (`https://lmk.today/api/ucp/mcp`) | Price history and deal scores from merchant feeds | Hosted MCP, keyless | Links go to LMK pages |
| Fazy (`https://fazy.com/mcp`) | Deals with Fazy's own dated price record, promos | Hosted MCP, keyless | Terms require its `fazy.com/go` links unchanged; no training |
| Best Buy API | Products, store stock, open-box offers, review stats | Free key | Cache only temporarily |
| Walmart Affiliate API | Search, items, reviews, nearby stores | Free key plus affiliate ID | Plain URL `walmart.com/ip/<id>` |
| Kroger API | Store-level regular and promo prices, stock | Free key | Rootz Food (`https://food.rootz.global/mcp`) serves the same, keyless |
| retailerapi | UPC or ASIN price, 90-day history, 7 big US retailers | Free key, 1,000 lookups a month | No keyword search; part origin unverified |
| iDevice (`https://idevice.com/api/mcp`) | Phones and wearables: buy, wait or skip; history; returns, recalls | Hosted MCP, keyless, 500 calls a day | Cite iDevice |
| Kit's Deals (`https://mcp.kitsdeals.com`), MoneyDeals (`https://go.moneydeals.com/mcp`), Dealerific (`https://dealerific.com/api/mcp`) | Reviewed deals and coupons; MoneyDeals adds 90-day history | Hosted MCP, keyless | Affiliate |
| Clippy / McClipFace (endpoint in `getclippy.co/mcp/docs`), Tenmomo (`https://tenmomo.com/mcp`), Coupondroid (`https://coupondroid.com/mcp/public`) | Coupons and cashback rates | Hosted MCP, keyless | Affiliate. Tenmomo's `activate` uses the user's own key: only on their ask |
| Shop Nobi (`https://api.nobi.ai/v1/shop/mcp`) | Independent brands | Hosted MCP, keyless | Paid links labelled |
| deal.ly | Used and collectible prices from eBay listings | Hosted MCP, keyless | Origin unverified |
| Instacart (`https://fig-mcp.instacart.com/mcp`) | Grocery search across retailers | OAuth, the user's account | `search_products` only; `cart` changes their cart |
| BuySignal (`https://buysignal.deals/mcp`) | Canadian deals (40 retailers), daily price record | Hosted MCP, keyless | Also UK |
| GroceryPulse (`https://grocerypulse.ca/api/shopper/mcp`) | Canadian grocery list comparison, 16 cities | Hosted MCP, keyless; send `MCP-Protocol-Version` | Items need its canonical ids |

## United Kingdom

| Source | Gives | Access | Notes |
|---|---|---|---|
| BuySignal (`https://buysignal.deals/mcp`) | Deals at 20+ retailers, "lowest in 30 days" | Hosted MCP, keyless | No affiliate links |
| TheBetterBuy (`https://mcp.thebetterbuy.co.uk`) | Multi-retailer offers by GTIN | Hosted MCP, keyless | Affiliate; origin unverified |
| Ponito (`https://ponito.com/mcp`) | Offers by GTIN, one year of daily history | Hosted MCP, keyless | Also CH, DE, FR, AT, ES, NL |
| Vouchernaut (`https://vouchernaut.com/mcp`) | Codes, 30-day price drops, phone and SIM deals | Hosted MCP, keyless | Gifts and homeware lean |
| BudgetFitter (`https://budgetfitter.uk/mcp`) | Discount codes, buying guides | Hosted MCP, keyless | Affiliate |

## Europe

| Market | Source | Access | Notes |
|---|---|---|---|
| Many | eBay Browse API; Kelkoo Shopping API (approved publisher); Awin feeds (approved publisher) | Keys | Kelkoo: live multi-merchant offers, about 20 countries. Awin: feeds of national stores with no API |
| CH, DE, FR, GB, AT, ES, NL | Ponito (`https://ponito.com/mcp`) | Keyless | See United Kingdom |
| DK, SE, DE, NO | Plendio (`https://plendio.com/mcp`) | Keyless | Own crawler with a published bot policy |
| GR | BestPrice.gr (`https://mcp.bestprice.gr/mcp`) | Keyless | Store offers, price history |
| GR | posokanei-mcp (local package) | None | Government supermarket prices through undocumented endpoints |
| LT, LV, EE | PriceBee (`https://pricebee.lt/mcp/pricebee`) | Keyless | Also mobile plans |
| DE | OfferHopper (`https://mcp.offerhopper.ai/mcp`) | Keyless | Grocery and drugstore flyers; origin unverified; sends queries to Gemini |
| DE, ES, FR, IT | Coupondroid (`https://coupondroid.<tld>/mcp/public`) | Keyless | Coupons |
| NL, BE | bol.com Marketing Catalog API | bol affiliate account | |
| PL, CZ, SK, HU | Allegro REST API | App verified by Allegro | Gated |
| CH, FI, RU | swissgroceries-mcp, suomi-shopping-mcp, rf-marketplaces-mcp (local packages) | None | Read store APIs or pages plainly; check results against the site |

## Middle East

| Market | Source | Access | Notes |
|---|---|---|---|
| Iran | the `iran-stores` skill | Install (SKILL.md, Reader skills first) | 17 stores: offers, reviews, price history, seller trust, installments |
| UAE | YallaDeals (`https://yalladeals.io/mcp`) | Keyless | Amazon.ae and noon, 90-day history; affiliate; noon origin unverified |
| UAE | Brainy UAE Prices (`https://prices.brainy.ae/mcp/v2`) | Keyless | Dubai groceries, dated values |
| Israel | SuperMCP (`https://supermcp.co.il/mcp`) | Keyless | Legally mandated chain price feeds, 11 chains, daily |
| Israel | Wizbi (`https://wizbi.store/mcp`) | Free key | Supermarkets |
| Israel | deali.co.il | Keyless | Hebrew AliExpress deals |
| Turkey | market-fiyati-mcp (local package) | None | TÜBİTAK Market Fiyatı supermarket prices |

Trendyol, Hepsiburada and noon have no buyer API: use the generic steps.

## Asia

| Market | Source | Access | Notes |
|---|---|---|---|
| TW, HK, JP, SG, MY, TH, ID, VN, PH, IN, US | BigGo-MCP-Server (local package) | Keyless search and history | BigGo's own comparison API; last release 2025-04 |
| Japan | Rakuten Web Service (`rakuten-mcp` wraps it) | Free app ID | Plain `itemUrl` given |
| Japan | Yahoo! Shopping itemSearch v3 | Free client ID | Price, shipping, points, reviews |
| Korea | Supershopping (`https://supershopping-mcp.atdev.ai/mcp`) | Keyless | New and used, Danawa data; origin unverified |
| Korea | Coupang Partners Open API | Partners account | Tight limits. Naver's shopping search API shut down 2026-07-31 |
| Korea | Paybooc (Claude directory) | Keyless | Card cashback rates per store |
| India | Flipkart Affiliate API | Affiliate token | |
| India | DesiDime (`https://mcp.desidime.com/mcp`) | OAuth | Community deals; read tools only |
| India | CashJosh (`https://cashjosh.com/mcp`) | Keyless | Cashback, coupons |
| Malaysia | ManaMurah (`https://mcp.manamurah.com/mcp`) | Keyless | Government PriceCatcher data, cheapest shops |
| Southeast Asia | Shopee Affiliate Open API | Affiliate app | BR, ID, MY, PH, SG, TH, VN |
| China | JD Union, Taobao/Tmall (Alimama) | Promoter accounts, Chinese identity in practice | No vetted MCP: every wrapper found failed the bot-check rule |
| Uzbekistan | DiscountHub (`https://mcp.discounthub.uz/mcp`) | Keyless | Small catalog |

## Oceania

| Market | Source | Access | Notes |
|---|---|---|---|
| Australia | Pinch (`https://pinch-app.com/api/mcp`) | Keyless, 1,000 calls a day | Woolworths, Coles, Aldi specials and history; credit Pinch; origin unverified |
| Australia, NZ | Commission Factory feeds | Affiliate key | Retailers with no API |

## Latin America

| Market | Source | Access | Notes |
|---|---|---|---|
| Brazil | Pechincha.ai (`https://pechincha.ai/mcp`) | Keyless | Deals, coupons, 30-day history |
| Brazil | Mestre Pratico (`https://mestrepratico.com.br/mcp/v1`) | Auth unclear | Fuel, groceries and medicine price caps from government data |
| MX, CL | Coupondroid (`https://coupondroid.mx/mcp/public`, `.cl`) | Keyless | Coupons |
| Peru | plaza-vea-mcp (local package) | None | Store's public VTEX API |
| 18 markets | Mercado Libre API (`mercadolibre-mcp` wraps it) | The user's app credentials | Keyless search returns 403 since 2026 |

## Africa

No store source passed. Use ProofPrice for typical prices, Coreplex
for Shopify stores, OneFindMe and AliExpress for cross-border, and the
generic steps for Jumia and Takealot.

## Excluded

| Source | Why |
|---|---|
| idealo MCP (`mcp.idealo.com`) | Trial terms §1.2: consumers and private use excluded; §5.2 bans end-customer use and price observation. Paid Partner contract only |
| Shop by Shopify (`mcp.shop.com`) | Has checkout and spend tools. Its `search_catalog` and `lookup_catalog` are fine only in a client that allows just those |
| Forage | Has a purchase tool |
| Fewsats amazon-mcp | Buys on the user's behalf; archived |
| awesome-iran-mcp servers | Chrome TLS impersonation, cookie-challenge solving, proxy rotation, headless browser |
| geizhals-mcp, mcp-taiwan-price-compare, alza-mcp-community | TLS impersonation (curl_cffi), browsers, residential proxies |
| Secondhand MCP, marketplace-search-mcp | Stealth browser, residential proxies |
| Coupang MCP (uju777) | Proxies around Danawa's block; also down |
| Logimu, avito-shopping-mcp, xianyu-shopping-assistant, dealwatch, jbeshir amazon-products and supermarkets-uk | Drive a browser through the store, some solving its WAF challenge |
| Pangolinfo Amazon MCP, Menlo Labs | Hosted scraping vendors that sell getting past blocks |
| ShopOracle (tooloracle) | Origin undisclosed, needs a wallet key |
| Etsy dev MCP | API docs only, no listings |
| Google Shopping, Target, Temu, Otto, Zalando, Kaufland, Cdiscount, Fnac, Geizhals, PriceRunner, PriceSpy, noon, Trendyol, Hepsiburada | No buyer API (seller APIs only, or none) |
| Naver Shopping Search API | Shut down 2026-07-31 |
