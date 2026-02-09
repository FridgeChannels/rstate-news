"""
批量保存所有网站的DOM结构
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


SCRAPERS = [
    ('newsbreak', NewsbreakScraper, '90210'),
    ('patch', PatchScraper, '90210'),
    ('realtor', RealtorScraper, None),
    ('redfin', RedfinScraper, None),
    ('nar', NARScraper, None),
    ('freddiemac', FreddieMacScraper, None),
]


async def save_dom(website_key, scraper_class, zipcode=None):
    """使用scraper访问网站并保存DOM"""
    output_dir = Path(__file__).parent.parent / "analysis" / "dom_structures"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    scraper = scraper_class()
    
    try:
        print(f"\n{'='*70}")
        print(f"处理: {website_key}")
        print(f"{'='*70}\n")
        
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
            url = scraper.base_url if hasattr(scraper, 'base_url') else ''
        
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
        
        print("  ✓ 页面已加载")
        await asyncio.sleep(5)  # 等待内容加载
        
        # 处理弹窗
        close_selectors = [
            "button[aria-label*='close' i]", ".close-button",
            "[data-testid='close']", ".cookie-consent button"
        ]
        for selector in close_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click(timeout=2000)
                    await asyncio.sleep(1)
                    break
            except:
                continue
        
        await asyncio.sleep(3)
        
        # 获取完整DOM
        html_content = await page.content()
        
        # 保存HTML
        html_file = output_dir / f"{website_key}_full_dom.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  ✓ DOM已保存: {html_file.name}")
        
        # 截图
        screenshot_file = output_dir / f"{website_key}_screenshot.png"
        await page.screenshot(path=str(screenshot_file), full_page=True)
        print(f"  ✓ 截图已保存: {screenshot_file.name}")
        
        print(f"  ✅ {website_key} 完成")
        
    except Exception as e:
        print(f"  ❌ {website_key} 失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.cleanup()


async def main():
    """主函数"""
    print("="*70)
    print("批量保存所有网站的DOM结构")
    print("="*70)
    
    output_dir = Path(__file__).parent.parent / "analysis" / "dom_structures"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {output_dir}\n")
    
    for website_key, scraper_class, zipcode in SCRAPERS:
        try:
            await save_dom(website_key, scraper_class, zipcode)
            await asyncio.sleep(3)  # 网站之间延迟
        except Exception as e:
            print(f"  ❌ {website_key} 处理失败: {str(e)}")
            continue
    
    print("\n" + "="*70)
    print("✅ 所有网站处理完成！")
    print(f"结果保存在: {output_dir}")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
