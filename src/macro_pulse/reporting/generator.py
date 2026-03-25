import base64
import io
import os

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader

from ..config.report_formats import get_mode_format, load_report_format_config
from ..core.logging import get_logger
from ..core.paths import PACKAGE_ROOT, resolve_project_path
from ..domain.models import RenderedAssetSnapshot, ValueFormat, normalize_dataset


matplotlib.use("Agg")

logger = get_logger(__name__)

DEFAULT_TEMPLATE_DIR = PACKAGE_ROOT / "reporting" / "templates"


def generate_sparkline(history):
    figure, axis = plt.subplots(figsize=(2, 0.5))
    axis.plot(
        history,
        color="#2ecc71" if history[-1] >= history[0] else "#e74c3c",
        linewidth=2,
    )
    axis.axis("off")
    figure.tight_layout(pad=0)

    image = io.BytesIO()
    figure.savefig(image, format="png", transparent=True)
    image.seek(0)
    plt.close(figure)

    return base64.b64encode(image.getvalue()).decode("utf-8")


def generate_html_report(data, template_dir=None):
    normalized_data = normalize_dataset(data)
    logger.info("Generating HTML report for %s categories", len(normalized_data))
    rendered_data = {
        category: [_render_item(item) for item in items]
        for category, items in normalized_data.items()
    }

    env = Environment(loader=FileSystemLoader(_resolve_template_dir(template_dir)))
    template = env.get_template("report.html")
    return template.render(data=rendered_data)


def generate_telegram_summary(data, mode="Global", format_config=None):
    normalized_data = normalize_dataset(data)
    logger.info("Generating Telegram summary for mode=%s", mode)

    def format_line(item):
        if item.price is None:
            return f"{item.name}: N/A"

        # sentiment 카테고리 전용 포맷
        if item.name.startswith("Fear & Greed"):
            score = int(round(item.price))
            change_str = f"{item.change:+.1f}" if item.change else ""
            return f"{item.name}: {score}/100 ({change_str})"

        if item.name == "Put/Call Ratio":
            signal = "풋 우세(공포)" if item.price >= 1.0 else "콜 우세(낙관)"
            return f"{item.name}: {item.price:.2f} [{signal}] ({item.change_pct:+.2f}%)"

        price_str = _format_numeric(item.price, item.value_format)
        if item.change_pct not in (None, 0):
            return f"{item.name}: {price_str} ({item.change_pct:+,.2f}%)"
        return f"{item.name}: {price_str}"

    def get_items(category, names):
        """
        이름 매칭 시 완전 일치를 먼저 시도하고,
        실패하면 startswith 부분 매칭으로 폴백.
        Fear & Greed처럼 이름이 동적으로 바뀌는 항목에 대응.
        """
        source_items = normalized_data.get(category, [])
        found_items = []
        for name in names:
            # 1차: 완전 일치
            match = next((item for item in source_items if item.name == name), None)
            if match:
                found_items.append(match)
                continue
            # 2차: startswith 부분 매칭 (Fear & Greed (xxx) 대응)
            prefix = name.split("(")[0].strip()
            match = next(
                (item for item in source_items if item.name.startswith(prefix)),
                None,
            )
            if match:
                found_items.append(match)
        return found_items

    mode_format = get_mode_format(mode, format_config or load_report_format_config())
    lines = []
    for index, section in enumerate(mode_format.summary_sections):
        section_lines = [format_line(item) for item in get_items(section.category, section.items)]
        if section_lines:
            lines.append(f"[{section.title}]")
            lines.extend(section_lines)
            if index < len(mode_format.summary_sections) - 1:
                lines.append("")

    return "\n".join(lines)


def _resolve_template_dir(template_dir):
    if template_dir is None:
        return str(DEFAULT_TEMPLATE_DIR)
    return str(resolve_project_path(template_dir))


def _render_item(item) -> RenderedAssetSnapshot:
    sparkline = generate_sparkline(item.history) if len(item.history) > 1 else ""
    change_str = ""
    change_pct_str = ""
    color_class = "neutral"

    if item.change is not None:
        change_str = _format_signed_numeric(item.change, item.value_format)
        change_pct_str = (
            f"{item.change_pct:+,.2f}%" if item.change_pct is not None else ""
        )
        color_class = (
            "positive"
            if item.change > 0
            else "negative"
            if item.change < 0
            else "neutral"
        )

    return RenderedAssetSnapshot(
        name=item.name,
        price_str=_format_numeric(item.price, item.value_format),
        change_str=change_str,
        change_pct_str=change_pct_str,
        color_class=color_class,
        sparkline=sparkline,
    )


def _format_numeric(value, value_format):
    if value is None:
        return ""
    decimals = 3 if value_format == ValueFormat.YIELD_3 else 2
    return f"{value:,.{decimals}f}"


def _format_signed_numeric(value, value_format):
    if value is None:
        return ""
    decimals = 3 if value_format == ValueFormat.YIELD_3 else 2
    return f"{value:+,.{decimals}f}"
