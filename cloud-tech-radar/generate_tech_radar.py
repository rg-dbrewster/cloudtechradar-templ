import json
import os
import requests
import textwrap
import random
from math import cos, sin, radians
from PIL import Image, ImageDraw, ImageFont # Function to download the font if it doesn't exist

def download_font(url, font_path):
    if not os.path.exists(font_path):
        response = requests.get(url)
        if response.status_code == 200:
            with open(font_path, 'wb') as f:
                f.write(response.content)
        else:
            raise Exception(f"Failed to download font from {url} (status code: {response.status_code})")

placed_entries=[]
# Download the font if necessary
font_url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf" #needs updating
font_path = "fonts/Roboto-Regular.ttf"
download_font(font_url, font_path)

# Load the font with error handling
try:
    large_font = ImageFont.truetype(font_path, 32)
    font = ImageFont.truetype(font_path, 18)
    small_font = ImageFont.truetype(font_path, 12)
except IOError:
    print("Error loading font. Using default font.")
    font = ImageFont.load_default(28)
    large_font = ImageFont.load_default(12)
    small_font = ImageFont.load_default(8)

# Load json data
with open('product_definitions.json', 'r') as f:
    product_definitions = json.load(f)

with open('tech_radar_product_categories.json', 'r') as f:
    category_titles = json.load(f)

with open('tech_radar_classifications.json', 'r') as f:
    classifications = json.load(f)

# Define quadrants based on category titles, this is a bit all the wrong way around
quadrants = [
    { "id": "data_ml", "name": "Data Platform" },
    { "id": "storage", "name": "Storage and Databases" },
    { "id": "compute", "name": "Compute and Web Platform" },
    { "id": "build_ci", "name": "DevOps" },
    { "id": "observability", "name": "Observability" }
]

# Define rings to appear on the radar for "status" of the tech
rings = [
    { "id": "adopt", "name": "Adopt", "color": "#93c47d" },
    { "id": "evaluation", "name": "Assess", "color": "#fbdb84" },
    { "id": "hold", "name": "Hold", "color": "#efafa9" },
    { "id": "retire", "name": "Retire", "color": "#a32d01" }
]

# Map categories to slices of the circular tech radar
category_to_quadrant = {
    "Data Platform": "data_ml",
    "Storage and Databases": "storage",
    "Compute and Web Platform": "compute",
    "DevOps": "build_ci",
    "Observability": "observability"
}

# Map products to rings based on classifications json file
product_to_ring = {}
for classification, products in classifications.items():
    for product in products:
         product_to_ring[product] = classification
         print (product, classification)

# Function to clean the text because this file format is particularly sensitive to escape chars etc
def clean_text(text):
    return text#.replace('(', '').replace(')', '').strip()

# Transform entries
entries = []
for product_key, product in product_definitions.items():
    quadrant = category_to_quadrant.get(product.get('category'))
    keywords = product.get('keywords', []).join(' ')
    entry = {
        "id": product_key,
        "title": product['name'],
        "description": product.get('description', ''),
        "url": product.get('url', ''),
        "file_path": product.get('file_path', ''),
        "quadrant": quadrant,
        "keywords": keywords,
        "image_url": product.get('image_url', '')
    }
    entries.append(entry)

# Construct the final data model
tech_radar = {
    "title": "Cloud Tech Radar",
    "quadrants": quadrants,
    "rings": rings,
    "entries": entries
}

# Function to resize and add images
def add_images(entry, draw,image, x, y):
    try:
        local_img_path = f'{entry.get("file_path")}'
        
        if not os.path.exists(local_img_path):
            # Download image if it doesn't exist locally
            image_url = entry.get('image_url')
            if image_url:
                response = requests.get(image_url)
                if response.status_code == 200 and 'image' in response.headers['Content-Type']:
                    with open(local_img_path, 'wb') as f:
                        f.write(response.content)
                else:
                    raise Exception(f"Failed to download image for {entry['id']} from {image_url} (status code: {response.status_code}, content type: {response.headers['Content-Type']})")
            else:
                raise Exception(f"No local image or image URL for {entry['id']}")

        opacity_level = 80 #doesn't seem to work
        img = Image.open(local_img_path).convert("RGBA")
        img_w, img_h = img.size
        img_ratio = img_w / img_h
        new_height = 42  #vary based on the content in your tech radar..
        new_width = int(new_height * img_ratio)
        img2 = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        img_x = x - new_width // 2
        img_y = y - new_height // 2
        image.paste(img2, (int(img_x), int(img_y)))
        placed_entries.append((img_x,img_y))
        return int(img_x), int(img_y), new_width, new_height
    except FileNotFoundError:
        print(f"Image file for {entry['id']} not found.")
    except IOError:
        print(f"Error opening image for {entry['id']}.")
    except Exception as e:
        print(f"Error adding image for {entry['id']}: {e}")
    return None, None, None, None

