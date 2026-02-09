"""
使用现有的scraper类访问网站并保存DOM
这样可以复用已有的资源管理逻辑
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.newsbreak_scraper import NewsbreakScraper
from scrapers.patch_scraper import PatchScraper
from scrapers.realtor_scraper import RealtorScraper
from scrapers.redfin_scraper import RedfinScraper
from scrapers.nar_scraper import NARScraper
from scrapers.freddiemac_scraper import FreddieMacScraper
from utils.logger import logger


SCRAPERS = {
    'newsbreak': (NewsbreakScraper, '90210'),
    'patch': (PatchScraper, '90210'),
    'realtor': (RealtorScraper, None),
    'redfin': (RedfinScraper, None),
    'nar': (NARScraper, None),
    'freddiemac': (FreddieMacScraper, None),
}


async def save_dom(scraper_class, zipcode=None, website_key=''):
    """使用scraper访问网站并保存DOM"""
    output_dir = Path(__file__).parent.parent / "analysis" / "dom_structures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scraper = scraper_class()
    
    try:
        await scraper._setup_browser(headless=True)
        page = await scraper._create_page()
        
        # 根据scraper类型确定URL
        if zipcode:
            if scraper.source_name == 'Newsbreak':
                url = f"https://www.newsbreak.com/search?q={zipcode}"
            elif scraper.source_name == 'Patch':
                url = f"https://patch.com/search?q={zipcode}"
            else:
                url = scraper.base_url if hasattr(scraper, 'base_url') else ''
        else:
            # 对于房地产网站，使用base_url
            if hasattr(scraper, 'base_url'):
                url = scraper.base_url
            else:
                # 根据scraper类型确定URL
                if scraper.source_name == 'Realtor.com':
                    url = 'https://www.realtor.com/news/real-estate-news/'
                elif scraper.source_name == 'Redfin':
                    url = 'https://www.redfin.com/news/all-redfin-reports/'
                elif scraper.source_name == 'NAR':
                    url = 'https://www.nar.realtor/newsroom'
                elif scraper.source_name == 'Freddie Mac':
                    url = 'https://freddiemac.gcs-web.com/news-releases'
                else:
                    url = ''
        
        if not url:
            print(f"❌ 无法确定 {scraper.source_name} 的URL")
            return
        
        print(f"📍 访问: {url}")
        
        # 访问页面
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except:
            try:
                await page.goto(url, wait_until="load", timeout=60000)
            except:
                await page.goto(url, wait_until="commit", timeout=60000)
        
        await asyncio.sleep(5)  # 等待内容加载
        
        # 获取完整DOM
        html_content = await page.content()
        
        # 保存HTML
        html_file = output_dir / f"{website_key}_full_dom.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  ✓ DOM已保存: {html_file}")
        
        # 截图
        screenshot_file = output_dir / f"{website_key}_screenshot.png"
        await page.screenshot(path=str(screenshot_file), full_page=True)
        print(f"  ✓ 截图已保存: {screenshot_file}")
        
    except Exception as e:
        print(f"❌ 保存DOM失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.cleanup()


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 scripts/save_dom_using_scraper.py <网站名称>")
        print(f"可用网站: {', '.join(SCRAPERS.keys())}")
        sys.exit(1)
    
    website_key = sys.argv[1].lower()
    
    if website_key not in SCRAPERS:
        print(f"❌ 未知网站: {website_key}")
        print(f"可用网站: {', '.join(SCRAPERS.keys())}")
        sys.exit(1)
    
    scraper_class, zipcode = SCRAPERS[website_key]
    await save_dom(scraper_class, zipcode, website_key)


if __name__ == "__main__":
    asyncio.run(main())
