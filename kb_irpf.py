links = ["https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/perguntas-frequentes/imposto-de-renda/dirpf"]



import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

# URL base
BASE_URL = "https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/"

class IRPF_page:
    def __init__(self, url):
        self.url = url
        self.content = None
        self.scraped = False

    def __repr__(self):
        return f"IRPF_page({self.url})"

    def scrape(self):
        if self.scraped:
            return
        response = requests.get(self.url)
        response.raise_for_status()  # levanta erro se falhar
        self.content = BeautifulSoup(response.text, "html.parser")
        self.scraped = True

    def get_links(self):
        if not self.scraped:
            self.scrape()
        links = set()
        for a_tag in self.content.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(self.url, href)
            if urlparse(full_url).netloc.endswith("gov.br"):
                links.add(full_url)
        return links

    def get_content(self):
        if not self.scraped:
            self.scrape()
        return self.content

    def get_text(self):
        if not self.scraped:
            self.scrape()
        return self.content.get_text()

    def get_title(self):
        if not self.scraped:
            self.scrape()
        return self.content.find("title").get_text()

    def get_description(self):
        if not self.scraped:
            self.scrape()
        return self.content.find("meta", attrs={"name": "description"})["content"]

    def run_all(self):
        if not self.scraped:
            self.scrape()
        return {
            "links": self.get_links(),
            "content": self.get_content(),
            "text": self.get_text(),
            "title": self.get_title(),
            "description": self.get_description()
        }

def crawl_irpf(BASE_URL):
    pages = set([BASE_URL])
    scraped_pages = list()
    scraped_urls = set()
    while pages:
        print(f"{len(scraped_pages)} pages scraped, {len(pages)} pages remaining...")
        url = pages.pop()
        if url in scraped_urls:
            raise ValueError(f"Page {url} already scraped")
        page = IRPF_page(url)
        page.scrape()
        scraped_pages.append(page)
        scraped_urls.add(url)
        pages.update([x.split("#", 1)[0] for x in page.get_links() if BASE_URL in x and x.split("#", 1)[0] not in scraped_urls])
    return scraped_pages

result = crawl_irpf(BASE_URL)



def get_links_from_page(url):
    # Requisição da página
    response = requests.get(url)
    response.raise_for_status()  # levanta erro se falhar

    # Parse do HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Coletar todos os links da página
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(BASE_URL, href)

        # Filtra apenas links do mesmo domínio
        if urlparse(full_url).netloc.endswith("gov.br"):
            links.add(full_url)
    return links


valids = [x for x in get_links_from_page(BASE_URL) if BASE_URL in x]


all_links = []
for i in tqdm(valids):
    all_links.extend(get_links_from_page(i))


new_valids = [x for x in all_links if BASE_URL in x]
len(valids)
len(new_valids)


all_links = list(set([x.url for x in result]))

from trafilatura import extract   
extract(all_links[0], output_format="json", with_metadata=True)

k = extract(all_links[0], output_format="json", with_metadata=True)


# import the necessary functions
from trafilatura import fetch_url, extract

# grab a HTML file to extract data from
urls = [fetch_url(x) for x in all_links]
kb = [extract(x, output_format="json", with_metadata=True) for x in urls]
