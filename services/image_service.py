import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont


MEDALS_COLORS = [
    (233, 168, 37),   # oro
    (125, 125, 125),  # argento
    (205, 127, 50)    # bronzo
]

def _load_font(size: int, bold: bool = False):
    try:
        if bold:
            return ImageFont.truetype("assets/Rajdhani-Bold.ttf", size)
        return ImageFont.truetype("assets/Rajdhani-Regular.ttf", size)
    except:
        return ImageFont.load_default()


async def build_leaderboard_image(ranking: list[dict[str, Any]], lobby_name: str | None = None) -> io.BytesIO:
    w, h = 1080, 1350

    img = Image.new("RGBA", (w, h), (250, 250, 250))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(64, bold=True)
    name_font = _load_font(42, bold=True)

    draw.text(
        (w // 2, 220),
        "CLASSIFICA GENERALE TEAM" if lobby_name is None else f"LOBBY {lobby_name.upper()}",
        fill=(10, 10, 10),
        font=title_font,
        anchor="ma"
    )

    header_bottom = 300
    bottom_margin = 10

    max_rows = 16

    if not ranking:
        draw.text(
            (w // 2, h // 2),
            "No teams available",
            fill=(10, 10, 10),
            anchor="mm",
            font=name_font
        )
    else:
        usable_height = h - header_bottom - bottom_margin
        row_height = usable_height / max_rows
        size = int(row_height)
        gold_medal = Image.open("assets/gold.png").convert("RGBA").resize((size, size))
        silver_medal = Image.open("assets/silver.png").convert("RGBA").resize((size, size))
        bronze_medal = Image.open("assets/bronze.png").convert("RGBA").resize((size, size))
        medals = [gold_medal, silver_medal, bronze_medal]
        y = header_bottom

        for i, t in enumerate(ranking[:max_rows]):
            name = t.get("name", "Unknown")
            score = t.get("score", 0)
            kills = t.get("kills", 0)

            color = MEDALS_COLORS[i] if i < 3 else (40, 40, 40)
            line_y = int(y + 20)

            if i < 3:
                medal = medals[i]
                img.paste(medal, (80, line_y), medal)
            draw.text(
                (80+row_height, line_y),
                f"{i + 1}°  {name}",
                fill=color,
                font=name_font
            )

            draw.text(
                (w - 300, line_y),
                f"{score} pt",
                fill=color,
                anchor="ra",
                font=name_font
            )

            draw.text(
                (w - 80, line_y),
                f"{kills} kills",
                fill=(60, 60, 60),
                anchor="ra",
                font=name_font
            )

            y += row_height

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_mvp_image(
    mvps: list[dict[str, Any]],
    lobby_name: str | None = None,
    width: int = 1080,
    height: int = 1350
) -> io.BytesIO:

    img = Image.new("RGBA", (width, height), (250, 250, 250))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(64, bold=True)
    name_font = _load_font(48, bold=True)

    draw.text(
        (width // 2, 350),
        "TOP 5 MVP GENERALE" if lobby_name is None else f"TOP 5 MVP LOBBY {lobby_name.upper()}",
        fill=(10, 10, 10),
        anchor="mm",
        font=title_font
    )
    size = 120
    gold_medal = Image.open("assets/gold.png").convert("RGBA").resize((size, size))
    silver_medal = Image.open("assets/silver.png").convert("RGBA").resize((size, size))
    bronze_medal = Image.open("assets/bronze.png").convert("RGBA").resize((size, size))
    medals = [gold_medal, silver_medal, bronze_medal]
    
    start_y = 500
    spacing = 140


    if not mvps:
        draw.text(
            (width // 2, height // 2),
            "No data",
            fill=(30, 30, 30),
            anchor="mm",
            font=name_font
        )
    else:
        for i, d in enumerate(mvps):
            name = d["player"]
            kills = d["kills"]

            y = start_y + i * spacing

            medal = medals[i] if i < len(medals) else None
            if medal is not None:
                img.paste(medal, (180, y-30), medal)

            draw.text(
                (width // 2, y+30),
                f"{i+1}° {name}",
                fill=MEDALS_COLORS[i] if i < 3 else (10, 10, 10),
                anchor="mm",
                font=name_font
            )

            draw.text(
                (width-250, y),
                f"{kills} Kill",
                fill=(10, 10, 10),
                anchor="ra",
                font=name_font
            )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer