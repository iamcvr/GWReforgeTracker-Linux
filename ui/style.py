# ui/style.py
from PySide6.QtGui import QColor, QPainter, QPixmap, QPen, QIcon, QPainterPath, QBrush
from PySide6.QtCore import Qt, QRect
from config import AppConfig, ThemeColors

def get_stylesheet():
    return f"""
    QMainWindow {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ThemeColors.DARK_BG_GRADIENT_START}, stop:1 {ThemeColors.DARK_BG_GRADIENT_END});
    }}
    
    QWidget {{ font-family: "{AppConfig.FONT_FAMILY}"; font-size: 14px; color: {ThemeColors.WHITE}; }}

    /* --- PANELS --- */
    QFrame#CardPanel {{
        background-color: {ThemeColors.PANEL_BG};
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
    }}
    QFrame#Transparent {{ background: transparent; border: none; }}

    /* --- SCROLLBARS --- */
    QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0px; }}
    QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.2); min-height: 20px; border-radius: 3px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

    /* --- BUTTONS --- */
    QPushButton {{
        background-color: rgba(255, 255, 255, 0.05);
        color: {ThemeColors.WHITE};
        border-radius: 20px;
        padding: 8px 16px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {ThemeColors.HOVER_WHITE};
        border: 1px solid rgba(255, 255, 255, 0.2);
    }}
    
    /* SYNC BUTTON */
    QPushButton#PrimaryBtn {{
        background-color: {ThemeColors.GOLD};
        color: #111; border: none;
    }}
    QPushButton#PrimaryBtn:hover {{ background-color: #F4CF57; }}
    
    /* HEADER BUTTONS (CIRCULAR) */
    QPushButton#HeaderBtn {{
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 18px; 
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    QPushButton#HeaderBtn:hover {{
        background-color: rgba(255, 255, 255, 0.15);
        border: 1px solid {ThemeColors.GOLD};
    }}
    
    /* DANGER BUTTON (Reset/Delete) */
    QPushButton#DangerBtn {{ 
        background-color: rgba(255, 107, 107, 0.1); 
        color: {ThemeColors.RED}; 
        border: 1px solid {ThemeColors.RED}; 
        border-radius: 20px;
    }}
    QPushButton#DangerBtn:hover {{ background-color: rgba(255, 107, 107, 0.2); color: #FF8888; }}
    
    /* SMALL TOOL BTN */
    QPushButton#ToolBtn {{
        background-color: transparent;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 4px;
    }}
    QPushButton#ToolBtn:hover {{ border-color: {ThemeColors.GOLD}; }}
    
    /* --- FILTER SELECTOR WIDGET --- */
    QPushButton#FilterMainBtn {{
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }}
    QPushButton#FilterMainBtn:hover {{ border: 1px solid {ThemeColors.GOLD}; background-color: rgba(255, 255, 255, 0.1); }}
    QFrame#FilterContainer {{
        background-color: #2b2b30;
        border: 1px solid #444;
        border-top: none;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }}
    QFrame#FilterContainer QPushButton {{
        background-color: transparent; color: #aaa; text-align: left; padding-left: 10px; border-radius: 6px; border: none; font-size: 12px;
    }}
    QFrame#FilterContainer QPushButton:hover {{ background-color: rgba(212, 175, 55, 0.15); color: {ThemeColors.GOLD}; }}
    
    /* --- PROFILE SELECTOR WIDGET --- */
    QPushButton#ProfileMainBtn {{
        background-color: rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }}
    QPushButton#ProfileMainBtn:hover {{ border: 1px solid {ThemeColors.GOLD}; }}
    QFrame#ProfileContainer {{
        background-color: #2b2b30;
        border: 1px solid #444;
        border-top: none;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }}
    QFrame#ProfileContainer QPushButton {{
        background-color: transparent; color: #aaa; text-align: left; padding-left: 10px; border-radius: 6px; border: none;
    }}
    QFrame#ProfileContainer QPushButton:hover {{ background-color: rgba(212, 175, 55, 0.15); color: {ThemeColors.GOLD}; }}

    /* --- CHECKBOXES (TRI-STATE) --- */
    QCheckBox {{ spacing: 15px; background: transparent; }}
    QCheckBox::indicator {{ 
        width: 18px; height: 18px; 
        border: 2px solid #666; 
        border-radius: 6px; 
        background-color: #222; 
    }}
    QCheckBox::indicator:hover {{ border-color: {ThemeColors.WHITE}; }}
    
    /* COMPLETED STATE */
    QCheckBox::indicator:checked {{ 
        background-color: {ThemeColors.GOLD}; 
        border-color: {ThemeColors.GOLD}; 
    }}
    
    /* IN-PROGRESS STATE (Indeterminate) */
    QCheckBox::indicator:indeterminate {{
        background-color: {ThemeColors.GREEN};
        border-color: {ThemeColors.GREEN};
    }}

    /* --- INPUTS & COMBOBOX --- */
    QLineEdit {{
        background-color: rgba(0, 0, 0, 0.3);
        border-radius: 20px;
        padding: 10px 15px;
        color: {ThemeColors.WHITE};
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    QLineEdit:focus {{ border: 1px solid {ThemeColors.GOLD}; }}
    
    /* Pill Search Input used in main_window.py */
    QLineEdit#PillSearchInput {{
        background-color: rgba(0, 0, 0, 0.3);
        border-radius: 18px; 
        padding: 0px 15px;
        color: {ThemeColors.WHITE};
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    QLineEdit#PillSearchInput:focus {{ border: 1px solid {ThemeColors.GOLD}; }}

    /* --- QUEST PILLS --- */
    QPushButton#QuestLabel {{
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 18px;
        padding: 8px 15px;
        text-align: left;
        border: 1px solid transparent;
        max-width: 315px;
    }}
    QPushButton#QuestLabel:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    /* --- TIMESTAMP LABEL --- */
    QLabel#TimeLabel {{
        color: {ThemeColors.GREY};
        font-size: 11px;
        font-style: italic;
        margin-left: 5px;
    }}

    /* --- TABS --- */
    QTabWidget::pane {{ border: none; background: transparent; }}
    QTabBar::tab {{ background: transparent; color: {ThemeColors.GREY}; padding: 8px 12px; font-weight: bold; border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {ThemeColors.GOLD}; border-bottom: 2px solid {ThemeColors.GOLD}; }}
    QTabBar::scroller {{ width: 0px; }}

    /* --- HEADERS --- */
    QLabel#H1 {{ font-size: 24px; font-weight: bold; color: {ThemeColors.WHITE}; }}
    QLabel#H2 {{ font-size: 13px; font-weight: bold; color: {ThemeColors.GOLD}; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }}
    QLabel#SubText {{ font-size: 12px; color: {ThemeColors.GREY}; }}
    
    /* GLOBAL PROGRESS BAR */
    QProgressBar {{
        background: rgba(0,0,0,0.4);
        border: 1px solid rgba(255,255,255,0.05); 
        border-radius: 9px; 
        text-align: center;
        color: #fff;
        font-weight: bold;
        font-size: 11px;
    }}
    
    QProgressBar::chunk {{ 
        background-color: {ThemeColors.GOLD}; 
        border-radius: 9px; 
    }}

    /* CAMPAIGN PROGRESS BAR */
    QProgressBar#CampBar {{
        min-height: 6px;
        max-height: 6px;
        border-radius: 3px; 
        border: none;
        background: rgba(255,255,255,0.1);
    }}

    QProgressBar#CampBar::chunk {{
        border-radius: 3px;
        background-color: {ThemeColors.GOLD};
    }}
    
    QSplitter::handle {{ background: transparent; }}
    """

