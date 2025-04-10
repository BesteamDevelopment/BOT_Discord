import discord
import os
import sqlite3
import shutil
import datetime
import re
import asyncio
import logging
from discord import ButtonStyle
from discord.ext import commands
from discord.ui import View, Button
from dotenv import load_dotenv

# Impostazioni di logging per il debug
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    logging.error("Errore: il token del bot non è stato trovato.")
    exit()

# Configurazione del bot
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Percorso del database
DB_PATH = os.path.join(os.getcwd(), "database.db")
BACKUP_PATH = os.path.join(os.getcwd(), "database_backup.db")

# Connessione al Database
def initialize_database():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            role TEXT,
            date TEXT,
            email TEXT
        )
        """)
        conn.commit()
        logging.debug("✅ Database inizializzato correttamente.")
        return conn, cursor
    except sqlite3.Error as e:
        logging.error(f"Errore con il database: {e}")
        return None, None

conn, cursor = initialize_database()
if conn is None or cursor is None:
    logging.error("Impossibile avviare il bot, errore nel database.")
    exit()

def save_database():
    try:
        conn.commit()
        shutil.copy(DB_PATH, BACKUP_PATH)
        logging.debug("✅ Database aggiornato e backup creato!")
    except Exception as e:
        logging.error(f"Errore durante il salvataggio del database: {e}")

def save_user_data(user_id, username, email):
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT OR REPLACE INTO users (user_id, username, role, date, email)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, "BestDEMO", date, email))
    save_database()

# ------------------------------------------------------------------------------
#                            VERIFICHE E CREAZIONE CANALI
# ------------------------------------------------------------------------------
@bot.event
async def on_ready():
    try:
        logging.debug(f"✅ Il bot {bot.user} è online!")
        for guild in bot.guilds:
            logging.debug(f"Verifica e configurazione per il server: {guild.name}")
            await setup_category_and_channel(guild)
        logging.debug("🏁 Setup completato!")
    except Exception as e:
        logging.error(f"Errore durante l'avvio del bot: {e}")
        await bot.close()

async def setup_category_and_channel(guild):
    try:
        category_name = "----🟢 DEMO 0.1.0 🟢----"
        channel_name = "🚀│demo-requirements"

        logging.debug(f"Verifica la presenza della categoria: {category_name}")
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
            logging.debug(f"Categoria {category_name} creata.")
        else:
            logging.debug(f"Categoria {category_name} già presente.")

        logging.debug(f"Verifica la presenza del canale: {channel_name}")
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            channel = await guild.create_text_channel(channel_name, category=category)
            logging.debug(f"Canale {channel_name} creato.")
        else:
            logging.debug(f"Canale {channel_name} già presente.")

        await channel.set_permissions(guild.default_role, view_channel=True, send_messages=True)
        await send_demo_message(channel)
    except Exception as e:
        logging.error(f"Errore durante la configurazione della categoria o del canale: {e}")

async def send_demo_message(channel):
    try:
        await channel.purge(limit=100)
        embed = discord.Embed(
            title="Welcome in Besteam DEMO V0.1.0",
            description=(
                "It's time to show you what we've been working on for you over the past two years. "
                "To download the DEMO, please check the minimum system requirements listed below and follow the instructions.\n"
                "Be the First!\n\n"  # Aggiungi un salto di linea tra l'inglese e l'italiano
                ":flag_it: E' arrivato il momento di mostrarvi cosa stiamo sviluppando per voi in questi ultimi due anni. "
                "Per scaricare la DEMO, verifica i requisiti minimi sotto elencati e segui la procedura.\n"
                "Buon divertimento.\n\n"
                "-----------------------------\n"
                "How to download the demo:\n\n"
                "1. Click on \"Request the Demo\";\n"
                "2. Respond to the private chat that will be suggested to you;\n"
                "3. Wait for the email with the download link;\n"
                "4. Download the file to your PC;\n"
                "5. Extract the files from the compressed folder;\n"
                "6. Run the file \"Besteam_Demo_0.1.0.exe\" (right-click → \"Run as administrator\")\n\n"
                "-----------------------------\n"
                "Minimum system requirements:\n"
                "Hard Disk: 15 GB\n"
                "Operating System: Windows 10/11 (64-bit)\n"
                "Processor: Intel Core i5 (or equivalent AMD)\n"
                "RAM: 8 GB\n"
                "Graphics Card: DirectX 11/12 compatible (Shader Model 5 or 6) with at least 2 GB VRAM\n"
                "Storage: SSD required (Final space TBD based on the build)\n"
                "Minimum Resolution: 1920x1080"
            ),
            color=discord.Color.green()
        )
        view = DemoSubscriptionView()
        await channel.send(embed=embed, view=view)
    except Exception as e:
        logging.error(f"Errore durante l'invio del messaggio nel canale: {e}")


class DemoSubscriptionView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Request the Demo", style=ButtonStyle.green, custom_id="open_private_chat")
    async def open_private_chat(self, interaction: discord.Interaction, button: Button):
        await start_private_chat(interaction)

# ------------------------------------------------------------------------------
#                     GESTIONE CHAT PRIVATA E RACCOLTA EMAIL
# ------------------------------------------------------------------------------
async def start_private_chat(interaction: discord.Interaction):
    try:
        user = interaction.user
        guild = interaction.guild

        private_chat_category = discord.utils.get(guild.categories, name="---- Demo Subscription ----")
        if not private_chat_category:
            private_chat_category = await guild.create_category("---- Demo Subscription ----")
            logging.debug("Categoria '---- Demo Subscription ----' creata.")

        existing_chat = discord.utils.get(private_chat_category.text_channels, name=f"chat-{user.name}")
        if existing_chat:
            await interaction.response.send_message(
                f"⚠️ You already have an open private chat: {existing_chat.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            bot.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        private_channel = await guild.create_text_channel(
            f"chat-{user.name}",
            category=private_chat_category,
            overwrites=overwrites
        )
        # Indichiamo all'utente dove si trova la chat privata
        await interaction.response.send_message(
            f"✅ Private chat created: {private_channel.mention}\nYour chat is in the category **{private_chat_category.name}**.",
            ephemeral=True
        )

        await private_channel.send("Insert your e-mail! (ex. besteam@gmail.com)")

        def check(m):
            return m.author == user and m.channel == private_channel

        for _ in range(3):
            try:
                email_msg = await bot.wait_for("message", check=check, timeout=600)
            except asyncio.TimeoutError:
                await private_channel.send("⏰ Time expired. Please try again.")
                return

            email = email_msg.content.strip()
            if validate_email(email):
                break
            else:
                await private_channel.send("❌ The email entered is invalid. Please try again.")
        else:
            await private_channel.send("❌ Too many failed attempts. Please try again later.")
            return

        save_user_data(user.id, user.name, email)

        role = discord.utils.get(guild.roles, name="BestDEMO")
        if not role:
            role = await guild.create_role(name="BestDEMO")
        await user.add_roles(role)

        await private_channel.send("✅ You will soon receive an email with the link to download the DEMO! Let's build the Football Metaverse together! This chat will automatically delete in one minute!")
        
        # Dopo 1 secondo attende, poi invia un messaggio finale e cancella la chat
        await asyncio.sleep(1)
        await private_channel.send("🧪 Try the Demo and let us know your feedback in #🧪│fix-and-bug.")
        await asyncio.sleep(60)
        await private_channel.delete()
        # Alla fine il flusso termina, senza inviare ulteriori messaggi a canali pubblici.
    except Exception as e:
        logging.error(f"Error private chat: {e}")
        try:
            await interaction.response.send_message("⚠️ An error occurred. Please try again later.", ephemeral=True)
        except Exception:
            pass

def validate_email(email):
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(regex, email) is not None

# ------------------------------------------------------------------------------
#                           AVVIO DEL BOT
# ------------------------------------------------------------------------------
bot.run(TOKEN)
