import math
import requests
from bs4 import BeautifulSoup
import asyncio
from pyppeteer import launch
import argparse
import os.path
import logging
from urllib.parse import urlparse
import multiprocessing
import time

# Press ⌃R to execute it or replace it with your code.
bad_status_codes = [301, 303, 404]
bad_texts = ["not found", "not exist", "don't exist", "can't be found", "invalid page", "invalid webpage", "invalid path"]
probable_html_tags = ["h1", "h2", "h3", "title"]


def check_redirects(response):
    logging.info("  [*] Checking if webpage with no redirects returns a bad code")
    origin_url = urlparse(response.url)

    # We create a list of probable simple redirects
    origin_list = [origin_url.hostname, "http://" + origin_url.hostname, "https://" + origin_url.hostname, "http://" + origin_url.hostname + "/",
                   "https://" + origin_url.hostname + "/", "http://" + origin_url.hostname + "/#", "https://" + origin_url.hostname + "/#"]

    # Check new and old urls
    if response.history:
        for resp in response.history:
            if resp.is_redirect or resp.is_permanent_redirect:
                if resp.url in origin_list:
                    logging.info("      [-] Bad redirect found: {}".format(response.url))
                    return True
    return False

def requests_page_titles(response):

    soup = BeautifulSoup(response.text, 'html.parser')

    logging.info("  [*] Searching for keywords using Beautiful Soup")
    # We check if any of the htlm tags has some text similar to the ones in bad_texts array
    for prob_tag in probable_html_tags:
        for tag in soup.find_all(prob_tag):
            for bad_text in bad_texts:
                if bad_text in tag.get_text().lower():
                    logging.info("      [-] Bad text found: {}".format(bad_text))
                    return True


async def puppeteer_page_titles(url):

    logging.info("  [*] Using Pyppeteer to find bad tags in dynamic html")
    browser = await launch({"headless": True})

    page = await browser.newPage()
    # set page viewport to the largest size
    #await page.setViewport({"width": 1600, "height": 900})
    # navigate to the page
    await page.goto(url)
    # locate the search box
    # We check if any of the htlm tags has some text similar to the ones in bad_texts array
    try:
        #await page.waitForSelector("title")
        html = await page.content()
        await browser.close()
        parsed_url = urlparse(page.url)
    except:
        logging.info("      [!] Timeout while awaiting for tags. Page may be down.")
        return False

    # Redirection case
    if url != page.url:
        logging.info("      [!] Redirection detected to {}".format(page.url))
        if parsed_url.path in ["/", "/#"]:
            logging.info("      [-] Redirected to root!")
            return True

    soup = BeautifulSoup(html, 'html.parser')
    for prob_tag in probable_html_tags:
        for tag in soup.find_all(prob_tag):
            for bad_text in bad_texts:
                if bad_text in tag.get_text().lower():
                    logging.info("      [-] Bad text found: {}".format(bad_text))
                    return True

    return False


async def check_all_methods(lines, good_urls):

    past_response = ""
    for url in lines:
        logging.info("[*] Checking URL: {}".format(url))
        r = requests.get(url)
        if past_response == r.text:
            logging.info("  [!] Same page detected. Skipping.")
            past_response = r.text
            continue

        past_response = r.text

        # Splitted in three ifs to improve timing: If redirect
        if check_redirects(r):
            continue

        if requests_page_titles(r):
            continue

        ppt = await puppeteer_page_titles(url)
        if ppt:
            continue

        logging.info("[*] Url found legit!")
        good_urls.append(url + "\n")


def multiprocess_executer(args):
    manager = multiprocessing.Manager()
    good_urls = manager.list()
    cpus = multiprocessing.cpu_count()
    jobs = []

    if os.path.isfile(args.input_file):
        with open(args.input_file, "r") as ifile:
            lines = ifile.read().splitlines()

            # Here we are splitting the file in multiple pieces for better processing
            parts_len = math.ceil(len(lines)/cpus)
            parts = list(chunks_from_lines(lines, parts_len))
    else:
        logging.error("[!] File not found! {}".format(args.input_file))
        parser.print_help()

    for i in range(cpus):
        p = multiprocessing.Process(target=worker, args=(parts[i], good_urls))
        jobs.append(p)
        p.start()

    for proc in jobs:
        proc.join()

    with open(args.output_file, "w") as ofile:
        ofile.writelines(good_urls)

# Aux function to divide a file into chunks
def chunks_from_lines(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

def single_thread_executer(args):

    if os.path.isfile(args.input_file):
        with open(args.input_file, "r") as ifile:
            lines = ifile.read().splitlines()
    else:
        logging.error("[!] File not found! {}".format(args.input_file))
        parser.print_help()

    good_urls = []
    worker(lines, good_urls)

    with open(args.output_file, "w") as ofile:
        ofile.writelines(good_urls)


def worker(lines, good_urls):
    asyncio.get_event_loop().run_until_complete(check_all_methods(lines, good_urls))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_file", help="Input file with urls on it (one per line)", type=str, required=True)
    parser.add_argument("-o", "--output_file", help="Output file with good urls (one per line)", type=str, required=True)
    parser.add_argument('-v', '--verbose', help="Be verbose", action="store_const", dest="loglevel", const=logging.INFO)
    args = parser.parse_args()

    if not os.path.isfile(args.input_file):
        logging.error("File not found! {}".format(args.input_file))
        exit()

    logging.basicConfig(level=args.loglevel)
    try:
        os.remove(os.path.realpath(args.output_file))
    except:
        pass

    multiprocess_start = time.time()
    multiprocess_executer(args)
    multiprocess_end = time.time()

    print("Multiprocess time: {}".format(multiprocess_end - multiprocess_start))

