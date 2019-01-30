import re
from pathlib import Path
from urllib.parse import ParseResult, urlparse

import click
import jsonlines
import pandas as pd
import requests
from lxml import html
from tqdm import tqdm


# translation of contact keyword in different european languages.
CONTACT_KEYWORD_COLLECTION = 'contacto|contact|Epikoinonía|kapcsolatba lépni|Hafðu samband|teagmháil|contatto|kontakts|kontaktas|контакт|contato|kontakt|kontakta|cysylltu'  # noqa
# creating the list of all those contact keywords for checking the urls
#  which starts with these words.
CONTACT_KEYWORD_COLLECTION_LIST = CONTACT_KEYWORD_COLLECTION.split('|')
# regular expression for checking these contact keywords exist in the url.
CONTACT_EXPRESSION = re.compile(CONTACT_KEYWORD_COLLECTION)


# method for passing the input file with domains and it will return contact url
def extract(data_directory, output_file):
    # variable for checking how many times contact url found for domains
    n_contacts_found = 0
    # loading the data file using pandas
    df = pd.read_csv(data_directory)
    # writing the jsonl file after getting the contact url.
    with jsonlines.open(output_file, 'a') as fp:
        # iteration for getting the domains from data frame and get contact url
        for i, row in tqdm(df.iterrows(), total=len(df.response_url)):
            url = row.domains
            # using extract_contact on url for getting the contact_urls
            contact_found = extract_contact(url)
            # checking if we found the contact url for this domain then
            #  save it in jsonl file.
            if contact_found:
                fp.write(contact_found)
                n_contacts_found += 1


def extract_contact(url):
    # using try and catch blocks for saving the code from runtime exception.
    try:
        contacts_found = {}
        # pre-processing the domains for getting the domain in proper format.
        url = urlparse(url, 'http')
        netloc = url.netloc or url.path
        path = url.path if url.netloc else ''
        if not netloc.startswith('www.'):
            netloc = 'www.' + netloc
        url = ParseResult('http', netloc, path, *url[3:])
        # after pre-processing we get this domain.
        domain = url.geturl()
        # using request for getting the html content from domain
        page = requests.get(domain)
        # using lxml library's html class for getting the html page from text
        webpage = html.fromstring(page.content)
        # for getting all the links from the html page
        all_urls = webpage.xpath('//a/@href')
        # creating  the list of all the contact urls by checking urls with
        #  contact's regular expressions
        contact_page_url_list = [
            url for url in all_urls if re.search(CONTACT_EXPRESSION, url)
        ]
        # check if it found some contact url or not.
        if not contact_page_url_list:
            return
        else:
            # if found gets only the first one.
            contact_page_url = contact_page_url_list[0]
            ''' using the contact keyword collection list for checking the
             irregularity in urls likes some times the url is just like the
             page name e.g contact, /contact, /de/contact, /en/contact and
              #contact in the urls which is wrong so for getting the exact url
              we need to process our urls so for that i have created the code
              which is as follow.
             '''
            for keyword in CONTACT_KEYWORD_COLLECTION_LIST:
                if contact_page_url.startswith('/' + keyword):
                    contact_page_url = domain + contact_page_url
                if contact_page_url.startswith(keyword):
                    if not domain.endswith('/'):
                        domain = domain + '/'
                    contact_page_url = domain + contact_page_url
                if contact_page_url.startswith('#'):
                    if not domain.endswith('/'):
                        domain = domain + '/'
                    contact_page_url = domain + contact_page_url
                if contact_page_url.startswith('/d'):
                    contact_page_url = domain + contact_page_url
                if contact_page_url.startswith('/e'):
                    contact_page_url = domain + contact_page_url
            # after processing the contact url now i will get html from
            #  those urls
            response = requests.get(contact_page_url).text
            contacts_found['url'] = contact_page_url
            contacts_found['html'] = response
            return contacts_found
    except requests.exceptions.RequestException as e:
        return


# for getting the arguments
@click.command()
@click.argument('data_directory', type=Path)
@click.argument('output_file', type=Path)
def entrypoint(data_directory, output_file):
    extract(data_directory, output_file)
