"""采集器模块"""
from scrapers.base_scraper import BaseScraper
from scrapers.local_news_scraper import LocalNewsScraper
from scrapers.newsbreak_scraper import NewsbreakScraper
from scrapers.patch_scraper import PatchScraper
from scrapers.real_estate_scraper import RealEstateScraper
from scrapers.realtor_scraper import RealtorScraper
from scrapers.redfin_scraper import RedfinScraper
from scrapers.nar_scraper import NARScraper
from scrapers.freddiemac_scraper import FreddieMacScraper

__all__ = [
    'BaseScraper',
    'LocalNewsScraper',
    'NewsbreakScraper',
    'PatchScraper',
    'RealEstateScraper',
    'RealtorScraper',
    'RedfinScraper',
    'NARScraper',
    'FreddieMacScraper',
]
