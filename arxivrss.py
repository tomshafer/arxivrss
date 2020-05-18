"""arxivrss: Deduplicate and clean arXiv RSS feeds.

1. Download a collection of feeds
2. Build a list of entries in each feed
3. Delete unwanted entries from each feed
4. Export the remaining entries.

TODO:
  1. Simplify the deletion logic
  2. Clean up the copies
  3. Clen up the <li> tags that I'm not deleting yet
"""

import argparse as ap
import copy
import logging
import os
import re
from collections import OrderedDict
from typing import List, Tuple, Union

import requests
from lxml.etree import (
    Element,
    ElementTree,
    fromstring as xml_fromstring,
    tostring as xml_tostring,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("arxivrss")

__version__ = "0.0.3-devel"

# RSS parsing namespaces
_NS = {"rss": "http://purl.org/rss/1.0/", "dc": "http://purl.org/dc/elements/1.1/"}


def process_arxiv_feeds(
    section_codes: Union[List[str], Tuple[str]], output_dir: str
) -> None:
    """Download, clean, and re-export one or more arXiv RSS feeds.

    Args:
        section_codes (list[str]): arXiv section identifiers
        output_dir (str): where to write the updated XML files
    """
    feeds = OrderedDict({s: Feed(fetch_arxiv_xml(s), s) for s in section_codes})

    counts = {s: {"pre": len(feeds[s].articles)} for s in feeds}

    feeds = remove_updated_articles(feeds)
    feeds = deduplicate_feeds(feeds)
    feeds = match_xml_to_articles(feeds)

    for s in feeds:
        counts[s]["post"] = len(feeds[s].articles)
        logger.info(
            "[%s] Final result: pre %d, post %d; reduction %d (%.1f%%)",
            s,
            counts[s]["pre"],
            counts[s]["post"],
            counts[s]["pre"] - counts[s]["post"],
            100 * (1 - counts[s]["post"] / counts[s]["pre"]),
        )

    for feed in feeds:
        path = os.path.join(output_dir, f"{feed}.xml")
        write_feed(xml=feeds[feed]._xml, subject="feed", path=path)

    num_pre = sum(counts[s]["pre"] for s in feeds)
    num_post = sum(counts[s]["post"] for s in feeds)
    logger.info(
        "TOTAL Final result: pre %d, post %d; reduction %d (%.1f%%)",
        num_pre,
        num_post,
        num_pre - num_post,
        100 * (1 - num_post / num_pre),
    )


class Feed:
    """A Feed is a simple collections of articles.

    Properties:
        articles (dict[Element, Article]): a mapping between XML
            entries and Article objects to facilitate deduplication.
    """

    def __init__(self, xml: Element, subject: str) -> None:
        """Create a Feed from XML.

        Args:
            xml (Element): the root XML of a feed
        """
        self._xml = copy.deepcopy(xml)
        self.subject = subject
        self.articles = OrderedDict()

        items = self._xml.findall("rss:item", namespaces=_NS)
        for xml_article in items:
            self.articles[Article(xml_article)] = xml_article

        logger.info("[%s] Created feed %s", self.subject, self)

    def __repr__(self):
        """Represent the object."""
        return f"<Feed [{self.subject}] with {len(self.articles)} articles>"


class Article:
    """Representation of an arXiv article.

    Properties:
        title (str): article title
        id (str): arXiv identifier
        version (int): arXiv article version
        subject (str): arXiv subject area (e.g., "nucl-th")
        updated (bool): is the RSS entry article an article update?
    """

    def __init__(self, xml: Element) -> None:
        """Create an Article from an RSS item.

        Args:
            xml (Element): the XML entry for the article
        """
        self._xml = xml  # Not a copy -- it points back to its container

        (
            self.title,
            self.id,
            self.version,
            self.subject,
            self.updated,
        ) = self.parse_title(self._xml)

    def __repr__(self):
        """Represent the object."""
        return f"<Article({self.id}v{self.version}, [{self.subject}])>"

    @classmethod
    def parse_title(cls, xml: Element):
        """Extract the title, section, ID, and updatedness from the title."""
        text = xml.findtext("rss:title", namespaces=_NS)
        if not text:
            raise ValueError(f"could not extract article title: '{text}'")

        RE_TITLE = re.compile(r"^\s*(.+)\s*\((.+)\)\s*$")
        title, meta = _extract_regex_matches(RE_TITLE, text, (1, 2))

        RE_ID = re.compile(r"arXiv:([^v\s]+)(v([0-9]+))?")
        axid, version = _extract_regex_matches(RE_ID, meta, (1, 3))

        RE_SUBJECT = re.compile(r"\[([^\[\]]+)\]")
        subject = _extract_regex_matches(RE_SUBJECT, meta, (1,))

        RE_UPDATED = re.compile(r"UPDATED\s*$")
        updated = RE_UPDATED.search(meta) is not None

        return title.strip(), axid.strip(), int(version), subject.strip(), updated


def fetch_arxiv_xml(section_code: str) -> ElementTree:
    """Download an arXiv RSS file given its section code."""
    logger.info("[%s] Collecting subject", section_code)
    r = requests.get(f"http://export.arxiv.org/rss/{section_code}")
    r.raise_for_status()
    return xml_fromstring(r.content)


def remove_updated_articles(
    feeds: "OrderedDict[str, Feed]",
) -> "OrderedDict[str, Feed]":
    """Remove any updated articles from feeds."""
    feeds = copy.copy(feeds)
    for subject in feeds:
        feeds[subject] = _remove_updated(feeds[subject])
    return feeds


def _remove_updated(feed: Feed) -> Feed:
    feed = copy.copy(feed)
    to_remove = []
    num_pre = len(feed.articles)
    for article in feed.articles:
        if article.updated:
            to_remove.append(article)
    for article in to_remove:
        del feed.articles[article]
    num_post = len(feed.articles)
    logger.info(
        "[%s] Removed %d UPDATED articles: %d -> %d",
        feed.subject,
        len(to_remove),
        num_pre,
        num_post,
    )
    return feed


def deduplicate_feeds(feeds: "OrderedDict[str, Feed]") -> "OrderedDict[str, Feed]":
    """Remove duplicates from feeds.

    Following two steps:
        1. Remove coss-posts that belong to other sections
        2. Remove duplicate articles, keeping the first occurrence
    """
    if len(feeds) < 2:
        return feeds
    feeds = copy.copy(feeds)
    feeds = _clean_up_crosses(feeds)
    feeds = _deduplicate_in_order(feeds)
    return feeds


def _clean_up_crosses(feeds: "OrderedDict[str, Feed]") -> "OrderedDict[str, Feed]":
    # Remove cross-posts if the main subject is in our list
    feeds = copy.copy(feeds)
    subjects = set(feeds)
    for subj in feeds:
        to_remove = []
        num_pre = len(feeds[subj].articles)
        for article in feeds[subj].articles:
            if article.subject != subj and article.subject in subjects:
                to_remove.append(article)
        for article in to_remove:
            del feeds[subj].articles[article]
        num_post = len(feeds[subj].articles)
        logger.info(
            "[%s] Removed %d CROSSES: %d -> %d",
            feeds[subj].subject,
            len(to_remove),
            num_pre,
            num_post,
        )
    return feeds


def _deduplicate_in_order(feeds: "OrderedDict[str, Feed]") -> "OrderedDict[str, Feed]":
    feeds = copy.copy(feeds)
    # Remove duplicated articles, going in order of the feed subjects
    queue = set()
    for subj in feeds:
        num_pre = len(feeds[subj].articles)
        to_remove = []
        for article in feeds[subj].articles:
            if article not in queue:
                queue.add(article)
                continue
            to_remove.append(article)
        for article in to_remove:
            del feeds[subj].articles[article]
        num_post = len(feeds[subj].articles)
        logger.info(
            "[%s] Removed %d DUPLICATES: %d -> %d",
            feeds[subj].subject,
            len(to_remove),
            num_pre,
            num_post,
        )
    return feeds


def match_xml_to_articles(feeds: "OrderedDict[str, Feed]") -> "OrderedDict[str, Feed]":
    """Sync the internal XML representation to the Articles representation."""
    feeds = copy.copy(feeds)
    for subj in feeds:
        feeds[subj] = _match_xml_to_articles(feeds[subj])
    return feeds


def _match_xml_to_articles(feed: Feed) -> Feed:
    feed = copy.copy(feed)
    # Identify what to delete from the XML
    num_pre = len(feed._xml.findall("rss:item", namespaces=_NS))
    to_remove = set(feed._xml.findall("rss:item", namespaces=_NS))
    to_remove.difference_update(feed.articles.values())
    for item in to_remove:
        feed._xml.remove(item)
    num_post = len(feed._xml.findall("rss:item", namespaces=_NS))
    logger.info(
        "[%s] Removed %d XML entries: %d -> %d",
        feed.subject,
        len(to_remove),
        num_pre,
        num_post,
    )
    return feed


def write_feed(xml: ElementTree, subject: str, path: str) -> None:
    """Write the XML to output."""
    logger.info("[%s] Writing to %s", subject, path)
    with open(path, "w") as f:
        f.write(
            xml_tostring(
                xml,
                encoding="unicode",
                doctype='<?xml version="1.0" encoding="UTF-8"?>',
            )
        )
        # f.write(
        #     '<?xml version="1.0" encoding="UTF-8"?>'
        #     + "\n\n"
        #     + ET.tostring(feeds[feed]._xml, encoding="unicode")
        # )


def _extract_regex_matches(rx, text, groups):
    """Safely extract regex matches."""
    test = rx.search(text)
    if not test:
        raise ValueError(f'no matches for regex "{rx}"')
    return test.group(*groups)


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