def create_custom_icon(shape, color_hex):
    # (Rest of create_custom_icon remains the same)
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    pen = QPen(QColor(color_hex))
    pen.setWidth(4)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    
    if shape == "search":
        painter.drawEllipse(12, 12, 28, 28)
        painter.drawLine(36, 36, 52, 52)
    elif shape == "info":
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(36)
        font.setFamily(AppConfig.FONT_FAMILY)
        painter.setFont(font)
        painter.drawText(QRect(0, 0, 64, 64), Qt.AlignCenter, "i")
    elif shape == "moon":
        path = QPainterPath()
        path.addEllipse(12, 12, 36, 36)
        cut = QPainterPath()
        cut.addEllipse(22, 6, 36, 36)
        path = path.subtracted(cut)
        painter.fillPath(path, QBrush(QColor(color_hex)))
    elif shape == "sun":
        painter.drawEllipse(20, 20, 24, 24)
        painter.drawLine(32, 10, 32, 16) 
        painter.drawLine(32, 48, 32, 54) 
        painter.drawLine(10, 32, 16, 32) 
        painter.drawLine(48, 32, 54, 32) 
    elif shape == "trash":
        painter.drawRect(20, 24, 24, 30)
        painter.drawLine(16, 20, 48, 20)
        painter.drawLine(28, 16, 36, 16)
    elif shape == "filter":
        # Funnel / Filter icon
        path = QPainterPath()
        path.moveTo(10, 14)
        path.lineTo(54, 14)
        path.lineTo(38, 36)
        path.lineTo(38, 52)
        path.lineTo(26, 46)
        path.lineTo(26, 36)
        path.lineTo(10, 14)
        painter.drawPath(path)
        
    painter.end()
    return QIcon(pixmap)