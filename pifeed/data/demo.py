import os
import random
from datetime import datetime, timedelta
from typing import List
from .models import FeedItem, FeedSource

# Realistic demo headlines
DEMO_HEADLINES = [
    "Global Summit Reaches Historic Climate Agreement After Marathon Negotiations",
    "Breakthrough in Quantum Computing Achieves New Processing Milestone",
    "Space Agency Announces Plans for First Crewed Mission to Mars",
    "Revolutionary Medical Treatment Shows Promise in Clinical Trials",
    "World Leaders Gather for Emergency Economic Policy Forum",
    "Scientists Discover New Species in Deep Ocean Expedition",
    "Major Infrastructure Project to Transform Urban Transportation",
    "Technology Giants Unveil Next Generation of AI Systems",
    "International Space Station Celebrates 25 Years of Continuous Operation",
    "Renewable Energy Production Surpasses Fossil Fuels in Record Quarter",
    "Archaeological Discovery Rewrites Ancient Civilization Timeline",
    "Global Pandemic Response Network Established by Health Organizations",
    "Electric Vehicle Sales Reach Tipping Point in Major Markets",
    "New Telescope Array Captures First Images of Distant Exoplanet Surface",
    "Historic Peace Treaty Signed After Decades of Regional Conflict",
]

DEMO_SUMMARIES = [
    "In a landmark decision that could reshape global policy for decades to come, delegates from over 190 nations have reached consensus on a comprehensive framework for addressing the most pressing challenges of our time.",
    "Researchers at a leading university have achieved what many thought impossible, demonstrating a working prototype that could revolutionize computing and solve problems that would take traditional computers millions of years.",
    "The ambitious timeline calls for a crewed landing within the next decade, with preparatory robotic missions set to begin as early as next year. The announcement has reignited public interest in space exploration.",
    "Early results from the multi-center trial show significant improvement in patient outcomes, offering hope to millions affected by the condition worldwide. Regulatory approval could come within two years.",
    "The summit brings together finance ministers and central bank governors to address growing concerns about global economic stability and propose coordinated policy responses.",
    "The expedition, which spent three months exploring previously uncharted depths, has catalogued dozens of new species and provided insights into life in extreme environments.",
    "The multi-billion dollar project will introduce high-speed rail connections, modernized public transit, and smart infrastructure systems to reduce congestion and emissions.",
    "The new platforms promise unprecedented capabilities in natural language processing, visual understanding, and decision-making, raising both excitement and concerns among experts.",
    "The orbiting laboratory has hosted hundreds of astronauts from dozens of countries, conducting thousands of experiments that have advanced our understanding of life in space.",
    "The shift marks a significant milestone in the transition to clean energy, driven by falling costs and supportive policies across multiple regions.",
]

def create_demo_placeholder_image(cache_dir: str, index: int) -> str:
    """Create a simple colored placeholder image for demo mode."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return ''

    os.makedirs(cache_dir, exist_ok=True)
    filepath = os.path.join(cache_dir, f'demo_placeholder_{index}.png')

    if os.path.exists(filepath):
        return filepath

    # Generate a visually distinct color per image
    hue_step = 360 / 15
    hue = (index * hue_step) % 360

    # HSV to RGB (S=0.4, V=0.3 for dark, muted backgrounds)
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(hue / 360.0, 0.4, 0.3)

    img = Image.new('RGB', (1920, 1080), (int(r * 255), int(g * 255), int(b * 255)))
    draw = ImageDraw.Draw(img)

    # Add some visual interest - gradient overlay
    for y in range(1080):
        alpha = int(40 * (y / 1080))
        draw.line([(0, y), (1920, y)], fill=(alpha, alpha, alpha + 20))

    # Add a subtle grid pattern
    for x in range(0, 1920, 120):
        draw.line([(x, 0), (x, 1080)], fill=(255, 255, 255, 10), width=1)
    for y in range(0, 1080, 120):
        draw.line([(0, y), (1920, y)], fill=(255, 255, 255, 10), width=1)

    # Add text label
    text = f"DEMO IMAGE {index + 1}"
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (1920 - text_w) // 2
    y = (1080 - text_h) // 2

    # Text shadow
    draw.text((x + 2, y + 2), text, fill=(0, 0, 0), font=font)
    draw.text((x, y), text, fill=(200, 200, 200), font=font)

    img.save(filepath, 'PNG')
    return filepath


class DemoDataProvider:
    """Generates synthetic feed data for demo/testing mode."""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir

    def create_source(self, accent_color: str = '#1E88E5') -> FeedSource:
        """Create a demo FeedSource with synthetic items."""
        items = []
        headlines = random.sample(DEMO_HEADLINES, min(10, len(DEMO_HEADLINES)))

        for i, headline in enumerate(headlines):
            summary = DEMO_SUMMARIES[i % len(DEMO_SUMMARIES)]
            image_path = create_demo_placeholder_image(self.cache_dir, i)

            item = FeedItem(
                title=headline,
                summary=summary,
                link=f'https://demo.example.com/story/{i}',
                image_url=f'demo://placeholder/{i}',
                local_image_path=image_path if image_path else None,
                published=datetime.now() - timedelta(hours=random.randint(1, 24)),
                source_name='Demo Feed',
                accent_color=accent_color,
            )
            items.append(item)

        return FeedSource(
            name='Demo Feed',
            feed_url='',
            accent_color=accent_color,
            items=items,
            last_fetched=datetime.now(),
            is_demo=True,
            refresh_interval=0,
            story_duration=10.0,
            items_limit=10,
        )
