from typing import List, Dict, Optional
import requests
import xml.etree.ElementTree as ET
import re
import time

# PubMed E-utilities API endpoints
PUBMED_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# List of common academic keywords to filter out academic affiliations
ACADEMIC_KEYWORDS = [
    "university", "college", "institute", "school", "hospital", "faculty", "department",
    "center", "centre", "academy", "université", "universidad", "università", "clinic"
]

# List of common pharma/biotech keywords (expand as needed)
PHARMA_KEYWORDS = [
    "pharma", "biotech", "therapeutics", "laboratories", "inc", "ltd", "gmbh", "s.a.", "s.r.l.", "corp", "llc"
]

# Add throttle constant for PubMed E-utilities (max 3 requests/sec without API key)
THROTTLE_SECONDS = 0.34  # ~3 req/sec

def is_non_academic_affiliation(affil: Optional[str]) -> bool:
    """
    Return True if the affiliation is likely non-academic (pharma/biotech).
    Checks for absence of academic keywords and presence of pharma/biotech keywords.
    """
    if not affil:
        return False
    affil_lower = affil.lower()
    if any(word in affil_lower for word in ACADEMIC_KEYWORDS):
        return False
    if any(word in affil_lower for word in PHARMA_KEYWORDS):
        return True
    return False

def fetch_pubmed_details(pubmed_ids: List[str]) -> List[Dict]:
    """
    Fetch details for a list of PubMed IDs using the EFetch API.
    Parses the XML response and extracts required fields for each article.
    Returns a list of dictionaries, one per article.
    """
    if not pubmed_ids:
        return []

    results = []
    BATCH_SIZE = 100  # NCBI allows up to 100 IDs per EFetch request

    for i in range(0, len(pubmed_ids), BATCH_SIZE):
        batch_ids = pubmed_ids[i:i + BATCH_SIZE]
        params = {
            "db": "pubmed",
            "id": ",".join(batch_ids),
            "retmode": "xml"
        }
        resp = requests.get(PUBMED_EFETCH_URL, params=params)
        resp.raise_for_status()

        # 🕒 Throttle between EFetch batch requests
        if i + BATCH_SIZE < len(pubmed_ids):
            time.sleep(THROTTLE_SECONDS)

        root = ET.fromstring(resp.content)
        for article in root.findall(".//PubmedArticle"):
            result = parse_pubmed_article(article)
            if result:
                results.append(result)

    return results


# def fetch_pubmed_ids(query: str, retmax: int = 100) -> List[str]:
#     """
#     Fetch all PubMed IDs for a given query using the ESearch API.
#     Handles pagination to retrieve all matching IDs.
#
#     - query: PubMed search query string.
#     - retmax: Number of results to fetch per request (batch size).
#     Returns a list of all matching PubMed IDs as strings.
#     """
#     all_ids = []
#     retstart = 0
#
#     while True:
#         params = {
#             "db": "pubmed",
#             "term": query,
#             "retmax": retmax,
#             "retstart": retstart,
#             "retmode": "json"
#         }
#         resp = requests.get(PUBMED_ESEARCH_URL, params=params)
#         resp.raise_for_status()
#
#         time.sleep(THROTTLE_SECONDS)  # Avoid rate-limiting
#
#         data = resp.json()
#         ids = data["esearchresult"].get("idlist", [])
#         all_ids.extend(ids)
#
#         total = int(data["esearchresult"]["count"])
#         retstart += retmax
#
#         if retstart >= total:
#             break
#
#     return all_ids


# def fetch_pubmed_ids(query: str, retmax: int = 100) -> List[str]:
#     """
#     Fetch PubMed IDs for a given query using the ESearch API.
#     - query: PubMed search query string.
#     - retmax: Maximum number of IDs to return.
#     Returns a list of PubMed IDs as strings.
#     """
#     params = {
#         "db": "pubmed",
#         "term": query,
#         "retmax": retmax,
#         "retmode": "json"
#     }
#     resp = requests.get(PUBMED_ESEARCH_URL, params=params)
#     resp.raise_for_status()
#
#     # 🕒 Throttle after ESearch request to avoid hitting limits
#     time.sleep(THROTTLE_SECONDS)
#
#     data = resp.json()
#     return data["esearchresult"]["idlist"]

def fetch_pubmed_ids(query: str, retmax: int = 100) -> List[str]:
    """
    Fetch all PubMed IDs for a given query using the ESearch API.
    Handles pagination to retrieve all matching IDs.

    - query: PubMed search query string.
    - retmax: Number of results to fetch per request (batch size).
    Returns a list of all matching PubMed IDs as strings.
    """
    # Clean up query input to avoid invalid characters
    query = query.strip().replace("\n", " ").replace("\t", " ")

    all_ids = []
    retstart = 0
    total = None  # Will store total result count once known

    while True:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": retmax,
            "retstart": retstart,
            "retmode": "json"
        }
        resp = requests.get(PUBMED_ESEARCH_URL, params=params)
        resp.raise_for_status()

        time.sleep(THROTTLE_SECONDS)  # Avoid rate-limiting

        try:
            data = resp.json()
        except ValueError as e:
            print("[ERROR] Failed to parse JSON from ESearch API.")
            print("[DEBUG] Raw response:\n", repr(resp.text))
            raise e

        # Get total count once
        if total is None:
            total = int(data["esearchresult"]["count"])
            print(f"[INFO] Total results found: {total}")

        ids = data["esearchresult"].get("idlist", [])
        all_ids.extend(ids)

        retstart += retmax
        if retstart >= total:
            break

    return all_ids


