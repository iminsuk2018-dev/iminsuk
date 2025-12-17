"""
테마 관리자
애플 스타일 라이트/다크 모드 지원
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ThemeManager:
    """애플리케이션 테마 관리"""

    # 사용 가능한 테마
    THEMES = {
        "light": "apple_light.qss",
        "dark": "apple_dark.qss"
    }

    def __init__(self):
        self.current_theme = "light"
        self.styles_dir = Path(__file__).parent

    def load_theme(self, theme_name: str = "light") -> Optional[str]:
        """
        테마 QSS 파일 로드

        Args:
            theme_name: 'light' 또는 'dark'

        Returns:
            QSS 스타일시트 문자열
        """
        if theme_name not in self.THEMES:
            logger.warning(f"Unknown theme: {theme_name}, falling back to light")
            theme_name = "light"

        qss_file = self.styles_dir / self.THEMES[theme_name]

        if not qss_file.exists():
            logger.error(f"Theme file not found: {qss_file}")
            return None

        try:
            with open(qss_file, 'r', encoding='utf-8') as f:
                stylesheet = f.read()

            self.current_theme = theme_name
            logger.info(f"Loaded theme: {theme_name}")
            return stylesheet

        except Exception as e:
            logger.error(f"Failed to load theme: {e}")
            return None

    def get_current_theme(self) -> str:
        """현재 테마 이름 반환"""
        return self.current_theme

    def toggle_theme(self) -> str:
        """
        라이트/다크 모드 전환

        Returns:
            새로운 테마 이름
        """
        if self.current_theme == "light":
            return "dark"
        else:
            return "light"

    def get_theme_colors(self, theme_name: Optional[str] = None) -> dict:
        """
        테마별 주요 색상 반환

        Args:
            theme_name: 테마 이름 (기본값: 현재 테마)

        Returns:
            색상 딕셔너리
        """
        if theme_name is None:
            theme_name = self.current_theme

        if theme_name == "light":
            return {
                'background': '#f5f5f7',
                'foreground': '#1d1d1f',
                'primary': '#007aff',
                'secondary': '#5ac8fa',
                'accent': '#ff9500',
                'success': '#34c759',
                'warning': '#ff9500',
                'error': '#ff3b30',
                'border': '#d2d2d7',
                'card_background': '#ffffff',
                'text_secondary': '#86868b',
                'hover': '#e8e8ed'
            }
        else:  # dark
            return {
                'background': '#1e1e1e',
                'foreground': '#f5f5f7',
                'primary': '#0a84ff',
                'secondary': '#5ac8fa',
                'accent': '#ff9f0a',
                'success': '#32d74b',
                'warning': '#ff9f0a',
                'error': '#ff453a',
                'border': '#3a3a3c',
                'card_background': '#2c2c2e',
                'text_secondary': '#98989d',
                'hover': '#3a3a3c'
            }

    @staticmethod
    def apply_theme_to_app(app, theme_name: str = "light"):
        """
        QApplication에 테마 적용

        Args:
            app: QApplication 인스턴스
            theme_name: 'light' 또는 'dark'
        """
        theme_manager = ThemeManager()
        stylesheet = theme_manager.load_theme(theme_name)

        if stylesheet:
            app.setStyleSheet(stylesheet)
            logger.info(f"Applied {theme_name} theme to application")
        else:
            logger.error(f"Failed to apply {theme_name} theme")


def get_theme_manager() -> ThemeManager:
    """테마 매니저 싱글톤 인스턴스"""
    if not hasattr(get_theme_manager, "_instance"):
        get_theme_manager._instance = ThemeManager()
    return get_theme_manager._instance
