"""Deduplicate and clean arXiv RSS feeds.

1. Download a collection of feeds
2. Build a list of entries in each feed
3. Delete unwanted entries from each feed
4. Export the remaining entries.
"""

import argparse as ap
import copy
import logging
import os
import re
from collections import OrderedDict
from typing import Iterable, List, Optional, Pattern, Tuple, Union

import requests
from lxml import etree

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("arxivrss")


__version__ = "0.1.0"

_XML_NAMESPACES = {
    "dc": "http://purl.org/dc/elements/1.1/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss": "http://purl.org/rss/1.0/",
}


class Article:
    def __init__(
        self,
        title: str,
        arxiv_id: str,
        subject: str,
        xml: etree.Element,
        updated: bool = False,
        version: int = 1,
    ):
        self.title = title
        self.arxiv_id = arxiv_id
        self.subject = subject
        self.xml = xml  # XML _points_ to the source
        self.updated = updated
        self.version = version

    def __repr__(self):
        return f"<Article[{self.subject}] id: {self.arxiv_id}>"

    @classmethod
    def from_xml(cls, xml: etree.Element):
        text = xml.findtext("rss:title", namespaces=_XML_NAMESPACES)
        if not text:
            raise ValueError(f"could not extract article title: '{text}'")

        def _extract_regex_matches(rx: Pattern, text: str, groups: Tuple[int, ...]):
            test = rx.search(text)
            if not test:
                raise ValueError(f'no matches for regex "{rx}"')
            return test.group(*groups)

        # Titles are like "The title is here (<metadata>)"
        RE_TITLE = re.compile(r"^\s*(.+)\s*\((.+)\)\s*$")
        title, meta = _extract_regex_matches(RE_TITLE, text, (1, 2))

        # The ID matches "arXiv:..." within <metadata>
        RE_ID = re.compile(r"arXiv:([^v\s]+)(v([0-9]+))?")
        axid, version = _extract_regex_matches(RE_ID, meta, (1, 3))

        # The subject is in braces in <metadata>
        RE_SUBJECT = re.compile(r"\[([^\[\]]+)\]")
        subject = _extract_regex_matches(RE_SUBJECT, meta, (1,))

        # It is labeled very loudly in <metadata> if updated
        RE_UPDATED = re.compile(r"UPDATED\s*$")
        updated = RE_UPDATED.search(meta) is not None

        return cls(
            title=title.strip(),
            arxiv_id=axid.strip(),
            subject=subject.strip(),
            updated=updated,
            version=int(version),
            xml=xml,
        )


class Formatter:
    """Formatters replace an Article's XML in-place."""
    def __call__(self, article: Article) -> etree.Element:
        raise NotImplementedError


class NoopFormatter(Formatter):
    """Do nothing by default."""
    def __call__(self, article: Article) -> etree.Element:
        return article.xml


class LinkTitleFormatter(Formatter):
    """Provide direct PDF links and better titles."""
    def __call__(self, article: Article) -> etree.Element:
        # Update the link
        link = article.xml.find("rss:link", _XML_NAMESPACES)
        link.text = link.text.replace("http://", "https://")
        link.text = link.text.replace("/abs/", "/pdf/") + ".pdf"
        # Update the title
        title = article.xml.find("rss:title", _XML_NAMESPACES)
        title.text = f"[{article.subject}] {article.title}"
        return article.xml


class LinkTitleDescFormatter(LinkTitleFormatter):
    """Provide direct PDF links, better titles, and updated descriptions."""
    def __call__(self, article: Article) -> etree.Element:
        # Get the title and link fixes
        article.xml = super().__call__(article)
        # Do the article reformatting
        descr = article.xml.find("rss:description", _XML_NAMESPACES)
        descr.text = (
            "\n"
            + f'<p><a href="https://arxiv.org/abs/{article.arxiv_id}">'
            + "arXiv abstract page</a>)</p>"
            + "\n\n"
            + descr.text
        )
        return article.xml


