import asyncio
import aiohttp
import re
import random
from urllib.parse import urlparse
from fake_useragent import UserAgent
import gradio as gr
from datetime import datetime
import os

# ---------------------------
# Logging
# ---------------------------
def log_info(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[INFO] [{timestamp}] {message}")

def log_success(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[SUCCESS] [{timestamp}] {message}")

def log_error(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[ERROR] [{timestamp}] {message}")

# ---------------------------
# Rumbo Bot Class
# ---------------------------
class Rumbo:
    def __init__(self, url, bot_count):
        self.url = url
        self.bot_count = bot_count
        self.video_id = None
        self.extracted_video_id = None
        self.channel_name = None
        self.viewer_ids = {}
        self.user_agent_gen = UserAgent()
        self.running = True
        self.viewbot_endpoint = "https://wn0.rumble.com/service.php?api=7&name=video.watching-now"
        self.total_sent = 0
        self.total_accepted = 0

    def get_random_user_agent(self):
        try:
            return self.user_agent_gen.random
        except:
            ua_list = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
            ]
            return random.choice(ua_list)

    async def extract_video_id(self):
        parsed_url = urlparse(self.url)
        if parsed_url.netloc not in ["rumble.com", "www.rumble.com"]:
            raise ValueError("Invalid Rumbo URL")
        log_info("Rumboing...")
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": self.get_random_user_agent()}
            async with session.get(self.url, headers=headers) as resp:
                html = await resp.text()
                match = re.search(r'"embedUrl":"https://rumble.com/embed/([^"]+)/"', html)
                if match:
                    self.video_id = match.group(1)
                    log_success(f"Rumboed: {self.video_id}")
                else:
                    raise ValueError("Could not Rumbo")

    async def get_viewer_ids(self):
        log_info(f"Getting {self.bot_count} Rumbos...")
        url = f"https://rumble.com/embedJS/u3/?request=video&v={self.video_id}"

        async def fetch_viewer_id():
            user_agent = self.get_random_user_agent()
            headers = {"User-Agent": user_agent}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        await asyncio.sleep(random.uniform(0, 0.5))
                        if resp.status == 200:
                            data = await resp.json()
                            viewer_id = data.get("viewer_id")
                            if viewer_id and viewer_id not in self.viewer_ids:
                                if "author" in data and "name" in data["author"]:
                                    self.channel_name = data["author"]["name"]
                                if "vid" in data:
                                    self.extracted_video_id = str(int(data["vid"]))
                                return viewer_id, user_agent
            except Exception as e:
                log_error(f"Error Rumboing: {e}")
            return None, None

        gathered = 0
        while len(self.viewer_ids) < self.bot_count and self.running:
            viewer_id, ua = await fetch_viewer_id()
            if viewer_id:
                self.viewer_ids[viewer_id] = ua
                gathered += 1
                log_success(f"Rumboed {viewer_id} ({gathered}/{self.bot_count})")
                await asyncio.sleep(random.uniform(0, 0.5))
        log_success(f"Finished Rumboing {len(self.viewer_ids)}")

    async def send_view(self, viewer_id, user_agent, attempt_num):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": user_agent}
                data = f"video_id={self.extracted_video_id}&viewer_id={viewer_id}"
                log_info(f"Sending Rumbo {viewer_id}, attempt {attempt_num}...")
                async with session.post(self.viewbot_endpoint, data=data, headers=headers) as resp:
                    await asyncio.sleep(random.uniform(0, 0.5))
                    self.total_sent += 1
                    if resp.status == 200:
                        self.total_accepted += 1
                        log_success(f"Rumbo {viewer_id} attempt {attempt_num} sent — Total accepted: {self.total_accepted}")
                    else:
                        log_error(f"Rumbo {viewer_id} attempt {attempt_num} failed (HTTP {resp.status})")
        except Exception as e:
            log_error(f"Error Rumboing {viewer_id} attempt {attempt_num}: {e}")

    async def send_views_continuously(self):
        while self.running:
            for viewer_id, ua in self.viewer_ids.items():
                await self.send_view(viewer_id, ua, 1)
                await self.send_view(viewer_id, ua, 2)
            log_info("All done Rumboing, waiting 3.5 minutes before next round...")
            await asyncio.sleep(210)

    async def run_viewbot(self):
        await self.extract_video_id()
        await self.get_viewer_ids()
        log_info(f"Starting Rumbo: {self.channel_name}")
        await self.send_views_continuously()

# ---------------------------
# Gradio Functions
# ---------------------------
bot_instance = None

async def start_bot(url, bots):
    global bot_instance
    bot_instance = Rumbo(url, int(bots))
    asyncio.create_task(bot_instance.run_viewbot())
    return "Rumbo started!"

def stop_bot():
    global bot_instance
    if bot_instance:
        bot_instance.running = False
        return "Rumbo stopped!"
    return "No Rumbo running."

# ---------------------------
# Gradio Interface
# ---------------------------
with gr.Blocks() as iface:
    url_input = gr.Textbox(label="Rumbo URL")
    bots_input = gr.Number(label="Number of Rumbos")
    start_btn = gr.Button("Rumbo On")
    stop_btn = gr.Button("Rumbo Off")
    status_label = gr.Label("RumboStatus")

    start_btn.click(fn=start_bot, inputs=[url_input, bots_input], outputs=status_label)
    stop_btn.click(fn=stop_bot, outputs=status_label)

# ---------------------------
# Launch Gradio for Railway
# ---------------------------
iface.launch(
    server_name="0.0.0.0",
    server_port=int(os.environ.get("PORT", 7860))
)
