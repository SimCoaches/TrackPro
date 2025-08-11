#!/usr/bin/env python3
"""
TrackPro ultra-fast bootstrap launcher.
Shows the splash screen immediately, then defers heavy imports to improve perceived startup time.
Also prints high-resolution timing checkpoints to the console to diagnose slow phases.
"""
import sys
import os
import time
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QLinearGradient

BOOT_T0 = time.perf_counter()

def log_boot(msg: str) -> None:
    elapsed_ms = int((time.perf_counter() - BOOT_T0) * 1000)
    print(f"[BOOT +{elapsed_ms}ms] {msg}")


def show_instant_splash(app: QApplication) -> QSplashScreen:
    width, height = 600, 320
    splash_pixmap = QPixmap(width, height)
    splash_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(splash_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Gradient background
    grad = QLinearGradient(0, 0, 0, height)
    grad.setColorAt(0.0, QColor(16, 16, 22))
    grad.setColorAt(1.0, QColor(44, 25, 69))
    painter.fillRect(0, 0, width, height, grad)

    # Title
    painter.setPen(QColor(235, 235, 245))
    painter.setFont(QFont("Arial", 22, QFont.Weight.Bold))
    painter.drawText(0, int(height * 0.60), width, 40, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "TrackPro")

    # Subtitle
    painter.setPen(QColor(180, 180, 200))
    painter.setFont(QFont("Arial", 10))
    painter.drawText(0, int(height * 0.60) + 28, width, 24, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "by Sim Coaches")

    painter.end()

    splash = QSplashScreen(splash_pixmap)
    splash.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
    splash.show()
    splash.showMessage("Loading...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
    app.processEvents()
    log_boot("Splash displayed")
    return splash


def main() -> int:
    log_boot("Bootstrap start")
    # Set critical Qt attributes BEFORE QApplication is created
    try:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL, True)
        log_boot("Qt attributes set")
    except Exception as e:
        log_boot(f"Qt attribute setup skipped: {e}")

    # Minimal app first
    app = QApplication(sys.argv)
    log_boot("QApplication created")
    splash = show_instant_splash(app)

    # Defer heavy import until after splash is visible
    try:
        log_boot("Importing new_ui.main...")
        from new_ui import main as run_main
        log_boot("Imported new_ui.main; handing off to app")
        rc = run_main(app=app, existing_splash=splash)
        log_boot(f"new_ui.main returned rc={rc}")
        return rc
    except Exception as e:
        import traceback
        print("\n\n==== TrackPro crashed during startup ====")
        traceback.print_exc()
        print("========================================\n")
        try:
            input("Press Enter to exit...")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
