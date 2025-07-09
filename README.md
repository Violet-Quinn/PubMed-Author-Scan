# PubMedAuthorScan

Fetch PubMed research papers with at least one author affiliated with a pharmaceutical or biotech company, and output the results as a CSV file. PubMedAuthorScan is a professional tool for industry-focused literature mining.

## Project Structure

- `pubmed_authorscan/` - Python module containing core logic and CLI
  - `core.py` - Core functions for fetching and parsing PubMed data
  - `cli.py` - Command-line interface using Typer
- `pyproject.toml` - Poetry configuration and dependencies
- `README.md` - Project documentation

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-github-repo-url>
   cd <repo-directory>
   ```

2. **Install dependencies with Poetry:**
   ```bash
   poetry install
   ```

## Usage

After installation, you can run the CLI tool using Poetry:

```bash
poetry run get-papers-list "your pubmed query here" [OPTIONS]
```

Or, after installing as a package:

```bash
get-papers-list "your pubmed query here" [OPTIONS]
```

You can also run the command without a query to show the help section:

```bash
poetry run get-papers-list
```

### Options

- `-h`, `--help`         Show usage instructions (works even without a query)
- `-d`, `--debug`        Enable debug output
- `-f`, `--file` FILE    Specify output CSV filename (prints to console if omitted)

### Example

```bash
poetry run get-papers-list "cancer immunotherapy" -f results.csv --debug
```

## How It Works

- The program fetches papers from PubMed using the full query syntax provided by the user.
- It identifies papers with at least one author affiliated with a pharmaceutical or biotech company (using heuristics on affiliation strings).
- Results are output as a CSV file or printed to the console, with the following columns:
  - PubmedID
  - Title
  - Publication Date
  - Non-academic Author(s)
  - Company Affiliation(s)
  - Corresponding Author Email

## Author Affiliation Filtering

To identify non-academic (pharma/biotech) authors, the tool uses keyword-based filtering:

- **Excludes** affiliations containing academic terms like `university`, `hospital`, `institute`, etc.
- **Includes** affiliations with industry terms like `pharma`, `biotech`, `therapeutics`, `inc`, `ltd`, etc.

Only papers with at least one non-academic author are included in the output.


## Why Not Scrape Publisher Sites or Google Scholar for Emails?
- Scraping publisher websites or Google Scholar for author emails is not recommended for several reasons:
  - **Legal and Ethical Issues:** Most publishers and Google Scholar prohibit automated scraping in their terms of service. Violating these terms can result in IP bans or legal action.
  - **Unreliable and Unstable:** The structure of publisher and Google Scholar pages can change at any time, breaking scrapers and making maintenance difficult.
  - **No Guarantee of Results:** Even when implemented in this project, scraping or searching Google Scholar did **not** yield any additional author emails in our tests. Most emails are not exposed in a structured or accessible way on these platforms, and the code did not find any emails this way.
  - **Respect for Privacy:** Authors may not wish for their emails to be harvested and distributed without consent.
- For these reasons, this project only uses public APIs (PubMed, CrossRef, Europe PMC) and metadata for email extraction, ensuring compliance and reliability.

## Rate Limiting / Throttling

- To comply with **NCBI PubMed’s E-utilities rate limits**, the tool automatically throttles API requests:
  - A delay of **~0.34 seconds** is added between requests to the PubMed E-utilities API (`esearch` and `efetch`), which aligns with NCBI's guidelines of **no more than 3 requests per second** without an API key.
  - Additional delays are added when querying external services like **CrossRef** and **Europe PMC** for corresponding author emails.
- This helps prevent **IP bans or temporary access restrictions**.

💡 **Note**: If you plan to make large-scale queries, consider obtaining an [NCBI API key](https://www.ncbi.nlm.nih.gov/account/settings/) to increase your rate limit.


## Development & Testing

- All dependencies are managed with Poetry. Run `poetry install` to set up the environment.

## Tools & Libraries Used

- [Typer](https://typer.tiangolo.com/) for CLI
- [Requests](https://docs.python-requests.org/) for HTTP requests
- [Pandas](https://pandas.pydata.org/) for CSV output
- [lxml](https://lxml.de/) and [xml.etree.ElementTree](https://docs.python.org/3/library/xml.etree.elementtree.html) for XML parsing
- [Rich](https://rich.readthedocs.io/) for elegant terminal formatting, including colored output, tables, and better logging
- [tqdm](https://tqdm.github.io/) for progress bars during article processing, providing real-time feedback for long-running tasks
- [scholarly](https://github.com/scholarly-python-package/scholarly) and [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) (optional, for advanced email extraction)
- [OpenAI GPT-4.1](https://openai.com/) for assisted code generation and refinement


## Notes

- The CLI supports `-h` and `--help` even when no query is provided.
- The tool handles common errors like network failures or empty results.
- Code is modular, type-annotated, and built for maintainability.