def get_doi_from_pubmed_xml(article: ET.Element) -> Optional[str]:
    """
    Extract DOI from PubMedArticle XML if available.
    """
    article_ids = article.findall('.//ArticleId')
    for aid in article_ids:
        if aid.attrib.get('IdType', '').lower() == 'doi' and aid.text:
            return aid.text.strip()
    return None

def get_email_from_crossref(doi: str) -> Optional[str]:
    """
    Query CrossRef API for a DOI and try to extract a corresponding author email.
    """
    url = f"https://api.crossref.org/works/{doi}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        authors = data.get('message', {}).get('author', [])
        for author in authors:
            email = author.get('email')
            if email:
                return email if isinstance(email, str) else email[0]
        for author in authors:
            affils = author.get('affiliation', [])
            for affil in affils:
                if 'mailto:' in affil.get('name', ''):
                    match = re.search(r"mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", affil['name'])
                    if match:
                        return match.group(1)
    except Exception:
        return None
    return None

def get_email_from_europepmc(pmid: str) -> Optional[str]:
    """
    Query Europe PMC API for a PubMed ID and try to extract a corresponding author email.
    """
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{pmid}%20AND%20SRC:MED&format=json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        results = data.get('resultList', {}).get('result', [])
        if not results:
            return None
        for result in results:
            if 'authorList' in result:
                for author in result['authorList']['author']:
                    if 'email' in author:
                        return author['email']
            if 'affiliation' in result and '@' in result['affiliation']:
                match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", result['affiliation'])
                if match:
                    return match.group(0)
    except Exception:
        return None
    return None

def get_email_from_europepmc_emails_endpoint(pmid: str) -> Optional[str]:
    """
    Query Europe PMC's /emails endpoint for a PubMed ID to extract any available author emails.
    """
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/MED/{pmid}/emails/json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        emails = data.get('emailList', {}).get('email', [])
        if emails:
            return emails[0]
    except Exception:
        return None
    return None

try:
    from scholarly import scholarly
    from bs4 import BeautifulSoup
except ImportError:
    scholarly = None
    BeautifulSoup = None

def parse_pubmed_article(article: ET.Element) -> Optional[Dict]:
    """
    Parse a PubMedArticle XML element and extract required fields:
    - PubmedID, Title, Publication Date, Non-academic Author(s),
      Company Affiliation(s), Corresponding Author Email.
    Returns a dictionary or None if no non-academic author is found.
    """
    medline = article.find("MedlineCitation")
    article_info = medline.find("Article") if medline is not None else None
    if article_info is None:
        return None

    pmid = medline.findtext("PMID")

    # ✅ FIXED: Robust extraction of full article title
    title_elem = article_info.find("ArticleTitle")
    if title_elem is not None:
        title = ''.join(title_elem.itertext()).strip()
    else:
        title = ""

    pub_date = extract_pub_date(article_info)
    authors = article_info.find("AuthorList")
    non_acad_authors = []
    company_affils = []
    possible_emails = []

    if authors is not None:
        for author in authors.findall("Author"):
            affils = [affil.text for affil in author.findall("AffiliationInfo/Affiliation") if affil.text]
            email_from_identifier = None
            for identifier in author.findall("Identifier"):
                if identifier.attrib.get("Source", "").lower() == "email" and identifier.text:
                    email_from_identifier = identifier.text
            for elec_addr in author.findall("ElectronicAddress"):
                if elec_addr.text:
                    email_from_identifier = elec_addr.text
            if email_from_identifier:
                possible_emails.append(email_from_identifier)
            if not affils:
                continue
            for affil in affils:
                if is_non_academic_affiliation(affil):
                    name = extract_author_name(author)
                    non_acad_authors.append(name)
                    company_affils.append(affil)
                    email = extract_email_from_affil(affil)
                    if email:
                        if 'corresponding' in affil.lower():
                            possible_emails.insert(0, email)
                        else:
                            possible_emails.append(email)

    if not non_acad_authors:
        return None

    corresponding_email = None
    if possible_emails:
        corresponding_email = possible_emails[0]
    else:
        doi = get_doi_from_pubmed_xml(article)
        pmid = medline.findtext("PMID")
        if doi:
            corresponding_email = get_email_from_crossref(doi)
            time.sleep(0.2)  # slight delay for external APIs
        if not corresponding_email and pmid:
            corresponding_email = get_email_from_europepmc(pmid)
            time.sleep(0.2)
        if not corresponding_email and pmid:
            corresponding_email = get_email_from_europepmc_emails_endpoint(pmid)
            time.sleep(0.2)

    return {
        "PubmedID": pmid,
        "Title": title,
        "Publication Date": pub_date,
        "Non-academic Author(s)": "; ".join(non_acad_authors),
        "Company Affiliation(s)": "; ".join(company_affils),
        "Corresponding Author Email": corresponding_email or ""
    }


def extract_pub_date(article_info: ET.Element) -> str:
    """
    Extract publication date as a string in the format 'Year-Month-Day'.
    Returns an empty string if not available.
    """
    date = article_info.find("Journal/JournalIssue/PubDate")
    if date is not None:
        year = date.findtext("Year")
        month = date.findtext("Month")
        day = date.findtext("Day")
        return "-".join(filter(None, [year, month, day]))
    return ""

def extract_author_name(author: ET.Element) -> str:
    """
    Extract author name as 'LastName, Initials'.
    Returns 'Unknown' if not available.
    """
    last = author.findtext("LastName")
    initials = author.findtext("Initials")
    if last and initials:
        return f"{last}, {initials}"
    return last or "Unknown"

def extract_email_from_affil(affil: str) -> Optional[str]:
    """
    Extract email address from affiliation string if present using regex.
    Returns the email or None if not found.
    """
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", affil)
    return match.group(0) if match else None
