# CompanyEnrich Python SDK

[![PyPI](https://img.shields.io/pypi/v/companyenrich)](https://pypi.org/project/companyenrich/)

The official Python client for the [CompanyEnrich API](https://companyenrich.com): company and people enrichment, filter, semantic and lookalike search, work emails, and bulk jobs.

It includes sync and async clients, with types generated from the [OpenAPI spec](https://api.companyenrich.com/openapi/v2.json). It requires Python 3.10 or newer.

## Install

```sh
pip install companyenrich
```

## Quick start

Create an API key in your [dashboard](https://companyenrich.com/dashboard) and keep it secret.

```python
from companyenrich import CompanyEnrich

# Reads COMPANYENRICH_API_KEY from the environment, or pass CompanyEnrich("your-api-key").
client = CompanyEnrich()

company = client.companies.enrich("stripe.com")
print(company.get("name"), company.get("employees"))
```

Responses are plain dictionaries with the API's field names, so they pass straight to `json.dumps` or `pandas.DataFrame`. Optional fields can be absent or `None`, so read them with `.get()`. Editors and type checkers know every field through `companyenrich.types`.

Method arguments are in `snake_case`. Dictionaries you pass, such as `filter`, use the API's own field names.

## Companies

```python
# Add paid data to a lookup. Each expansion costs extra credits.
detailed = client.companies.enrich("stripe.com", expand=["technologies", "workforce"])

# Up to 50 domains at once. Check each item's status.
batch = client.companies.enrich_batch(["stripe.com", "adyen.com"])
for item in batch["items"]:
    found = item.get("company")
    if found:
        print(item["domain"], found.get("name"))

# Filter search
page = client.companies.search(
    filter={"country": "US", "employees": ["51-200", "201-500"], "categories": "saas"},
    page_size=25,
)
print(len(page["items"]), page.get("nextCursor"))

# Free count of the same query
total = client.companies.count(filter={"country": "US"})
print(total["count"])
```

## People

```python
results = client.people.search(
    filter={"domain": "stripe.com", "seniority": ["c-suite", "founder"]},
    page_size=10,
)

person = client.people.enrich("jane@stripe.com")

lookup = client.people.find_email(person["id"], domain="stripe.com")
if lookup["status"] == "found":
    print(lookup.get("email"), lookup.get("certainty"))
```

## Semantic and lookalike search

Semantic search finds companies or people from a plain-language description. Lookalike search finds companies similar to ones you already know. A company search can use either mode but not both, and either can be combined with `filter`. `search_all` accepts the same arguments as `search`.

| Search | Credits per result |
| --- | --- |
| Companies by filters | 1 |
| Companies by description | 2 |
| Lookalike companies | 5 |
| People, in any mode | 2 |

Paid expansions cost extra, and an empty result costs one result's base price. To try a query for free, pass the same arguments to `companies.preview()` or `people.preview()`, which need a plan with previews.

### Companies by description

By default, the API reads attributes such as location and size from your query and applies them. `interpretation` shows what it inferred.

```python
results = client.companies.search(
    semantic={"query": "saas companies in Turkey"},
    page_size=25,
)

for company in results["items"]:
    print(company["domain"], company.get("description"))

interpretation = results.get("interpretation")
if interpretation:
    print(interpretation.get("filter"))  # Inferred filters, such as the country
    print(interpretation.get("boost"))  # Inferred ranking boosts, such as the category
```

Filters you pass take priority over inferred values of the same kind. Set `"autoFilter": False` to turn inference off, or set `weight` (0 to 1) to control how much semantic similarity affects ranking.

```python
filtered = client.companies.search(
    semantic={"query": "AI tools for hospitals", "autoFilter": False},
    filter={"country": "US", "employees": ["51-200", "201-500"]},
    page_size=25,
)
```

### Lookalike companies

Pass 1 to 10 seed domains. Use `"minScore"` (0 to 1) to require a minimum similarity.

```python
similar = client.companies.search(
    lookalike={"domains": ["stripe.com", "adyen.com"]},
    filter={"country": "US", "employees": ["51-200", "201-500"]},
    page_size=25,
)

scores = similar.get("scores") or {}  # Scores are not probabilities
for company in similar["items"]:
    print(company["domain"], scores.get(company["id"]))
```

Keep results in the order returned rather than sorting them by score.

### People by description

The API turns your query into person filters, such as role, seniority and country, plus a description of their current companies. `interpretation` shows both. A query it can't infer any filters from is rejected with an error, so include something concrete like a role or location.

```python
people = client.people.search(
    semantic={"query": "marketing leaders at Series B fintech startups in London"},
    page_size=25,
)

for person in people["items"]:
    print(person.get("name"), person.get("position"))

print(people.get("interpretation"))  # The inferred filters and company description
```

### People at matching companies

Use `company` to find people by the kind of company they work at. These searches cover people at the 1,000 best-matching companies.

```python
# Executives at companies matching a description
executives = client.people.search(
    filter={"seniority": ["c-suite", "vp"]},
    company={"semantic": {"query": "AI tools for hospitals"}},
    page_size=25,
)

# Executives at companies similar to your best customers
similar_teams = client.people.search(
    filter={"seniority": ["c-suite", "vp"]},
    company={"lookalike": {"domains": ["stripe.com", "adyen.com"]}},
    page_size=25,
)
```

## Pagination

`search()` returns one page. The `*_all` methods return an iterator that requests pages as you consume them.

```python
for company in client.companies.search_all(filter={"country": "TR"}, page_size=100):
    print(company["domain"])
```

These are available as `companies.search_all`, `people.search_all`, `batches.list_all`, and `geo.search_countries_all`, `geo.search_states_all` and `geo.search_cities_all`.

Search credits are charged for every result on a fetched page, even if you stop iterating partway through it. Set `page_size` close to the number of results you plan to use.

## Bulk jobs

Bulk enrichment and search exports run in the background.

```python
job = client.companies.bulk_enrichment.create(["stripe.com", "adyen.com"])

client.batches.wait_for_completion(
    job["id"],
    on_progress=lambda batch: print(batch["progress"]["succeeded"], batch["progress"]["total"]),
)

for record in client.companies.bulk_enrichment.stream(job["id"]):
    enriched = record.get("company")
    if enriched:
        print(record["domain"], enriched.get("name"))
```

`companies.bulk_enrichment`, `companies.search_export` and `people.search_export` share the same methods:

| Method | Returns |
| --- | --- |
| `create(...)` | The new batch's status |
| `stream(id)` | An iterator of records, best for large jobs |
| `results(id)` | One JSON document with every record |
| `csv(id)` | The CSV as text |
| `iter_csv(id)` | The CSV as raw bytes, for writing to a file |

## Async

`AsyncCompanyEnrich` has the same methods. Await calls that return a result, and use `async for` with the iterators.

```python
import asyncio

from companyenrich import AsyncCompanyEnrich


async def main() -> None:
    async with AsyncCompanyEnrich() as client:
        company = await client.companies.enrich("stripe.com")
        print(company.get("name"))

        async for person in client.people.search_all(filter={"domain": "stripe.com"}, page_size=25):
            print(person.get("name"))


asyncio.run(main())
```

Both clients can be used as context managers, or closed with `close()`, to release network connections.

## Errors

Failed requests raise a subclass of `APIError`, which carries `status`, `title`, `detail`, `errors` (field-level validation messages) and `trace_id` (include it when contacting support).

```python
from companyenrich import APIError, NotFoundError, PaymentRequiredError

try:
    client.companies.enrich("example.invalid")
except NotFoundError:
    print("No company found")
except PaymentRequiredError:
    print("Out of credits, or not included in this plan")
except APIError as error:
    print(error.status, error.detail, error.trace_id)
```

| Status | Class |
| --- | --- |
| 400 | `BadRequestError` |
| 401 | `AuthenticationError` |
| 402 | `PaymentRequiredError` |
| 403 | `PermissionDeniedError` |
| 404 | `NotFoundError` |
| 422 | `ValidationError` |
| 429 | `RateLimitError` |
| 5xx | `ServerError` |
| Other | `APIError` |

`APIConnectionError` and `APITimeoutError` cover requests that never received a response. Everything above extends `CompanyEnrichError`.

## Retries and timeouts

Failed requests are retried up to twice with exponential backoff.

| Failure | GET and free POST endpoints | Other POST endpoints |
| --- | --- | --- |
| 429 rate limit | Retried | Retried |
| 408, 5xx, connection error, timeout | Retried | Not retried |

POST requests that consume credits or start a job are not repeated after an ambiguous failure, because the first attempt may already have been charged or created a batch.

## Configuration

```python
configured = CompanyEnrich("your-api-key", timeout=30.0, max_retries=4)

# Every method accepts per-request options.
configured.me(options={"timeout": 5.0, "max_retries": 0})
```

| Option | Default | Description |
| --- | --- | --- |
| `api_key` | `COMPANYENRICH_API_KEY` | Your API key |
| `base_url` | `https://api.companyenrich.com` | API origin, for proxies |
| `timeout` | `120.0` | Timeout in seconds. `None` disables it |
| `max_retries` | `2` | Retries after the first attempt |
| `default_headers` | none | Headers added to every request |
| `http_client` | new client | A custom `httpx.Client` or `httpx.AsyncClient` |

## API reference

| SDK method | Endpoint |
| --- | --- |
| `companies.get(id)` | `GET /v2/companies/{companyId}` |
| `companies.enrich(domain)` | `GET /v2/companies/enrich` |
| `companies.enrich_by_properties(...)` | `POST /v2/companies/enrich` |
| `companies.enrich_batch(domains)` | `POST /v2/companies/enrich/batch` |
| `companies.autocomplete(query)` | `GET /v2/companies/autocomplete` |
| `companies.workforce(...)` | `GET /v2/companies/workforce` |
| `companies.search(...)` | `POST /v2/companies/search` |
| `companies.count(...)` | `POST /v2/companies/search/count` |
| `companies.preview(...)` | `POST /v2/companies/search/preview` |
| `companies.bulk_enrichment.*` | `/v2/companies/enrich/bulk` |
| `companies.search_export.*` | `/v2/companies/search/export` |
| `people.get(id)` | `GET /v2/people/{personId}` |
| `people.enrich(email)` | `POST /v2/people/enrich` |
| `people.find_email(id)` | `GET /v2/people/{personId}/email` |
| `people.search(...)` | `POST /v2/people/search` |
| `people.count(...)` | `POST /v2/people/search/count` |
| `people.preview(...)` | `POST /v2/people/search/preview` |
| `people.search_export.*` | `/v2/people/search/export` |
| `batches.list(...)` | `GET /v2/batches` |
| `batches.get(id)` | `GET /v2/batches/{id}` |
| `batches.cancel(id)` | `POST /v2/batches/{id}/cancel` |
| `batches.raw_results(id)` | `GET /v2/batches/{id}/results` |
| `batches.wait_for_completion(id)` | Polls `GET /v2/batches/{id}` |
| `geo.regions()` | `GET /v2/geo/regions` |
| `geo.country(code)` | `GET /v2/geo/countries/{countryCode}` |
| `geo.search_countries(...)` | `POST /v2/geo/countries` |
| `geo.search_states(...)` | `POST /v2/geo/states` |
| `geo.search_cities(...)` | `POST /v2/geo/cities` |
| `industries.list()` | `GET /v2/industries` |
| `keywords.autocomplete(query)` | `GET /v2/keywords/autocomplete` |
| `technologies.autocomplete(query)` | `GET /v2/technologies/autocomplete` |
| `positions.autocomplete(query)` | `GET /v2/positions/autocomplete` |
| `me()` | `GET /v2/me` |

See the [API documentation](https://api.companyenrich.com/openapi/v2.json) for parameters and credit costs.

## Development

```sh
uv sync
uv run pytest
uv run python scripts/unasync.py                 # Regenerates the sync client after editing _async
uv run python scripts/generate_types.py --fetch  # Downloads the latest spec and regenerates types
```

To release, bump `version` in `pyproject.toml` and push to `main`. The publish workflow runs the checks and publishes that version to PyPI if it is new.

## License

MIT
