import requests
from bs4 import BeautifulSoup
import json
import io
from PyPDF2 import PdfReader

def scrape_webpage(url):
    try:
        if url.lower().endswith('.pdf'):
            response = requests.get(url)
            response.raise_for_status()
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)
            text_content = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    # Split into lines for better segmentation
                    text_content.extend([line.strip() for line in text.split('\n') if line.strip()])
            return text_content
        else:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract text from paragraphs and headers
            paragraphs = soup.find_all('p')
            headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            text_content = []
            for header in headers:
                text_content.append(header.get_text())
            for paragraph in paragraphs:
                text_content.append(paragraph.get_text())
            
            return text_content
    except requests.exceptions.RequestException as e:
        print(f"Error scraping {url}: {e}")
        return []
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []

def segment_into_prompt_response(text_content):
    prompt_response_pairs = []
    for i in range(len(text_content) - 1):
        prompt = text_content[i]
        response = text_content[i + 1]
        prompt_response_pairs.append({"prompt": prompt, "completion": response})
    return prompt_response_pairs

def save_to_jsonl(data, filename):
    system_message = {"role": "system", "content": "Reply user's question as accurately as possible."}
    with open(filename, 'w') as f:
        for entry in data:
            messages = [
                system_message,
                {"role": "user", "content": entry["prompt"]},
                {"role": "assistant", "content": entry["completion"]}
            ]
            json.dump({"messages": messages}, f)
            f.write('\n')

# Replace these URLs with your actual target pages
urls = [
    'https://prod-edam.honeywell.com/content/dam/honeywell-edam/pmt/hps/products/pas/experion-pks/human-machine-interface-hmi/experion%C2%AE-orion-console/pmt-hps-experion-orion-console-whitepaper-final-sw.pdf',
    'https://prod-edam.honeywell.com/content/dam/honeywell-edam/pmt/hps/products/pmc/field-instruments/honeywell-versatilis-transmitter/pmt-hps-fi-honeywell-versatilis-transmitter-brochure.pdf',
    'https://prod-edam.honeywell.com/content/dam/honeywell-edam/pmt/hps/products/ccc/turbomachinery-automation-systems/ccc-inside/ccc-inside%C2%AE-for-honeywell-experion%C2%AE-pks/hon-ccc-inside-experion-pks-flyer-en.pdf',
    'https://prod-edam.honeywell.com/content/dam/honeywell-edam/pmt/hps/products/pmc/modular-systems/experion-lx/pmt-hps-dcs-or-plc-whitepaper.pdf',
    'https://process.honeywell.com/content/dam/process/en/documents/document-lists/doc-list-batch-automation/ExperionBatchIG.pdf',
    'https://process.honeywell.com/content/dam/forge/en/documents/case-study/Achieving-Plant-Wide-Optimization.pdf'
]

all_prompt_response_pairs = []
for url in urls:
    text_content = scrape_webpage(url)
    prompt_response_pairs = segment_into_prompt_response(text_content)
    all_prompt_response_pairs.extend(prompt_response_pairs)

save_to_jsonl(all_prompt_response_pairs, 'prompt_response_pairs.jsonl')
print("Scraping and conversion completed. Data saved to prompt_response_pairs.jsonl.")