class Feed:
    def __init__(self, subject: str, xml: etree.Element) -> None:
        self.subject = subject
        self.xml = copy.deepcopy(xml)

    def __repr__(self) -> str:
        return f"<Feed[{self.subject}], {len(self.articles)} articles>"

    def remove_article(self, article: Article) -> None:
        # Remove from rss:li and from rss:item
        item = f".//rss:item[@rdf:about='http://arxiv.org/abs/{article.arxiv_id}']"
        li = f".//rdf:li[@rdf:resource='http://arxiv.org/abs/{article.arxiv_id}']"
        self.remove_at_xpath(self.xml, item)
        self.remove_at_xpath(self.xml, li)

    def remove_articles(self, articles: Iterable[Article]) -> None:
        for article in articles:
            self.remove_article(article)

    def remove_updated_articles(self) -> None:
        to_remove = [a for a in self.articles if a.updated]
        logger.info("[%s] Removing %d UPDATED articles", self.subject, len(to_remove))
        for article in to_remove:
            self.remove_article(article)

    def write_xml(self, dest: str, formatter: Optional[Formatter] = None) -> None:
        if not formatter:
            formatter = NoopFormatter()
        for article in self.articles:
            article.xml = formatter(article)
        logger.info("[%s] Writing to %s", self.subject, dest)
        with open(dest, "w") as f:
            f.write(
                etree.tostring(
                    self.xml,
                    encoding="unicode",
                    doctype='<?xml version="1.0" encoding="UTF-8"?>',
                )
            )

    @classmethod
    def remove_at_xpath(cls, xml: etree.Element, xpath: str) -> None:
        elem = xml.find(xpath, _XML_NAMESPACES)
        elem.getparent().remove(elem)

    def remove_shared_crosses(self, subjects: List[str]) -> None:
        rsub = set(subjects).difference([self.subject])
        remove = [a for a in self.articles if a.subject in rsub]
        logger.info("[%s] Removing %d CROSS POSTED articles", self.subject, len(remove))
        for a in self.articles:
            if a.subject != self.subject and a.subject in subjects:
                self.remove_article(a)

    @classmethod
    def from_arxiv_rss(cls, subject: str) -> "Feed":
        xml = fetch_arxiv_rss(subject)
        return cls(subject, xml)

    @classmethod
    def rss_items(cls, xml: etree.Element) -> List[etree.Element]:
        return xml.findall("rss:item", namespaces=_XML_NAMESPACES)

    @property
    def articles(self) -> List[Article]:
        return [Article.from_xml(item) for item in self.rss_items(self.xml)]


def fetch_arxiv_rss(subject: str) -> etree.Element:
    logger.info("[%s] Collecting subject", subject)
    r = requests.get(f"http://export.arxiv.org/rss/{subject}")
    r.raise_for_status()
    return etree.fromstring(r.content)


def deduplicate_feeds(feeds: "OrderedDict[str, Feed]") -> "OrderedDict[str, Feed]":
    # Remove crosses for which we have primary sources
    subjects = [feeds[f].subject for f in feeds]
    for subject in feeds:
        feeds[subject].remove_shared_crosses(subjects)
    # Keep remaining crosses in order of appearance
    queue = set()
    for subject in feeds:
        feed = feeds[subject]
        remove = set()
        for article in feed.articles:
            if article.arxiv_id in queue:
                remove.add(article.arxiv_id)
            else:
                queue.add(article.arxiv_id)
        logger.info("[%s] Removing %d DUPLICATE articles", subject, len(remove))
        feed.remove_articles([a for a in feed.articles if a.arxiv_id in remove])
    return feeds


# Main -------------------------------------------------------------------------


def log_counts(subject: str, pre: int, post: int) -> None:
    reduction = pre - post
    reduction_pct = 100 * reduction / (pre + 1e-15)
    logger.info(
        "[%s] Final result: pre %d, post %d; reduction %d (%.1f%%)",
        subject,
        pre,
        post,
        reduction,
        reduction_pct,
    )


def process_arxiv_feeds(
    section_codes: Union[List[str], Tuple[str]], output_dir: str
) -> None:
    """Download, clean, and re-export one or more arXiv RSS feeds.

    Args:
        section_codes (list[str]): arXiv section identifiers
        output_dir (str): where to write the updated XML files
    """
    feeds = OrderedDict({s: Feed.from_arxiv_rss(s) for s in section_codes})
    counts = {s: {"pre": len(feeds[s].articles)} for s in feeds}

    for subj in feeds:
        feeds[subj].remove_updated_articles()
    feeds = deduplicate_feeds(feeds)

    for s in feeds:
        counts[s]["post"] = len(feeds[s].articles)
        log_counts(s, counts[s]["pre"], counts[s]["post"])

    for feed in feeds:
        path = os.path.join(output_dir, f"{feed}.xml")
        feeds[feed].write_xml(path, LinkTitleDescFormatter())

    num_pre = sum(counts[s]["pre"] for s in feeds)
    num_post = sum(counts[s]["post"] for s in feeds)
    log_counts("TOTAL", num_pre, num_post)


def _cli() -> ap.Namespace:
    p = ap.ArgumentParser()
    p.add_argument(
        "-o",
        metavar="DIR",
        dest="OUTPUT",
        required=True,
        type=str,
        help="output directory",
    )
    p.add_argument("SUBJECTS", metavar="SUBJ", type=str, nargs="+")
    return p.parse_args()


if __name__ == "__main__":
    cli = _cli()
    process_arxiv_feeds(cli.SUBJECTS, cli.OUTPUT)