# Draw the tech radar
def draw_tech_radar(tech_radar):
    width, height = 1760, 1400# Set canvas size
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    random.seed(200) 
    center_x, center_y =((width // 2), (height // 2))
    ring_radius = [360, 475, 595, 680]

    quadrant_angle_step = 360 / len(tech_radar['quadrants'])
    
    # Draw quadrants and their titles
    for i, quadrant in enumerate(tech_radar['quadrants']):
        angle = i * quadrant_angle_step
        x = center_x + ring_radius[-1] * cos(radians(angle + quadrant_angle_step / 2))
        y = center_y + ring_radius[-1] * sin(radians(angle + quadrant_angle_step / 2)) 
        draw.text((x, y), quadrant['name'], font=large_font, fill="black", anchor="mm")
        placed_entries.append((x,y))

    # Draw rings and their titles
    for ring in tech_radar['rings']:
        radius = ring_radius[tech_radar['rings'].index(ring)]
        draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=ring['color'], width=3)
        draw.text((center_x + radius, center_y), ring['name'], font=font, fill="black", anchor="mm")
        placed_entries.append((center_x + radius, center_y))
        placed_entries.append((center_x + radius-10, center_y))

    for entry in tech_radar['entries']:
        # Determine quadrant and ring index
        quadrant_index = next((i for i, q in enumerate(tech_radar['quadrants']) if q['id'] == entry['quadrant']), None)
        if quadrant_index is None:
            print(f"Warning: Quadrant {entry['quadrant']} not found for entry {entry['title']}")
            continue
    
        product_name = entry["title"]
        ring_name = product_to_ring.get(product_name, 'hold')
        ring_index = next((i for i, r in enumerate(tech_radar['rings']) if r['id'] == ring_name), None)
        if ring_index is None:
            print(f"Warning: Ring {ring_name} not found for entry {product_name}")
            continue
    
        # Calculate angle and radius
        angle_start = quadrant_index * quadrant_angle_step
        angle_end = angle_start + quadrant_angle_step
        angle = (angle_start + angle_end) / 2  # Center angle of the quadrant section
    
        if ring_index == 0:
            # Special case for the innermost ring
            radius = random.uniform(0, ring_radius[0] + 15)
        else:
            radius = ring_radius[ring_index] 
    
        # Adjust angle slightly to avoid exact overlap
        angle += random.uniform(-quadrant_angle_step / 10, quadrant_angle_step / 10)
        x = center_x + radius * cos(radians(angle))
        y = center_y + radius * sin(radians(angle))
    
        # Collision detection and resolution
        i = 0
        max_attempts = 1000 # Limit attempts to prevent infinite loop
        while any(abs(px - x) < 85 and abs(py - y) < 85 for px, py in placed_entries) and i < max_attempts:
            angle += random.uniform(-5, 5)  # Small random adjustment
            x = center_x + radius * cos(radians(angle))
            y = center_y + radius * sin(radians(angle))
            if abs(x) < 90:
              if abs(y) < 200:
                x+=30
                x*=3
            elif abs(y) < 80 and abs(x) < 200:
                y+=20
                y*=2.5
            i += 1
    
        if i >= max_attempts:
            print(f"Max attempts reached for {entry['title']} at {quadrant_index}, {ring_index}")
    
        # Place image and text
        img_x, img_y, img_w, img_h = add_images(entry, draw, img, x, y)
        if img_x is not None:
            placed_entries.append((x, y))
            draw.text((img_x + img_w / 2 +5 , img_y - img_h/2 +5), entry['title'], font=font, fill="black", anchor="mm")
            draw.text((img_x-img_w/2-12, img_y + img_h/2+12), f"{textwrap.fill(entry['description'],24)}", font=small_font, fill="black")
            placed_entries.append((img_x + img_w/2+5, img_y - img_h/2 +5))
            placed_entries.append((img_x-img_w/2 -12 , img_y + img_h/2+12))

            img.save('output/tech_radar.png')
    print("Tech Radar image saved to tech_radar.png")

draw_tech_radar(tech_radar)

def generate_interactive_html(tech_radar):
    """Generate an HTML file with hover functionality for the tech radar."""
    tech_radar_entries = tech_radar['entries']
    center_x = center_y = INITIAL_CANVAS_SIZE // 2

    # Initialize ring_radius correctly
    ring_radius = [INITIAL_CANVAS_SIZE // 8, INITIAL_CANVAS_SIZE // 4, INITIAL_CANVAS_SIZE // 2, 3 * INITIAL_CANVAS_SIZE // 4]

    initial_positions, medium_font, small_font, ring_radius, center_x, center_y, canvas_size = adjust_sizes(
        tech_radar_entries, center_x, center_y, ring_radius, tech_radar['quadrants'], INITIAL_CANVAS_SIZE)
    adjusted_positions = adjust_positions(initial_positions, tech_radar['quadrants'], tech_radar['rings'], center_x, center_y, ring_radius)

    # Generate HTML content
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .tooltip {
                position: absolute;
                display: none;
                background-color: white;
                border: 1px solid black;
                padding: 5px;
                z-index: 10;
            }
        </style>
        <script>
            function showTooltip(evt, text) {
                var tooltip = document.getElementById('tooltip');
                tooltip.style.display = 'block';
                tooltip.style.left = evt.pageX + 10 + 'px';
                tooltip.style.top = evt.pageY + 10 + 'px';
                tooltip.innerHTML = text;
            }

            function hideTooltip() {
                var tooltip = document.getElementById('tooltip');
                tooltip.style.display = 'none';
            }
        </script>
    </head>
    <body>
        <div id="tooltip" class="tooltip"></div>
        <svg width="{size}" height="{size}">
    """.format(size=canvas_size)

    # Define colors for each ring
    ring_colors = ["rgba(255, 204, 204, 0.5)", "rgba(255, 255, 204, 0.5)", "rgba(204, 255, 204, 0.5)", "rgba(204, 204, 255, 0.5)"]
    
    # Draw the shaded rings
    for i, radius in enumerate(ring_radius):
        html_content += """
            <circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color}" stroke="black" />
        """.format(cx=center_x, cy=center_y, radius=radius, color=ring_colors[i])

    # Place adjusted entries on the SVG
    for x, y, w, h, _, _, entry in adjusted_positions:
        img_x, img_y, img_w, img_h = x - w // 2, y - h // 2, w, h
        html_content += """
            <image x="{img_x}" y="{img_y}" width="{img_w}" height="{img_h}" xlink:href="{img_src}" 
                   onmousemove="showTooltip(evt, '{title}: {description}')" onmouseout="hideTooltip()" />
            <text x="{text_x}" y="{text_y}" font-family="Roboto" font-size="{font_size}" text-anchor="middle">{title}</text>
        """.format(img_x=img_x, img_y=img_y, img_w=img_w, img_h=img_h, img_src=entry['image_url'], 
                   title=entry['title'], description=entry['description'], text_x=img_x + img_w // 2, 
                   text_y=img_y + img_h + 20, font_size=MEDIUM_FONT_SIZE)

    # Add category labels
    for quadrant in tech_radar['quadrants']:
        angle_start = tech_radar['quadrants'].index(quadrant) * quadrant_angle_step
        angle_end = angle_start + quadrant_angle_step
        angle = (angle_start + angle_end) / 2
        label_x = center_x + ring_radius[-1] * 1.1 * cos(radians(angle))
        label_y = center_y + ring_radius[-1] * 1.1 * sin(radians(angle))
        html_content += """
            <text x="{label_x}" y="{label_y}" font-family="Roboto" font-size="{font_size}" text-anchor="middle">{name}</text>
        """.format(label_x=label_x, label_y=label_y, font_size=LARGE_FONT_SIZE, name=quadrant['name'])

    # Close SVG and HTML tags
    html_content += """
        </svg>
    </body>
    </html>
    """

    with open('tech_radar.html', 'w') as f:
        f.write(html_content)

# Generate the interactive HTML file
generate_interactive_html(tech_radar)

