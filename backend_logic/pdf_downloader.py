import httpx
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path

def download_pdf_if_available(url, base_domain_str, client: httpx.Client, save_dir: Path):
    try:
        response = client.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            if href.lower().endswith('.pdf'):
                pdf_url = urljoin(url, href)
                
                parsed_pdf_url = urlparse(pdf_url)
                pdf_filename = Path(parsed_pdf_url.path).name
                save_path = save_dir / pdf_filename

                try:
                    pdf_response = client.get(pdf_url)
                    pdf_response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        f.write(pdf_response.content)
                    print(f"✅ PDF downloaded and saved to {save_path}")
                    return str(save_path)
                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    print(f"Failed to download PDF from {pdf_url}: {e}")
    
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        print(f"Could not access {url} to check for PDFs: {e}")
        
    return None

if __name__ == '__main__':
    test_url = "https://www.city.ama.aichi.jp/kurashi/toshikeikaku/toshikeikaku/1004481.html"
    test_domain = "ama.aichi.jp"
    save_directory = Path("./test_downloads")
    save_directory.mkdir(exist_ok=True)
    
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        pdf_path = download_pdf_if_available(test_url, test_domain, client, save_directory)
        if pdf_path:
            print(f"Test successful, PDF at: {pdf_path}")
        else:
            print("No PDF found for the test URL.")
