#!/usr/bin/env python3

from bs4 import BeautifulSoup
from tqdm.auto import tqdm
import os
import cloudscraper
import argparse
import threading
import time


class LockedIterator(object):
    def __init__(self, it):
        self._lock = threading.Lock()
        self._it = iter(it)

    def __iter__(self):
        return self

    def __next__(self):
        with self._lock:
            return next(self._it)


class KellyScraper:
    def __init__(self, pages_nb, file_type=''):
        self.url = "https://www.theonion.com/opinion/cartoons?startIndex="
        self.extension = self.get_extension(file_type)
        self.lock = threading.Lock()
        self.scraper = cloudscraper.create_scraper()
        self.locked_iterator = LockedIterator(self.kelly_generator(pages_nb))
        self.path = "kelly_comics/"
        try:
            os.mkdir(self.path)
        except FileExistsError:
            # Directory already exists
            pass

    def get_extension(self, file_type):
        file_type = file_type.lower()
        if file_type in ["png", "webp", "jpg", "jpeg"]:
            return f".{file_type}"
        else:
            return ''

    def get_image_link(self, page_url):
        page = self.scraper.get(page_url)
        soup = BeautifulSoup(page.content, "html.parser")
        return f"https://i.kinja-img.com/gawker-media/image/upload/{soup.find('figure')['data-id']}{self.extension}"

    def kelly_generator(self, pages_nb):
        for n in range(pages_nb):
            page = self.scraper.get(f"{self.url}{10 * (n + 1)}")
            soup = BeautifulSoup(page.content, "html.parser")
            try:
                for article in soup.find("body").find_all("article"):
                    try:
                        link = article.find("figure").find("a", href=True)["href"]
                        title = link.split('/')[-1]
                        yield {"title": title, "link": self.get_image_link(link)}
                    except TypeError:
                        # Not a comic
                        pass
            except AttributeError:
                print(f"Reached last page: {n}")
                break

    def print_links(self):
        for link in self.kelly_generator(2):
            print(k)

    def download_file(self, filename, url):
        request = self.scraper.get(url=url, stream=True)
        filename = f"{self.path}{filename}.{request.headers.get('Content-Type', 'image/jpg').split('/')[-1]}"
        if os.path.isfile(filename):
            print(f"{filename} already exists!")
        else:
            with tqdm.wrapattr(open(filename, "wb"), "write", miniters=1,
                               total=int(request.headers.get(
                                   'Content-Length', 0)),
                               desc=filename) as fout:
                for chunk in request.iter_content(chunk_size=4096):
                    fout.write(chunk)
        

    def threaded_download(self):
        for k in self.locked_iterator:
            self.download_file(k["title"], k["link"])

    def create_threads(self, threads_nb):
        threads = list()
        for _ in range(threads_nb):
            x = threading.Thread(target=self.threaded_download)
            threads.append(x)
            x.start()
        for thread in threads:
            thread.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Download Stan Kelly comics from https://www.theonion.com/opinion/cartoons")
    required = parser.add_argument_group('Required arguments')
    required.add_argument('-p', '--pages_nb',
                          help='number of pages to download', required=True)
    optional = parser.add_argument_group('Optional arguments')
    optional.add_argument(
        '-n', '--nthreads', help='number of parallel downloads', required=False, default='4')
    optional.add_argument(
        '-t', '--file_type', help='filetype (png, webp, jpg). Defaults to highest quality', required=False, default='')
    args = parser.parse_args()

    KellyScraper(int(args.pages_nb), args.file_type).create_threads(
        int(args.nthreads))
