"""
基础采集器类
提供通用的采集功能：反爬虫策略、重试机制等
"""
import asyncio
import random
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from fake_useragent import UserAgent
from playwright.async_api import async_playwright, Browser, Page, Playwright

from config.settings import settings
from utils.logger import logger


class BaseScraper(ABC):
    """基础采集器抽象类"""
    
    def __init__(self, source_name: str):
        """
        初始化采集器
        
        Args:
            source_name: 来源网站名称
        """
        self.source_name = source_name
        self.ua = UserAgent()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context = None  # 保存context引用，防止被垃圾回收
        self._is_persistent_context = False  # 标志：是否使用 persistent context（如 Realtor.com）
        self._is_cleaning_up = False  # 标志：是否正在清理资源（用于区分正常关闭和意外断开）
    
    async def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        # Realtor.com 强制使用固定 UA（macOS + Chrome），避免随机 UA 触发风控
        if self.source_name == "Realtor.com":
            return settings.realtor_user_agent
        try:
            return self.ua.random
        except Exception:
            # 如果fake-useragent失败，使用默认UA
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    async def _random_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """
        随机延迟，模拟人类行为
        
        Args:
            min_seconds: 最小延迟秒数（默认使用配置）
            max_seconds: 最大延迟秒数（默认使用配置）
        """
        min_delay = min_seconds or settings.scrape_delay_min
        max_delay = max_seconds or settings.scrape_delay_max
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def _setup_browser(self, headless: bool = True) -> Browser:
        """
        设置并启动浏览器
        
        Args:
            headless: 是否无头模式
            
        Returns:
            Browser实例
        """
        # 如果浏览器已存在且未关闭，直接返回
        if self.browser:
            try:
                # 检查浏览器是否仍然有效
                contexts = self.browser.contexts
                logger.debug(f"{self.source_name}: 复用现有浏览器")
                return self.browser
            except Exception as e:
                # 浏览器已关闭，需要重新创建
                logger.debug(f"{self.source_name}: 浏览器已关闭，重新创建: {str(e)}")
                self.browser = None
        
        logger.info(f"{self.source_name}: 正在启动浏览器 (headless={headless})...")
        
        if not self.playwright:
            try:
                self.playwright = await async_playwright().start()
                logger.debug(f"{self.source_name}: Playwright已启动")
            except Exception as e:
                logger.error(f"{self.source_name}: Playwright启动失败: {str(e)}", exc_info=True)
                raise
        
        user_agent = await self._get_random_user_agent()
        
        try:
            logger.debug(f"{self.source_name}: 正在启动Chromium浏览器...")
            
            # Realtor.com 在 macOS 上经常对“新会话/无cookie/自动化”触发封禁页。
            # 使用 system Chrome + 持久化 profile，允许手动通过一次验证并复用 cookie。
            if self.source_name == "Realtor.com" and (not headless) and sys.platform == "darwin":
                if not self.playwright:
                    self.playwright = await async_playwright().start()
                profile_dir = Path("logs/realtor_profile")
                profile_dir.mkdir(parents=True, exist_ok=True)

                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    channel="chrome",
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                    user_agent=settings.realtor_user_agent,
                    viewport={"width": 1920, "height": 1080},
                    locale=settings.realtor_locale,
                    timezone_id=settings.realtor_timezone_id,
                    extra_http_headers={
                        "Accept-Language": settings.realtor_accept_language,
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    },
                )
                # persistent context 没有单独的 browser.close() 入口，取其 browser 引用用于通用逻辑
                self.browser = self.context.browser
                self._is_persistent_context = True
                logger.info(f"{self.source_name}: 浏览器已成功启动 (headless={headless}, UA: {user_agent[:50]}...)")
                await asyncio.sleep(1.0)
                return self.browser

            # 启动参数：
            # - macOS 下 headed 模式对部分参数非常敏感，可能导致 Chromium 直接崩溃（TargetClosedError 出现在 new_page 之前）。
            # - 因此在 macOS + headed 时使用“最小参数集”，仅保留必要的 AutomationControlled 关闭。
            launch_args = ['--disable-blink-features=AutomationControlled']
            if headless or sys.platform != "darwin":
                launch_args.extend([
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ])
            
            # 在非headless模式下，添加额外参数以提高稳定性
            if not headless and sys.platform != "darwin":
                launch_args.extend([
                    '--disable-gpu',  # 在某些系统上可以提高稳定性
                    '--disable-software-rasterizer',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ])
            
            # Realtor.com 在 macOS headed 模式下，Playwright 内置 Chromium 可能出现崩溃。
            # 优先使用系统 Chrome（channel="chrome"）以提升稳定性与一致性。
            launch_kwargs = {
                "headless": headless,
                "args": launch_args,
                "timeout": 60000,  # 60秒启动超时
            }
            if self.source_name == "Realtor.com" and (not headless) and sys.platform == "darwin":
                launch_kwargs["channel"] = "chrome"

            self.browser = await self.playwright.chromium.launch(**launch_kwargs)
            self._is_persistent_context = False
            
            # 验证浏览器是否成功启动
            if not self.browser:
                raise Exception("浏览器启动返回None")
            
            # 监听浏览器断开事件（用于检测意外断开，而不是正常关闭）
            def on_disconnected():
                # 如果正在清理资源，这是正常关闭，不是意外断开
                if self._is_cleaning_up:
                    logger.debug(f"{self.source_name}: 浏览器正常关闭")
                    return
                
                # 这是意外断开
                logger.warning(f"{self.source_name}: 浏览器进程意外断开（非正常关闭）")
                self.browser = None
                self.context = None
            
            self.browser.on("disconnected", on_disconnected)
            
            # 添加延迟，确保浏览器完全启动（headless=False需要更长时间）
            wait_time = 2.0 if not headless else 0.5
            await asyncio.sleep(wait_time)
            
            # 验证浏览器是否真的可用
            try:
                _ = self.browser.contexts
                logger.info(f"{self.source_name}: 浏览器已成功启动 (headless={headless}, UA: {user_agent[:50]}...)")
                
                # 在非headless模式下，额外等待以确保窗口完全打开
                if not headless:
                    await asyncio.sleep(1.0)
            except Exception as e:
                logger.error(f"{self.source_name}: 浏览器启动后验证失败: {str(e)}", exc_info=True)
                if self.browser:
                    try:
                        await self.browser.close()
                    except:
                        pass
                self.browser = None
                raise Exception(f"浏览器启动验证失败: {str(e)}")
            
            return self.browser
            
        except Exception as e:
            logger.error(f"{self.source_name}: 浏览器启动失败: {str(e)}", exc_info=True)
            self.browser = None
            raise
    
    async def _create_page(self) -> Page:
        """
        创建新页面并设置反爬虫策略
        
        Returns:
            Page实例
        """
        # 确保浏览器存在且有效
        if not self.browser:
            await self._setup_browser()
        else:
            # 检查浏览器是否仍然有效
            try:
                _ = self.browser.contexts
                logger.debug(f"{self.source_name}: 浏览器有效，继续使用")
            except Exception as e:
                logger.warning(f"{self.source_name}: 浏览器已失效，重新创建: {str(e)}")
                # 只清理 browser 和 context，不要清理 playwright（避免重新启动）
                try:
                    if self.context:
                        await self.context.close()
                        self.context = None
                except:
                    pass
                try:
                    if self.browser:
                        await self.browser.close()
                        self.browser = None
                except:
                    pass
                await self._setup_browser()
        
        # persistent context（如 Realtor.com）会复用 cookie，不应每次关闭
        if self.context and not self._is_persistent_context:
            try:
                await self.context.close()
            except Exception as e:
                logger.debug(f"{self.source_name}: 关闭旧context失败: {str(e)}")
            finally:
                self.context = None
        
            # 如果已有 persistent context（如 Realtor.com），直接在其上创建新页面
            if self.context and self._is_persistent_context:
                self.context.on("dialog", lambda dialog: dialog.accept())
                page = await self.context.new_page()
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)
                logger.info(f"{self.source_name}: 页面已成功创建")
                return page

            # 创建新的context并保存引用
        try:
            logger.debug(f"{self.source_name}: 正在创建浏览器上下文...")
            
            # 在创建context前，再次验证浏览器
            try:
                _ = self.browser.contexts
            except Exception as e:
                raise Exception(f"浏览器在创建context前已断开: {str(e)}")
            
            # 获取user agent
            user_agent = await self._get_random_user_agent()
            
            # 创建context
            # Realtor.com 强制 en-US 画像（locale/headers/timezone/UA 一致化）
            locale = settings.realtor_locale if self.source_name == "Realtor.com" else "en-US"
            extra_http_headers = {}
            if self.source_name == 'Realtor.com':
                # 为Realtor.com设置一致化的请求头（en-US）
                extra_http_headers = {
                    'Accept-Language': settings.realtor_accept_language,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                }
            
            # 构建context参数
            context_kwargs = {
                'user_agent': user_agent,
                'viewport': {'width': 1920, 'height': 1080},
                'locale': locale
            }
            if self.source_name == "Realtor.com":
                context_kwargs["timezone_id"] = settings.realtor_timezone_id
            if extra_http_headers:
                context_kwargs['extra_http_headers'] = extra_http_headers
            
            self.context = await self.browser.new_context(**context_kwargs)
            
            if not self.context:
                raise Exception("Context创建返回None")
            
            # 处理对话框（alert/confirm/prompt）
            self.context.on("dialog", lambda dialog: dialog.accept())
            
            logger.debug(f"{self.source_name}: 正在创建页面...")
            page = await self.context.new_page()
            
            if not page:
                raise Exception("Page创建返回None")
            
            # 注入反检测脚本
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            logger.info(f"{self.source_name}: 页面已成功创建")
            return page
        except Exception as e:
            logger.error(f"{self.source_name}: 创建页面失败: {str(e)}", exc_info=True)
            # 如果创建失败，清理资源
            if self.context:
                try:
                    await self.context.close()
                except:
                    pass
            self.context = None
            raise
    
    async def _retry_with_backoff(
        self,
        func,
        max_retries: Optional[int] = None,
        base_delay: float = 1.0,
        *args,
        **kwargs
    ) -> Any:
        """
        带指数退避的重试机制
        
        Args:
            func: 要执行的异步函数
            max_retries: 最大重试次数（默认使用配置）
            base_delay: 基础延迟秒数
            *args, **kwargs: 传递给func的参数
            
        Returns:
            func的返回值
        """
        max_retries = max_retries or settings.scrape_retry_max
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # 指数退避
                    logger.warning(
                        f"{self.source_name}: 第 {attempt + 1} 次尝试失败，{delay:.1f}秒后重试: {str(e)}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"{self.source_name}: 所有重试均失败: {str(e)}", exc_info=True)
        
        raise last_error
    
    async def cleanup(self):
        """清理资源（关闭浏览器等）"""
        # 设置清理标志，避免disconnected事件被误认为是意外断开
        self._is_cleaning_up = True
        
        try:
            # 先关闭context（会关闭所有相关页面）
            if self.context:
                try:
                    await self.context.close()
                    self.context = None
                except Exception as e:
                    logger.debug(f"{self.source_name}: 关闭context失败: {str(e)}")
            
            # 然后关闭浏览器（这会触发disconnected事件，但我们已经设置了标志）
            # 注意：persistent context 的 browser 由 context 管理，通常不需要单独 close
            if self.browser and not self._is_persistent_context:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.debug(f"{self.source_name}: 关闭浏览器失败: {str(e)}")
                finally:
                    self.browser = None
            elif self.browser and self._is_persistent_context:
                self.browser = None
                self._is_persistent_context = False
            
            # 最后停止playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    logger.debug(f"{self.source_name}: 停止Playwright失败: {str(e)}")
                finally:
                    self.playwright = None
                
            logger.debug(f"{self.source_name}: 资源已清理")
        except Exception as e:
            logger.error(f"{self.source_name}: 清理资源失败: {str(e)}", exc_info=True)
        finally:
            # 重置清理标志
            self._is_cleaning_up = False
    
    @abstractmethod
    async def scrape(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        执行采集（子类必须实现）
        
        Returns:
            文章列表，每个文章包含：
            - source: 来源名称（字符串）
            - title: 标题
            - url: 链接
            - publish_date: 发布时间（ISO格式字符串）
            - content: 完整内容（优先，如果无法获取完整内容则使用content_summary）
            - content_summary: 摘要（如果无法获取完整内容）
            - keywords: 关键词列表（可选）
            - zipcode: Zipcode（仅局部新闻，可选，将映射为zip_code）
            - city: 城市名称（可选，将从配置中获取）
        """
        pass
