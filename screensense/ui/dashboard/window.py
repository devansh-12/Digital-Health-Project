from datetime import date, datetime, timedelta
import sqlite3

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screensense.core.clock import Clock
from screensense.core.gamification import (
    BADGES_CATALOGUE,
    evaluate_new_badges,
    update_streak,
)
from screensense.core.scoring import compute_daily_score
from screensense.platform_adapters.clock import SystemClock
from screensense.storage.export import clear_all_data, export_data_as_json
from screensense.storage.repositories import (
    BadgesRepository,
    BreaksRepository,
    DailyScoreRecord,
    DailyScoresRepository,
    SettingsRepository,
    StreaksRepository,
    UsageHourlyRepository,
    YogaSessionsRepository,
)
from screensense.ui.dashboard.widgets import (
    ScoreGaugeWidget,
    TodayTimelineWidget,
    WeeklyTrendChartWidget,
)
from screensense.ui.settings import SettingsDialog
from screensense.ui.theme.icons import get_svg_icon, get_svg_pixmap


class DashboardWindow(QDialog):
    def __init__(
        self,
        database: sqlite3.Connection,
        settings_repo: SettingsRepository,
        breaks_repo: BreaksRepository,
        yoga_repo: YogaSessionsRepository,
        usage_repo: UsageHourlyRepository,
        scores_repo: DailyScoresRepository,
        streaks_repo: StreaksRepository,
        badges_repo: BadgesRepository,
        settings_dialog: SettingsDialog | None = None,
        clock: Clock | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = database
        self._settings_repo = settings_repo
        self._breaks_repo = breaks_repo
        self._yoga_repo = yoga_repo
        self._usage_repo = usage_repo
        self._scores_repo = scores_repo
        self._streaks_repo = streaks_repo
        self._badges_repo = badges_repo
        self._settings_dialog = settings_dialog
        self._clock = clock if clock is not None else SystemClock()

        self.setWindowTitle("ScreenSense — Dashboard")
        self.setObjectName("dashboardDialog")
        self.setMinimumSize(640, 620)

        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            "QDialog#dashboardDialog { background-color: #1e1e1e; color: #cccccc; }"
            "QLabel { border: none; background: transparent; color: #cccccc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }"
            "QFrame#dashboardCard { background-color: #252526; border: 1px solid #333333; border-radius: 6px; }"
            "QPushButton { border-radius: 4px; padding: 6px 12px; font-size: 12px; border: 1px solid #3c3c3c; background-color: #2d2d2d; color: #cccccc; }"
            "QPushButton:hover { background-color: #383838; color: #ffffff; }"
        )
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(1)

        title_lbl = QLabel("ScreenSense")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 600; color: #ffffff;")
        header_text.addWidget(title_lbl)

        self._date_subtitle = QLabel("Today")
        self._date_subtitle.setStyleSheet("font-size: 11px; color: #858585;")
        header_text.addWidget(self._date_subtitle)

        header.addLayout(header_text)
        header.addStretch()

        if self._settings_dialog is not None:
            settings_btn = QPushButton("Settings", self)
            settings_btn.setIcon(get_svg_icon("gear", "#cccccc", 14))
            settings_btn.clicked.connect(self._settings_dialog.show)
            header.addWidget(settings_btn)

        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)

        main_layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(12)

        card_score = self._create_card()
        score_layout = QVBoxLayout(card_score)
        score_layout.setContentsMargins(14, 12, 14, 12)
        score_layout.setSpacing(8)

        score_h = self._create_card_header("award", "Wellness score")
        score_layout.addLayout(score_h)

        score_center = QHBoxLayout()
        self._gauge = ScoreGaugeWidget(self)
        score_center.addWidget(self._gauge)
        score_layout.addLayout(score_center)

        self._breakdown_text = QLabel("")
        self._breakdown_text.setStyleSheet("font-size: 11px; color: #999999;")
        self._breakdown_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self._breakdown_text)
        grid.addWidget(card_score, 0, 0)

        card_timeline = self._create_card()
        timeline_layout = QVBoxLayout(card_timeline)
        timeline_layout.setContentsMargins(14, 12, 14, 12)
        timeline_layout.setSpacing(6)

        tl_h = self._create_card_header("activity", "Today's timeline")
        timeline_layout.addLayout(tl_h)

        self._timeline_widget = TodayTimelineWidget(self)
        timeline_layout.addWidget(self._timeline_widget)

        self._timeline_summary = QLabel("")
        self._timeline_summary.setStyleSheet("font-size: 11px; color: #858585;")
        timeline_layout.addWidget(self._timeline_summary)
        grid.addWidget(card_timeline, 0, 1)

        card_streak = self._create_card()
        streak_layout = QVBoxLayout(card_streak)
        streak_layout.setContentsMargins(14, 12, 14, 12)
        streak_layout.setSpacing(6)

        streak_h = self._create_card_header("flame", "Streak")
        streak_layout.addLayout(streak_h)

        self._streak_days = QLabel("0 days")
        self._streak_days.setStyleSheet("font-size: 24px; font-weight: 600; color: #ffffff;")
        streak_layout.addWidget(self._streak_days)

        self._streak_sub = QLabel("Best: 0 days · Freeze available")
        self._streak_sub.setStyleSheet("font-size: 11px; color: #858585;")
        streak_layout.addWidget(self._streak_sub)

        badges_header = QLabel("Milestones")
        badges_header.setStyleSheet("font-size: 11px; font-weight: 600; color: #aaaaaa; margin-top: 4px;")
        streak_layout.addWidget(badges_header)

        self._badges_layout = QHBoxLayout()
        self._badges_layout.setSpacing(6)
        streak_layout.addLayout(self._badges_layout)
        grid.addWidget(card_streak, 1, 0)

        card_trend = self._create_card()
        trend_layout = QVBoxLayout(card_trend)
        trend_layout.setContentsMargins(14, 12, 14, 12)
        trend_layout.setSpacing(6)

        trend_h = self._create_card_header("chart", "7-day trend")
        trend_layout.addLayout(trend_h)

        self._trend_chart = WeeklyTrendChartWidget(self)
        trend_layout.addWidget(self._trend_chart)

        self._trend_summary = QLabel("")
        self._trend_summary.setStyleSheet("font-size: 11px; color: #858585;")
        trend_layout.addWidget(self._trend_summary)
        grid.addWidget(card_trend, 1, 1)

        main_layout.addLayout(grid)

        card_insight = self._create_card()
        insight_layout = QHBoxLayout(card_insight)
        insight_layout.setContentsMargins(12, 8, 12, 8)
        insight_layout.setSpacing(8)

        insight_icon = QLabel()
        insight_icon.setPixmap(get_svg_pixmap("lightbulb", "#E9C46A", 15))
        insight_layout.addWidget(insight_icon)

        self._insight_text = QLabel("Insight: Your day starts here. A short break is a good first step.")
        self._insight_text.setStyleSheet("font-size: 12px; color: #cccccc;")
        insight_layout.addWidget(self._insight_text)
        insight_layout.addStretch()
        main_layout.addWidget(card_insight)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        export_btn = QPushButton("Export JSON", self)
        export_btn.setIcon(get_svg_icon("download", "#cccccc", 14))
        export_btn.clicked.connect(self._handle_export)
        footer.addWidget(export_btn)

        clear_btn = QPushButton("Clear History", self)
        clear_btn.setIcon(get_svg_icon("trash", "#e06c75", 14))
        clear_btn.setStyleSheet(
            "QPushButton { border-color: #4a2222; color: #e06c75; }"
            "QPushButton:hover { background-color: #381a1a; color: #ffffff; }"
        )
        clear_btn.clicked.connect(self._handle_clear)
        footer.addWidget(clear_btn)

        footer.addStretch()

        refresh_btn = QPushButton("Refresh", self)
        refresh_btn.setIcon(get_svg_icon("refresh", "#cccccc", 14))
        refresh_btn.clicked.connect(self.refresh_data)
        footer.addWidget(refresh_btn)

        main_layout.addLayout(footer)

    def _create_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("dashboardCard")
        return card

    def _create_card_header(self, icon_name: str, title: str) -> QHBoxLayout:
        h_layout = QHBoxLayout()
        h_layout.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_svg_pixmap(icon_name, "#2A9D8F", 14))
        h_layout.addWidget(icon_lbl)
        text_lbl = QLabel(title)
        text_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #ffffff;")
        h_layout.addWidget(text_lbl)
        h_layout.addStretch()
        return h_layout

    def refresh_data(self) -> None:
        settings = self._settings_repo.load()
        now_dt = datetime.fromtimestamp(self._clock.wall_time())
        today_str = now_dt.strftime("%Y-%m-%d")
        self._date_subtitle.setText(f"Today · {now_dt.strftime('%b %d, %Y')}")

        start_of_day = int(datetime(now_dt.year, now_dt.month, now_dt.day).timestamp())
        now_ts = int(now_dt.timestamp())

        completed_b, due_b = self._breaks_repo.count_for_range(start_of_day, now_ts + 1)
        completed_yoga = self._yoga_repo.count_for_range(start_of_day, now_ts + 1)
        active_seconds = self._usage_repo.get_active_seconds_for_range(start_of_day, now_ts + 3600)

        breakdown = compute_daily_score(
            completed_breaks=completed_b,
            due_breaks=due_b,
            yoga_sessions=completed_yoga,
            yoga_target=settings.yoga_target_per_day,
            active_seconds=active_seconds,
            screen_goal_hours=settings.screen_goal_hours,
        )

        score_rec = DailyScoreRecord(
            day=today_str,
            score=breakdown.score,
            break_c=breakdown.break_score,
            yoga_c=breakdown.yoga_score,
            screen_c=breakdown.screen_score,
            blink_c=breakdown.blink_score,
            counted_for_streak=1 if breakdown.score >= 60 and completed_b >= 1 else 0,
        )
        self._scores_repo.save_score(score_rec)

        streak_state = self._streaks_repo.load()
        streak_state = update_streak(streak_state, today_str, breakdown.score, completed_b)
        self._streaks_repo.save(streak_state)

        earned_codes = self._badges_repo.earned_codes()
        new_badges = evaluate_new_badges(
            earned_codes=earned_codes,
            total_breaks_completed=completed_b,
            total_yoga_sessions=completed_yoga,
            streak_count=streak_state.current,
            today_score=breakdown.score,
        )
        for code in new_badges:
            self._badges_repo.award_badge(code, now_ts)
        earned_codes.update(new_badges)

        self._gauge.set_score(breakdown.score, breakdown.band)
        active_hours = active_seconds / 3600.0
        self._breakdown_text.setText(
            f"Breaks {completed_b}/{due_b} · Yoga {completed_yoga}/{settings.yoga_target_per_day} · Screen {active_hours:.1f}h"
        )

        hourly_rows = self._usage_repo.get_hourly_breakdown_for_range(start_of_day, now_ts + 3600)
        hourly_map: list[tuple[int, int]] = []
        for h_start, act_s, _ in hourly_rows:
            h_dt = datetime.fromtimestamp(h_start)
            hourly_map.append((h_dt.hour, act_s))
        self._timeline_widget.set_data(hourly_map)
        self._timeline_summary.setText(f"{active_hours:.1f}h active · {completed_b} breaks completed")

        self._streak_days.setText(f"{streak_state.current} {'day' if streak_state.current == 1 else 'days'}")
        freeze_status = "Freeze used" if streak_state.freeze_week else "Freeze available"
        self._streak_sub.setText(f"Best: {streak_state.best} days · {freeze_status}")

        self._render_badges(earned_codes)

        recent_scores = self._scores_repo.list_recent(7)
        recent_dict = {rec.day: rec.score for rec in recent_scores}
        chart_data: list[tuple[str, int]] = []
        for i in range(6, -1, -1):
            target_day = now_dt.date() - timedelta(days=i)
            day_str = target_day.strftime("%Y-%m-%d")
            day_label = target_day.strftime("%a")
            chart_data.append((day_label, recent_dict.get(day_str, 0)))
        self._trend_chart.set_data(chart_data)
        avg_score = int(sum(s for _, s in chart_data) / max(1, len(chart_data)))
        self._trend_summary.setText(f"7-day average: {avg_score} pts")

        if completed_b > 0:
            self._insight_text.setText(f"Insight: {breakdown.explanation}")
        else:
            self._insight_text.setText("Insight: Your day starts here. A short break is a good first step.")

    def _render_badges(self, earned_codes: set[str]) -> None:
        while self._badges_layout.count():
            item = self._badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for b in BADGES_CATALOGUE[:4]:
            is_earned = b.code in earned_codes
            badge_frame = QFrame(self)
            badge_frame.setStyleSheet(
                "QFrame {"
                f"  background-color: {'#17332f' if is_earned else '#1e1e1e'};"
                f"  border: 1px solid {'#2A9D8F' if is_earned else '#2c2c2c'};"
                "  border-radius: 4px;"
                "  padding: 3px 6px;"
                "}"
            )
            b_layout = QHBoxLayout(badge_frame)
            b_layout.setContentsMargins(4, 2, 4, 2)
            b_layout.setSpacing(4)

            icon_lbl = QLabel()
            icon_name = "check" if is_earned else "lock"
            icon_color = "#2A9D8F" if is_earned else "#555555"
            icon_lbl.setPixmap(get_svg_pixmap(icon_name, icon_color, 11))
            b_layout.addWidget(icon_lbl)

            name_lbl = QLabel(b.title)
            name_lbl.setStyleSheet(f"font-size: 10px; color: {'#ffffff' if is_earned else '#666666'}; font-weight: {'500' if is_earned else '400'};")
            b_layout.addWidget(name_lbl)

            badge_frame.setToolTip(f"{b.title}: {b.description}")
            self._badges_layout.addWidget(badge_frame)

        self._badges_layout.addStretch()

    def _handle_export(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export ScreenSense Data",
            "screensense_export.json",
            "JSON Files (*.json)",
        )
        if file_path:
            json_text = export_data_as_json(self._db)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_text)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Wellness data successfully exported to:\n{file_path}",
            )

    def _handle_clear(self) -> None:
        confirm = QMessageBox.warning(
            self,
            "Clear History",
            "Are you sure you want to delete all historical logs, breaks, and streaks?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            clear_all_data(self._db)
            self.refresh_data()
            QMessageBox.information(
                self,
                "Data Cleared",
                "Historical activity data has been wiped.",
            )
